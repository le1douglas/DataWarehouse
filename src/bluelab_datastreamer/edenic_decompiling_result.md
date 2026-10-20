# Bluelab OnePen: BLE protocol

What the Bluelab OnePen sends over Bluetooth Low Energy. Two sources:

- **Decompiled:** static analysis of the Edenic Android app (`com.bluelab.new_day_flutter.prod`, version 1.15.3, split APK in `apks/edenic_1.15.3`).
- **Observed:** packets captured from real pens with `ble_bridge.py` and `datastreamer.py`, on Windows with bleak:
  - 2026-10-19: pen `ONE-B8B5`, firmware 1.0.9, probe dry and in water, button presses.
  - 2026-10-20: pen `ONE-A1F0`, firmware 1.0.9, probe dry at 20 °C, then in a warm solution of EC 0.41 and pH 7.26 at about 33 °C.

Each section says which parts are **confirmed** by a capture, **corrected** by one, or still **decompiled only**. The open questions are listed at the end.

## Where the code lives

- The app is Flutter. Its Dart code (`libapp.so`) uses a Bluelab Flutter plugin, `flutter_bl_device_sdk`, which talks to native code through method channels such as `com.bluelab.flutter_bl_device_sdk/onepen` and `.../onepen_telemetry_results`.
- The Bluetooth stack itself is an obfuscated Kotlin library, `io.edenic.blbluetoothsdk`, in the base APK `classes.dex`. Only its model classes keep their real names.
- Key obfuscated classes (JADX names):

| Class | Role |
|---|---|
| `Y8.c` | Table of all service and characteristic UUIDs |
| `Y8.b` | Device-type enum: `OnePen`, `Intellilink`, `Pulse`, `PulsePairing`, `PulseConfigure`, `Unknown` |
| `W.a.h(ScanResult)` | Sorts scan results into device types by advertised service UUID |
| `p2.i` (mode 13) | OnePen client: commands, device-info read, record downloads |
| `W8.A` / `W8.B` / `W8.C` | Notification subscriptions on characteristics `02` / `01` / `03` |
| `W8.F` (case 0) | Decoder for live readings |
| `W8.J` | Decoder for calibration records (`06`) |
| `W8.L` | Decoder for measurement records (`05`) |
| `V4.a.q` | XOR checksum |
| `V2.d.q` | Decoder for the 3-byte value format |
| `W8.s` | GATT wrapper: connect, read, write, notify |
| `p2.l` | Method-channel handler (Flutter method names to commands) |
| `a9.*` | OnePen models and enums |

## Connection

- The app calls `connectGatt(autoConnect = false)` and then `discoverServices()`.
- **No bonding, pairing or encryption** on the OnePen path. **Confirmed:** bleak connects, reads and subscribes without pairing.
- Notifications are enabled by writing `ENABLE_NOTIFICATION_VALUE` to the CCCD `00002902-0000-1000-8000-00805f9b34fb`.
- Writes use `WRITE_TYPE_DEFAULT` (write with response).
- The app doesn't request a larger MTU. **Observed:** bleak reported an MTU of 498 on one connection and 23 on others, but every packet arrived whole at 32 bytes, so the reported value on Windows is not reliable and does not matter.
- **A connect attempt switches the pen on.** The pen switches itself off after the auto-off time (`04`, 270 s on `ONE-A1F0`), or after a long press of the button. Switched off, it can still be found and connected to without touching it, but switching on takes a while: in one test the connection came more than 15 s after the bridge started. A client should keep retrying rather than give up after one attempt (the bridge scans for 10 s at a time and retries).

## Discovery

A device is classed as a OnePen when its advertisement lists service UUID:

```
983DD3DA-D46F-BC05-0100-00C278B6B50A
```

The bridge finds pens by this service UUID too, lists them and connects to the one chosen. Not confirmed by a capture yet. Every pen seen so far is called `ONE-` followed by the last 4 hex digits of its address (`ONE-A1F0` is `F4:86:84:3B:A1:F0`).

For comparison, the other device families advertise:

