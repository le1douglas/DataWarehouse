// ============================================================
// OnePen BLE receiver -> CSV over serial for Excel Data Streamer
//
// Boot: scans for pens, prints a numbered menu, waits for a selection.
// To scan again, press the reset button or unplug and replug the USB cable.
//
// Commands: <n> connect to device n from the boot menu
// r one CSV row now
// sc <ms> stream connect, get data every <ms>
// sd stream disconnect (stops streaming, stays connected)
// status connection / stream / probe / last packet age
// ? command list
//
// CSV columns: ms,wet,ph,ec,temp
// A Reading is one measurement of one liquid. If the probe is not in
// contact, all three value columns are blank.
//
// Line prefixes: # human readable messages
// @ CSV header row
// $ CSV data row
//
// ============================================================

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// ============================================================
// Setup / loop
// ============================================================

static const unsigned long SERIAL_BAUD = 115200;
static const uint32_t SERIAL_SETTLE_MS = 200;
static const uint32_t LOOP_DELAY_MS = 5;

// Everything below is defined further down, in this order.
static void scanForPens();
static void handleSerialInput();
static void serviceConnection();
static void serviceStreaming();

void setup()
{
Serial.begin(SERIAL_BAUD);
delay(SERIAL_SETTLE_MS);
Serial.println(F("# onepen link ready"));

BLEDevice::init("");
scanForPens(); // once, at boot. reset to scan again.
}

void loop()
{
handleSerialInput();
serviceConnection();
serviceStreaming();
delay(LOOP_DELAY_MS);
}

// ============================================================
// Sensor values: decoding and validity
// ============================================================

// Notification payload, 4 bytes:
// [0] status / header byte, not used here
// [1] mantissa, low byte
// [2] mantissa, high byte (little endian, so mantissa = [1] | [2] << 8)
// [3] exponent = number of decimal places
// value = mantissa / 10^exponent
static const size_t SENSOR_PAYLOAD_BYTES = 4;

// A probe not in contact with liquid produces a mantissa well above 32767
// (observed ~55000+). That is a fault signature, not an extreme reading.
static const uint16_t MAX_VALID_MANTISSA = 32767;

// Data older than this is no longer evidence of anything.
static const uint32_t READING_STALE_AFTER_MS = 5000;

struct Decoded
{
float value = NAN;
bool valid = false;
uint32_t receivedAtMs = 0; // millis() at receipt, drives staleness
};

static Decoded decodeSensorValue(const uint8_t *payload, size_t length)
{
Decoded decoded;
if (length < SENSOR_PAYLOAD_BYTES)
return decoded;

uint16_t mantissa = payload[1] | (payload[2] << 8);
uint8_t exponent = payload[3];

decoded.value = mantissa / powf(10.0f, exponent);
decoded.valid = (mantissa <= MAX_VALID_MANTISSA);
decoded.receivedAtMs = millis();
return decoded;
}

// Valid AND recent. Both matter: a valid reading from 30 seconds ago is not
// evidence the probe is in liquid now.
static bool isFresh(const Decoded &decoded, uint32_t nowMs)
{
return decoded.valid && (nowMs - decoded.receivedAtMs) < READING_STALE_AFTER_MS;
}

struct Reading
{
Decoded ph, ec, temperature;

// Nothing should read .value without first checking this.
//
// EC is the only real contact signal: out of water its mantissa jumps above
// MAX_VALID_MANTISSA. pH and temperature keep producing plausible looking
// numbers in air (wrong, but in range), so neither can detect contact.
//
// The pH and temperature terms are therefore not contact tests, they are
// staleness vetoes. All three values are published as one reading, so if any
// of the three stops arriving the whole row is blanked rather than mixing a
// current value with a several second old one.
bool inLiquid(uint32_t nowMs) const
{
return isFresh(ec, nowMs) && isFresh(ph, nowMs) && isFresh(temperature, nowMs);
}
};

// ============================================================
// Latest reading, written from the BLE task
// ============================================================
//
// Arduino's loop runs on core 1; the Bluedroid notify callbacks runs on core 0.
// without a lock, snapshotReading() on core 1 can be halfway through the copy when core 0 overwrites latestReading.
// latestReading and lastPacketAtMs are the only variables shared between the two cores that are protected by a lock.
// other shared variables are not locked.

