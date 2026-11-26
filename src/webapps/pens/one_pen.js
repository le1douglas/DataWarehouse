// the OnePen over Web Bluetooth, in the browser: Chrome's own device chooser, and the bytes of every notification
// sent on to Python (one_pen.py), which decodes them. the protocol is that of bluelab_datastreamer/onepen.py
// - Chrome opens the chooser only from a click, so the buttons run connectOnePen and disconnectOnePen in the
//   browser itself
// - only on a secure page: http://localhost, or https
// - at most one event stream: the previous connection's listeners are removed before each new one, and the
//   handlers are named functions, which the browser never adds twice to the same target

// a device is a OnePen when its advertisement lists this service, as in the edenic app
const ONE_PEN_SERVICE = "983dd3da-d46f-bc05-0100-00c278b6b50a";
// the characteristics differ only in the two digits before c278b6b50a
const onePenCharacteristic = (number) => `983dd3da-d46f-bc05-0100-${String(number).padStart(2, "0")}c278b6b50a`;
// the live values. 05 holds the readings saved by a press of the pen's button: a subscribe makes the pen send
// and delete them, so it is never subscribed, as in the datastreamer
const ONE_PEN_LIVE = [1, 2, 3];
// subscribed too, as the datastreamer does: 04 device info, 06. not needed for the live values, so a failure is ignored
const ONE_PEN_OTHERS = [4, 6];

// the pen of the stream, and its characteristics subscribed: what dropOnePenStream lets go
let onePen = null;
let onePenCharacteristics = [];
let onePenConnecting = false;

async function connectOnePen() {
  if (onePenConnecting) return;
  onePenConnecting = true;
  // from the click to the end: the chooser open, then the connection being made
  emitEvent("one_pen_connecting", { connecting: true });
  try {
    if (!navigator.bluetooth) throw new Error("this browser has no Web Bluetooth: use Chrome on http://localhost");
    const device = await navigator.bluetooth.requestDevice({ filters: [{ services: [ONE_PEN_SERVICE] }] });
    dropOnePenStream();
    onePen = device;
    onePen.addEventListener("gattserverdisconnected", handleOnePenDisconnected);
    const service = await (await onePen.gatt.connect()).getPrimaryService(ONE_PEN_SERVICE);
    for (const number of ONE_PEN_LIVE) await subscribeOnePen(service, number);
    for (const number of ONE_PEN_OTHERS) await subscribeOnePen(service, number).catch(console.warn);
    emitEvent("one_pen_connected", { name: onePen.name || "" });
  } catch (error) {
    // NotFoundError: the chooser was closed without a pen, nothing started
    if (error.name !== "NotFoundError") {
      // quietly: the error tells Python the connection is gone
      dropOnePenStream();
      emitEvent("one_pen_error", { message: String(error.message || error) });
    }
  } finally {
    onePenConnecting = false;
    emitEvent("one_pen_connecting", { connecting: false });
  }
}

function disconnectOnePen() {
  // handleOnePenDisconnected tells Python. nothing happens without a pen connected
  onePen?.gatt.disconnect();
}

function dropOnePenStream() {
  // no event of the previous connection reaches Python again
  for (const characteristic of onePenCharacteristics) {
    characteristic.removeEventListener("characteristicvaluechanged", handleOnePenNotify);
    // only while still connected: else there is nothing to stop
    characteristic.stopNotifications().catch(() => {});
  }
  onePenCharacteristics = [];
  if (onePen) {
    onePen.removeEventListener("gattserverdisconnected", handleOnePenDisconnected);
    if (onePen.gatt.connected) onePen.gatt.disconnect();
  }
}

async function subscribeOnePen(service, number) {
  const characteristic = await service.getCharacteristic(onePenCharacteristic(number));
  characteristic.addEventListener("characteristicvaluechanged", handleOnePenNotify);
  onePenCharacteristics.push(characteristic);
  await characteristic.startNotifications();
}

function handleOnePenNotify(event) {
  const bytes = new Uint8Array(event.target.value.buffer);
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  emitEvent("one_pen_notify", { uuid: event.target.uuid, hex });
}

function handleOnePenDisconnected() {
  emitEvent("one_pen_disconnected");
}