| Device | Service UUID |
|---|---|
| Intellilink | `12341000-1234-1234-1234-123456789abc` |
| Pulse | `9B3DD3DA-D46F-BC00-0100-00C278B6B50A` |
| Pulse (pairing) | `9B3DD3DA-D46F-BC00-0102-00C278B6B50A` |
| Pulse (configure) | `9B3DD3DA-D46F-BC00-0101-00C278B6B50A` |

The first manufacturer-data entry (2-byte company ID, little-endian, followed by its payload) is passed raw to Flutter. The native code doesn't decode it for the OnePen.

## Services

**Observed** on both pens:

| Service | Characteristics | Notes |
|---|---|---|
| `00001801` generic attribute | `2a05` indicate, `2b29` write + read, `2b2a` read | `2a05` (service changed) cannot be subscribed on Windows: "access denied", harmless |
| `00001800` generic access | `2a00` write + read, `2a01` read, `2a04` read | |
| `983dd3da-...-00c278b6b50a` OnePen | `01` to `06`, see below | |
| `0000180a` device information | `2a24`, `2a29`, `2a25`, `2a26`, `2a27`, `2a28`, all read | maker `Bluelab`, model `NOYB-2023`, firmware `1.0.9`, hardware `P_000048_A03` |
| `8d53dc1d-1db7-4cd3-868b-8a527460aa84` | `da2e7828-fbce-4e01-ae9e-261174997c48` write-without-response + notify | the standard SMP firmware-update service |

## Characteristics

All are in the OnePen service and follow the pattern `983dd3da-d46f-bc05-0100-XXc278b6b50a`.

| XX | Properties used by the app | Properties the pen offers (observed) | Content |
|---|---|---|---|
| `01` | notify | read, notify | Live pH |
| `02` | notify | read, notify | Live EC |
| `03` | notify | read, notify | Live temperature |
| `04` | read, write | read, write, notify | Device info / settings (read); command channel (write). Never notified while subscribed |
| `05` | notify | notify | Stored measurement log |
| `06` | notify | notify | Calibration history |

**Every packet on `01` to `06`, and the read of `04`, is 32 bytes**, with zeros filling the end. The decompiled layouts below are the start of these packets.

## Number format

The same 3-byte value appears in live readings and in measurement records:

```
[int16 little-endian raw][int8 exponent e]
value = raw / 10^e        if e >= 0
value = raw * 10^(-e)     if e <  0
```

**Confirmed:**

- **`raw` is signed.** Read unsigned, the pH electrode's millivolts jump from about +130 to about +42 when they should go negative, and a value that should change smoothly jumps from 329 to 6225. Read signed, both change smoothly.
- **The exponent is signed** and chosen by the pen per value: exponents 6, 4, 3, 2, 1 and −1 (`ff`) were all seen. The same quantity changes exponent when its value would not fit in an int16, for example `f48402` = −315.00 and later `30f301` = −328.0, or temperature `a14e03` = 20.129 and `010d02` = 33.29.
- **`raw` = −9999 means no reading.** A dry EC probe always sends `f1d806`, raw −9999 with exponent 6. Seen only for EC so far.

Example: `f81603` = raw 0x16f8 = 5880, exponent 3, so pH **5.880**.

## Live readings (notify on `01`, `02`, `03`)

**Decompiled:** each notification is 4 bytes:

| Byte | Meaning |
|---|---|
| 0 | Tag, ASCII: `'P'` (0x50) = pH, `'E'` (0x45) = EC, `'T'` (0x54) = temperature. Other tags are dropped. |
| 1–2 | raw, int16 LE |
| 3 | exponent, int8 |

The app subscribes to all three characteristics at once and keeps the latest pH, EC and temperature it has seen. The tag, not the characteristic, decides which quantity a packet is. Decode errors are logged as `BluelabOnePen: Error decoding telemetry`.

**Corrected by observation:** each packet is 32 bytes, about every 0.25 s per characteristic while connected. Each characteristic always carries the same tag. After the tag comes more than one 3-byte value; the app reads only the first and ignores the rest. Each value is in the format above:

| Char | Tag | Value 1 | Value 2 | Value 3 | Value 4 |
|---|---|---|---|---|---|
| `01` | `P` | pH | a second pH, close to the first (unknown) | electrode millivolts | about 13.6 × value 3 (unknown, probably a raw count) |
| `02` | `E` | EC, in the pen's EC unit | unknown, probably a raw count | | |
| `03` | `T` | temperature, in the pen's temperature unit | battery, % | | |

Examples:

```
01  50 b21103 b11103 203502 4e4801   pH 4.530, 4.529, +136.00 mV, 1851.0     (20 °C, dry)
01  50 981c03 a91c03 c4a503 f48402   pH 7.320, 7.337, -23.100 mV, -315.00    (33 °C, solution)
02  45 f1d806 6606ff                 EC none (dry), 16380
02  45 a00f04 c802ff                 EC 0.4000, 7120                         (solution of EC 0.41)
03  54 a14e03 542402                 20.129 °C, battery 93
03  54 010d02 f02302                 33.29 °C, battery 92
```

What backs each meaning:

- **pH:** 7.32 to 7.38 in a solution of pH 7.26, about 4.6 in an earlier one.
- **Millivolts:** pH 4.62 gave +130.7 mV and pH 7.32 gave −23.1 mV, a slope of −57 mV per pH unit, the textbook (Nernst) slope for a pH electrode at 20 to 33 °C. Extending the line to pH 7 gives about −5 mV, close to the 0 mV a pH electrode reads there. The value is sent even with "mV display" off in `04`, so that setting only changes the pen's screen.
- **Value 4 on `01`:** value 4 / value 3 was 13.61 at pH 4.6 and 13.62 to 13.64 at pH 7.3, so it is the same reading on another scale. An earlier guess that it was a countdown (it fell steadily while the pH rose) is wrong: it rose and fell with the pH.
- **EC:** 0.4000 in a solution of EC 0.41. The pen is set to EC (mS/cm) in `04`.
- **Value 2 on `02`:** 16380 dry, 7120 to 7140 in the solution while the temperature rose from 33.3 to 33.7 °C. 16380 is close to 2¹⁴ (16384), the top of a 14-bit converter's range, which is what an open probe would read. So it may be the raw conductance count before temperature compensation. Not confirmed.
- **Temperature:** 20.2 °C in air, 33.3 to 33.7 °C in a warm solution. The pen is set to °C in `04`.
- **Battery:** 93 then 92, while byte 1 of `04` read 93.

## Device info (read `04`)

**Decompiled:** the response is at least 29 bytes. Multi-byte fields are little-endian.

| Byte(s) | Field | Notes |
|---|---|---|
| 0 | (not used) | Possibly a length byte. Observed: always `00` |
| 1 | battery, % | **Confirmed:** matches value 2 on `03` |
| 2–4 | (not used) | Observed: always `00 00 00` |
| 5–7 | firmware version | 3 separate bytes. **Confirmed:** `01 00 09` matches firmware `1.0.9` in the device-information service |
| 8 | brightness | |
| 9 | EC unit | 0 = EC, 1 = CF, 2 = ppm500, 3 = ppm700, 4 = mS/cm |
| 10 | temperature unit | 0 = °C, 1 = °F |
| 11–12 | number of stored measurements | uint16 |
| 13–14 | number of calibrations | uint16. **Confirmed:** 0, as is the count on `06` |
| 15 | mV display enabled | 0 or 1 |
| 16–17 | backlight-on time, seconds | uint16 |
| 18–19 | auto-off time, seconds | uint16 |
| 20 | resolution | 0 = Standard, 1 = High |
| 21–24 | minutes since last pH calibration | int32 |
| 25–28 | minutes since last EC calibration | int32 |

**Observed:** 32 bytes, bytes 29 to 31 are `00`. Pen `ONE-A1F0`:

```
00 5d 000000 010009 28 00 00 0000 0000 00 3c00 0e01 01 949d0000 969d0000 000000
   battery 93, firmware 1.0.9, brightness 40, EC, °C, 0 stored, 0 calibrations,
   mV display off, backlight 60 s, auto-off 270 s, resolution high,
   pH calibrated 40340 min ago, EC calibrated 40342 min ago (about 28 days)
```

Read again a few minutes later, both calibration counters had grown by 4, so they count minutes.

## Commands (write to `04`)

**Decompiled only:** no command has been sent to a real pen yet.

Frame format:

```
[length][0x01][opcode][args...][checksum]
```

- `length` is the frame size without the checksum byte.
- `checksum` is the XOR of every byte before it.

| Opcode | Flutter method | Arguments | Frame |
|---|---|---|---|
| `0x67` | `updateBrightness` | brightness `b` | `08 01 67 b 40 42 0F 00 cs` (the `40 42 0F 00` constant, 1,000,000 as uint32 LE, is always sent) |
| `0x71` | `updateUnits` | EC unit, temperature unit (enum values above) | `05 01 71 ec temp cs` |
| `0x72` | `updateMvEnabled` | 0 or 1 | `04 01 72 v cs` |
| `0x73` | `updateBacklightOnTime` | seconds, uint16 LE | `05 01 73 lo hi cs` |
| `0x74` | `updateAutoOffTime` | seconds, uint16 LE | `05 01 74 lo hi cs` |
| `0x75` | `updateUnitResolution` | 0 = Standard, 1 = High | `04 01 75 r cs` |

Worked example, auto-off at 300 s (0x012C):

```
05 01 74 2C 01  ->  checksum = 05^01^74^2C^01 = 5D
frame: 05 01 74 2C 01 5D
```

`updateFirmware` uses a separate write path (`W8.s.f` / `.b` / `.a`) that wasn't decoded.

## Stored measurements (notify `05`, Flutter `syncMeasurements`)

**Decompiled:**

```
[count (uint8, at most 3)] then count entries of 9 bytes:
  [EC: 3-byte value][pH: 3-byte value][temperature: 3-byte value]
```

- The app enables notifications and keeps collecting until a packet yields no records.
- **The packet carries no timestamp.** The app stamps each record with the phone's current time when it arrives.

**Confirmed and extended by observation:**

- Packets are 32 bytes: the count, up to 3 entries of 9 bytes (bytes 1–9, 10–18, 19–27), then zeros.
- Example: `01 f1d806 f81603 975d03` = 1 reading: EC none (dry), pH 5.880, temperature 23.959 °C.
- A packet of all zeros means nothing (more) is saved, and closes the list.
- **The pen sends its saved readings on every subscribe to `05`, not only at connect, and deletes them once sent.** The official app cannot sync them afterwards, and a reading sent while nothing listens is lost. Unsubscribing and subscribing again every few seconds turns a save on the pen into an event with that delay.
- **The button** (tested 2026-10-20, polling every 0.5 s). A short press is never sent live. The rule:
  - **A press outside a hold saves one reading**, the values at the moment of the press, available on `05` at once (it arrived within about 1 s). The pen's screen then holds that value with a countdown of about 10 s.
  - **Moving the probe during the countdown does not change the saved reading**, and nothing is sent when the countdown ends.
  - **A press during the countdown only ends the hold**: it saves nothing.
  - **A press after the countdown** saves a new reading.

  This explains the "presses work in pairs" result of 2026-10-19 (2 presses gave 1 reading, 4 gave 2): the second press of each pair fell inside the hold. That test's single press that gave nothing is not explained. A press of about 3 s switches the pen off.

## Calibration history (notify `06`, Flutter `syncCalibrations`)

**Decompiled:**

```
bytes 0–1   count, uint16 LE
bytes 2–10  probe ID, 9 bytes (shown as lowercase hex)
then up to min(count, 5) entries of 4 bytes, starting at byte 11:
  [type][temperature int8][value int16 LE]
```

| Type | Meaning |
|---|---|
| 7 | pH 7 |
| 4 | pH 4 |
| 10 | pH 10 |
| 14 | EC |