// do not read latestReading directly, use snapshotReading() to get a copy with the lock held.
static Reading latestReading;
static uint32_t lastPacketAtMs = 0;
static portMUX_TYPE readingMux = portMUX_INITIALIZER_UNLOCKED;

static void storeNotifiedValue(Decoded &destination, const uint8_t *payload, size_t length)
{
// Decode outside the critical section, assign inside. Keeps the lock short.
Decoded decoded = decodeSensorValue(payload, length);

portENTER_CRITICAL(&readingMux);
destination = decoded;
lastPacketAtMs = millis();
portEXIT_CRITICAL(&readingMux);
}

static void onPhNotify(BLERemoteCharacteristic *, uint8_t *payload, size_t length, bool)
{
storeNotifiedValue(latestReading.ph, payload, length);
}

static void onEcNotify(BLERemoteCharacteristic *, uint8_t *payload, size_t length, bool)
{
storeNotifiedValue(latestReading.ec, payload, length);
}

static void onTemperatureNotify(BLERemoteCharacteristic *, uint8_t *payload, size_t length, bool)
{
storeNotifiedValue(latestReading.temperature, payload, length);
}

// Copy of the latest reading, taken with the lock held for thread safety.
static Reading snapshotReading()
{
Reading copy;
portENTER_CRITICAL(&readingMux);
copy = latestReading;
portEXIT_CRITICAL(&readingMux);
return copy;
}

// ============================================================
// Scanning (boot only)
// ============================================================

static const char *DEVICE_NAME_FILTER = "ONE-";
static const int SCAN_DURATION_SECONDS = 4;
static const size_t MAX_FOUND_DEVICES = 8; // Keep <= 9: the menu is a single digit, so a 10th entry could never be selected, and in fact are not displayed at all. Raising this above 9 fails silently.
static const uint32_t SCAN_SETTLE_MS = 100;

struct FoundDevice
{
String name;
BLEAddress address = BLEAddress("00:00:00:00:00:00");
esp_ble_addr_type_t addressType = BLE_ADDR_TYPE_RANDOM;
int rssi = 0;
};

static FoundDevice foundDevices[MAX_FOUND_DEVICES];
static size_t foundDeviceCount = 0;

class ScanCallbacks : public BLEAdvertisedDeviceCallbacks
{
void onResult(BLEAdvertisedDevice device) override
{
if (foundDeviceCount >= MAX_FOUND_DEVICES)
return;
if (!device.haveName())
return;

String name = String(device.getName().c_str());
if (name.indexOf(DEVICE_NAME_FILTER) < 0)
return;

for (size_t i = 0; i < foundDeviceCount; i++)
if (foundDevices[i].address.equals(device.getAddress()))
return; // dedupe

foundDevices[foundDeviceCount].name = name;
foundDevices[foundDeviceCount].address = device.getAddress();
// The pen advertises a random address. The type cannot be reconstructed
// later, so it has to be captured here.
foundDevices[foundDeviceCount].addressType = device.getAddressType();
foundDevices[foundDeviceCount].rssi = device.getRSSI();
foundDeviceCount++;
}
};
static ScanCallbacks scanCallbacks;

static void printFoundDevices()
{
Serial.println(F("# found:"));
for (size_t i = 0; i < foundDeviceCount; i++)
{
Serial.print(F("# "));
Serial.print((unsigned)(i + 1));
Serial.print(F(") "));
Serial.print(foundDevices[i].name);
Serial.print(F(" "));
Serial.print(foundDevices[i].address.toString().c_str());
Serial.print(F(" rssi "));
Serial.println(foundDevices[i].rssi);
}
Serial.println(F("# send the number to connect, and press enter"));
}

static void scanForPens()
{
foundDeviceCount = 0;
Serial.println(F("# scanning..."));

BLEScan *scan = BLEDevice::getScan();
scan->setAdvertisedDeviceCallbacks(&scanCallbacks, false);
scan->setActiveScan(true);
scan->setInterval(100);
scan->setWindow(99);
scan->start(SCAN_DURATION_SECONDS, false); // blocking, boot only
scan->stop(); // must be explicit before any connect
scan->clearResults();
delay(SCAN_SETTLE_MS); // let the controller settle

if (foundDeviceCount == 0)
Serial.println(F("# no devices found. press reset to scan again"));
else
printFoundDevices();
}

