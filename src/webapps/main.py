from nicegui import ui

# the service a OnePen advertises, as ONEPEN_SERVICE in bluelab_datastreamer/onepen_bridge.py
ONEPEN_SERVICE = "983dd3da-d46f-bc05-0100-00c278b6b50a"

# web bluetooth has no python api: the browser talks to the pen, and sends every notification to the
# server with emitEvent. it runs in the click handler, because requestDevice needs a user gesture
CONNECT_PEN = f"""async () => {{
    const device = await navigator.bluetooth.requestDevice({{filters: [{{services: ["{ONEPEN_SERVICE}"]}}]}});
    window.onePen = device;
    const server = await device.gatt.connect();
    const service = await server.getPrimaryService("{ONEPEN_SERVICE}");
    for (const char of await service.getCharacteristics()) {{
        if (!char.properties.notify) continue;
        char.addEventListener("characteristicvaluechanged", (e) => {{
            const v = e.target.value;
            const hex = Array.from(new Uint8Array(v.buffer, v.byteOffset, v.byteLength),
                b => b.toString(16).padStart(2, "0")).join("");
            emitEvent("pen_notify", {{uuid: char.uuid, hex}});
        }});
        await char.startNotifications();
    }}
}}"""


@ui.page("/")
def index():
    with ui.row():
        ui.button("Connect OnePen").on("click", js_handler=CONNECT_PEN)
        ui.button("Disconnect").on("click", js_handler="() => window.onePen?.gatt.disconnect()")
    log = ui.log().classes("w-full h-96")
    ui.on("pen_notify", lambda e: log.push(f"{e.args['uuid']} {e.args['hex']}"))


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Web apps", show=False)