- EC values are `value / 10000`.
- pH values are left raw; the app doesn't scale them.
- Records get the phone's current time, as with measurements.
- Collection also stops at the first packet that yields no records.

**Confirmed for the header:** 32 bytes, sent once after every subscribe. Neither pen had a calibration stored, so no entry has been seen:

```
ONE-A1F0  0000 01234d77a448e8b2ee 00...   count 0, probe ID 01234d77a448e8b2ee
ONE-B8B5  0000 0123e222639771f2ee 00...   count 0, probe ID 0123e222639771f2ee
```

Both probe IDs start with `0123`.

## Open questions

Protocol:

1. **Value 2 on `01`**, a second pH. Within 0.003 of value 1 at pH 4.6 and 20 °C, about 0.015 above it at pH 7.3 and 33 °C. Perhaps unfiltered, or compensated differently.
2. **Value 4 on `01`**, always about 13.6 × the millivolts. Probably a raw converter count.
3. **Value 2 on `02`**, 16380 dry and about 7130 in EC 0.41. Probably a raw count before temperature compensation. A few minutes later, at the same temperature (33.6 °C), EC read 0.3899 and value 2 read 7220: EC went down while value 2 went up. Moving the pen between solutions confirmed it runs the opposite way to EC, like a resistance: dry 16350, EC 0.40 about 7370, EC 1.29 about 3540. It is not simply proportional to 1 / EC.
4. **Live-reading units.** EC and temperature arrived in the units `04` says the pen is set to (EC, °C), but the units were never changed. Change them with `0x71`, compare, and set them back.
5. **The no-reading value −9999** has only been seen for EC. It may also appear for pH or temperature, for example with the probe unplugged.
6. **`05` with more than 3 readings.** One connect sent a packet starting `05`, then one starting `02`, then zeros. With at most 3 entries per packet, byte 0 may be the number of readings still to come rather than the number in the packet.
7. **A value in `05` that matched no live value:** a saved temperature of 14.199 °C.
8. **A single press that saved nothing** on 2026-10-19 (polling every 5 s). Not seen again with the press rule above.
9. **`04` bytes 0, 2–4 and 29–31**, always zero so far. `04` offers notify but has never sent anything.
10. **Calibration entries on `06`**, and the meaning of the raw pH calibration value (possibly a mV offset). Needs a pen with a calibration stored.
11. **Commands.** None has been sent to a pen yet.
12. **Firmware-update protocol** (the SMP service). Not analysed.
13. **Dart-side security code.** `bluetooth_security.dart` and X25519 crypto exist in the Dart code. Nothing on the OnePen path in the native code uses them; they probably serve Pulse or Intellilink. Connecting without them works.
14. **Scan classification quirk.** As decompiled, `W.a.h` decides on the first advertised service UUID only, so a OnePen that advertises another UUID first may be classed differently. This could be a decompiler artifact. The bridge looks for the OnePen UUID anywhere in the list, so the order does not matter to it.

## Reproducing the analysis

REA's bundled JADX (`/opt/rea/android/jadx-headless-mcp-0.7.1-all.jar`) decompiled the base APK through a small launcher using the JADX API. The decompiled sources are in the session scratchpad: `/tmp/claude-1000/-home-node-work/9b434113-25a0-4b21-abf5-6a854c5f9ecf/scratchpad/all`.

REA evidence IDs:

| Evidence | ID |
|---|---|
| Dart AOT inspection | `ev_9483070dcb975cb7d7741246779ecc534e9fdf01ad98c1fe5969d8471420038f` |
| `TelemetryData` references | `ev_87e00eedf267385450f3c02ba15f8d4d953d766225298e7f35ff82b8249283c2` |

To capture packets again, run the bridge on Windows and the backend in the datastreamer container, in two terminals from the repo root. At the time of the captures above they were named `ble_bridge.py` and `datastreamer.py`.

```powershell
uv run src\bluelab_datastreamer\onepen_bridge.py
docker compose -f compose.yaml -f compose.dev.yaml run --rm datastreamer
```