// ============================================================
// Connecting
// ============================================================

// Every failure is treated as transient: the pen sleeps and advertises again.
static const uint32_t RECONNECT_DELAY_MS = 2000;
static const uint32_t DISCONNECT_RETRY_DELAY_MS = 500;
static const uint32_t STACK_SETTLE_MS = 100;

static BLEUUID SERVICE_UUID("983dd3da-d46f-bc05-0100-00c278b6b50a");
static BLEUUID PH_UUID("983dd3da-d46f-bc05-0100-01c278b6b50a");
static BLEUUID EC_UUID("983dd3da-d46f-bc05-0100-02c278b6b50a");
static BLEUUID TEMPERATURE_UUID("983dd3da-d46f-bc05-0100-03c278b6b50a");

enum LinkState
{
LINK_MENU, // waiting for a device number
LINK_CONNECTING, // connect attempt due now
LINK_CONNECTED,
LINK_RETRY_WAIT // waiting out reconnectAtMs
};
static volatile LinkState linkState = LINK_MENU;
static volatile uint32_t reconnectAtMs = 0;

// Set this flag before every intentional disconnect:
// connectToSelectedDevice() sometimes calls disconnect() on purpose. That still fires onDisconnect on
// the BLE task, asynchronously, which would overwrite linkState/reconnectAtMs
// after this code has already set them: in the worst case flipping a freshly
// established LINK_CONNECTED back to LINK_RETRY_WAIT and forcing a pointless
// reconnect of a working link. ; onDisconnect consumes it and returns without touching state.
static volatile bool expectingDisconnect = false;

static BLEAddress selectedAddress("00:00:00:00:00:00");
static esp_ble_addr_type_t selectedAddressType = BLE_ADDR_TYPE_RANDOM;
static String selectedName;
static bool haveSelectedDevice = false;

// One client for the life of the program. Creating and destroying a
// BLEClient per reconnect is the main Bluedroid leak.
static BLEClient *bleClient = nullptr;

class ClientCallbacks : public BLEClientCallbacks
{
void onConnect(BLEClient *) override {}

void onDisconnect(BLEClient *) override
{
// BLE task context. No printing, no blocking.
if (expectingDisconnect)
{
expectingDisconnect = false; // consumed, next disconnect is real again
return;
}
linkState = LINK_RETRY_WAIT;
reconnectAtMs = millis() + DISCONNECT_RETRY_DELAY_MS;
}
};
static ClientCallbacks clientCallbacks;

static bool subscribeToSensors()
{
BLERemoteService *service = bleClient->getService(SERVICE_UUID);
if (!service)
{
Serial.println(F("# service not found"));
return false;
}

BLERemoteCharacteristic *ph = service->getCharacteristic(PH_UUID);
BLERemoteCharacteristic *ec = service->getCharacteristic(EC_UUID);
BLERemoteCharacteristic *temperature = service->getCharacteristic(TEMPERATURE_UUID);
if (!ph || !ec || !temperature)
{
Serial.println(F("# characteristics not found"));
return false;
}
if (!ph->canNotify() || !ec->canNotify() || !temperature->canNotify())
{
Serial.println(F("# characteristic cannot notify"));
return false;
}

ph->registerForNotify(onPhNotify);
ec->registerForNotify(onEcNotify);
temperature->registerForNotify(onTemperatureNotify);
return true;
}

static void connectToSelectedDevice()
{
Serial.print(F("# connecting to "));
Serial.println(selectedAddress.toString().c_str());

if (!bleClient)
{
bleClient = BLEDevice::createClient();
bleClient->setClientCallbacks(&clientCallbacks);
}
else if (bleClient->isConnected())
{
expectingDisconnect = true; // device switch, not a failure
bleClient->disconnect();
delay(STACK_SETTLE_MS);
}

// Under the mux: a notify from the connection being torn down can still be
// in flight on the BLE task, and this reset must not interleave with it.
portENTER_CRITICAL(&readingMux);
lastPacketAtMs = 0;
portEXIT_CRITICAL(&readingMux);

if (!bleClient->connect(selectedAddress, selectedAddressType) || !subscribeToSensors())
{
if (bleClient->isConnected())
{
expectingDisconnect = true; // cleanup after failed subscribe
bleClient->disconnect();
}

Serial.println(F("# connect failed"));
linkState = LINK_RETRY_WAIT;
reconnectAtMs = millis() + RECONNECT_DELAY_MS;
return;
}

linkState = LINK_CONNECTED;
Serial.println(F("# connected"));
}

// millis() wraps after ~49 days, so compare as a signed difference.
static bool isDue(uint32_t deadlineMs)
{
return (int32_t)(millis() - deadlineMs) >= 0;
}

static void serviceConnection()
{
if (linkState == LINK_CONNECTING)
connectToSelectedDevice();
else if (linkState == LINK_RETRY_WAIT && isDue(reconnectAtMs))
linkState = LINK_CONNECTING; // attempt happens on the next loop pass
}

// ============================================================
// CSV output
// ============================================================

static const char *CSV_HEADER_ROW = "@ ms,wet,ph,ec,temp";

static void printValue(const Decoded &decoded, int decimals, bool inLiquid)
{
if (inLiquid)
Serial.print(decoded.value, decimals);
// else print nothing -> empty CSV cell -> visible gap in the chart
}

static void emitReadingRow()
{
Reading reading = snapshotReading();
uint32_t nowMs = millis();

// A dead link is never wet, no matter how fresh the last values still look.
// linkState should already been checked before this, but recheck here to make sure state has not changed in the meantime.
bool inLiquid = (linkState == LINK_CONNECTED) && reading.inLiquid(nowMs);

Serial.print(F("$ "));
Serial.print(nowMs);
Serial.print(',');
Serial.print(inLiquid ? 1 : 0);
Serial.print(',');
printValue(reading.ph, 2, inLiquid);
Serial.print(',');
printValue(reading.ec, 3, inLiquid);
Serial.print(',');
printValue(reading.temperature, 1, inLiquid);
Serial.println();
}

// ============================================================
// Streaming
// ============================================================

static const uint32_t MIN_STREAM_PERIOD_MS = 200;
static const uint32_t DEFAULT_STREAM_PERIOD_MS = 3000;

static bool streamingEnabled = false;
static uint32_t streamPeriodMs = DEFAULT_STREAM_PERIOD_MS;
static uint32_t nextRowAtMs = 0;

static void serviceStreaming()
{
// No rows at all while the link is down: output stops on the first missed
// period after a disconnect and resumes by itself once reconnected.
// streamingEnabled stays true through a drop; only sd clears it, so a
// reconnect never needs a fresh sc.
if (!streamingEnabled || linkState != LINK_CONNECTED || !isDue(nextRowAtMs))
return;

nextRowAtMs = millis() + streamPeriodMs;
emitReadingRow(); // blank value fields if not in liquid
}

// ============================================================
// Status report
// ============================================================

static const char *linkStateName()
{
switch (linkState)
{
case LINK_CONNECTED:
return "connected";
case LINK_CONNECTING:
return "connecting";
case LINK_RETRY_WAIT:
return "reconnecting";
default:
return "idle";
}
}

static void printStatus()
{
Reading reading = snapshotReading();

// Same rule as latestReading: only touch it with the lock held.
portENTER_CRITICAL(&readingMux);
uint32_t lastPacketCopyMs = lastPacketAtMs;
portEXIT_CRITICAL(&readingMux);

uint32_t nowMs = millis();

Serial.print(F("# state="));
Serial.print(linkStateName());
Serial.print(F(" device="));
Serial.print(haveSelectedDevice ? selectedName.c_str() : "none");
Serial.print(F(" stream="));
Serial.print(streamingEnabled ? "on" : "off");
Serial.print(F(" period="));
Serial.print(streamPeriodMs);
Serial.print(F("ms wet="));
// status can run mid-reconnect, where values may still count as fresh for a
// few seconds. A dead link is never wet.
Serial.print((linkState == LINK_CONNECTED && reading.inLiquid(nowMs)) ? 1 : 0);
Serial.print(F(" lastpkt="));

if (lastPacketCopyMs)
{
Serial.print(nowMs - lastPacketCopyMs);
Serial.println(F("ms ago"));
}
else
{
Serial.println(F("never"));
}
}

// ============================================================
// Commands
// ============================================================

// Echo of the raw bytes received, useful when Data Streamer sends something
// unexpected.
static void echoCommand(const char *line)
{
Serial.print(F("# received command ("));
Serial.print(strlen(line));
Serial.print(F(" bytes): ["));
for (size_t i = 0; line[i]; i++)
{
Serial.print((int)line[i]);
Serial.print(' ');
}
Serial.println(']');
}

// "1".."9" from the boot menu. Returns false if this is not a menu selection.
// Only valid while still in the menu: once a device has been chosen, a bare
// digit falls through to "unknown command"
static bool handleDeviceSelection(const char *line)
{
if (linkState != LINK_MENU)
return false;

if (line[0] < '1' || line[0] > '9' || line[1])
return false;

size_t deviceIndex = line[0] - '1';
if (deviceIndex >= foundDeviceCount)
{
Serial.println(F("# no such device"));
return true;
}

selectedAddress = foundDevices[deviceIndex].address;
selectedAddressType = foundDevices[deviceIndex].addressType;
selectedName = foundDevices[deviceIndex].name;
haveSelectedDevice = true;
linkState = LINK_CONNECTING;
return true;
}

// Strict form only: "sc <ms>". Bare "sc" is an error, not a silent resume.
static void handleStreamConnect(const char *argument)
{

if (linkState != LINK_CONNECTED)
{
Serial.println(F("# not connected"));
return;
}

char *end;
uint32_t period = strtoul(argument, &end, 10);
if (end == argument || *end)
{
Serial.println(F("# usage: sc <ms>"));
return;
}
if (period < MIN_STREAM_PERIOD_MS)
{
Serial.print(F("# min period "));
Serial.println(MIN_STREAM_PERIOD_MS);
return;
}

streamPeriodMs = period;
streamingEnabled = true;
nextRowAtMs = millis();
Serial.println(CSV_HEADER_ROW); // header row for Data Streamer
}

static void handleCommand(char *line)
{

while (*line == ' ')
line++;
if (!*line)
return;

if (handleDeviceSelection(line))
return;

if (!strcmp(line, "r"))
{
if (linkState != LINK_CONNECTED)
Serial.println(F("# not connected"));
else
emitReadingRow();
return;
}

if (!strncmp(line, "sc ", 3))
{
handleStreamConnect(line + 3);
return;
}

if (!strcmp(line, "sd"))
{
streamingEnabled = false;
Serial.println(F("# stream off"));
return;
}

if (!strcmp(line, "status"))
{
printStatus();
return;
}

if (!strcmp(line, "?"))
{
Serial.println(F("# r | sc <ms> | sd | status | ?"));
return;
}

Serial.println(F("# unknown command, send ?"));
}

// ============================================================
// Serial input (non-blocking, tolerates \r\n)
// ============================================================

static const size_t COMMAND_BUFFER_SIZE = 64;

static char commandBuffer[COMMAND_BUFFER_SIZE];
static size_t commandLength = 0;

// Returns a pointer into commandBuffer once a full line has arrived.
static bool readCommandLine(char **line)
{
while (Serial.available())
{
char c = Serial.read();

if (c == '\r')
continue;

if (c == '\n')
{
commandBuffer[commandLength] = '\0';
commandLength = 0;

echoCommand(commandBuffer); // does not show \r and \n

// Excel Data Streamer's Data Out sheet always sends the whole row as
// CSV, so trailing commas are expected. Cut at the first comma.
char *comma = strchr(commandBuffer, ',');
if (comma)
*comma = '\0';

*line = commandBuffer;
return true;
}

if (commandLength < COMMAND_BUFFER_SIZE - 1)
commandBuffer[commandLength++] = c; // overflow: extra chars dropped
}
return false;
}

static void handleSerialInput()
{
char *line;
if (readCommandLine(&line))
handleCommand(line);
}