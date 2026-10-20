"""Backend of the OnePen: connects to the bridge (ble_bridge.py) and does everything with the bytes.

Every press of the pen's button saves a reading on the pen. This subscribes to 05 again every
--poll seconds, because the pen sends its saved readings only right after a subscribe, and
deletes them once sent. For each reading it asks for the water amount in ml and appends a row to
datastreamer.csv, next to this file, in the shape of a journal entries export. The room (tags)
continues from the last row of the csv: 4 readings per room, in the order of ROOMS. Rows can be
deleted by hand between readings, the next one continues from whatever is the last row then.

    uv run --no-project src\\bluelab_datastreamer\\datastreamer.py

What the bytes mean is in edenic_decompiling_result.md, next to this file. Only the standard
library is used. From a container, pass --host host.docker.internal.
"""

import argparse
import asyncio
import csv
import json
import os
from itertools import count
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
RECONNECT_DELAY_SECONDS = 2
DEFAULT_POLL_SECONDS = 0.5

CSV_PATH = Path(__file__).with_suffix(".csv")
CSV_COLUMNS = (
    "date_time",
    "subject",
    "notes",
    "type",
    "ec",
    "ec_pore",
    "ec_bulk",
    "ph",
    "mc",
    "temp",
    "device",
    "media",
    "tags",
)
ROOMS = ("1.30", "1.29", "1.28", "1.27", "1.26", "1.25", "1.24", "0.33", "0.32", "0.31")
READINGS_PER_ROOM = 4
ROOM_SEPARATOR = "-" * 25
# terminal escape codes: cursor one line up, then clear that line
ERASE_LINE = "\x1b[1A\x1b[2K"


def characteristic(number: int) -> str:
    # the characteristics of the pen service differ only in the two digits before c278b6b50a
    return f"983dd3da-d46f-bc05-0100-{number:02d}c278b6b50a"


PEN_CHARACTERISTICS = {characteristic(number): f"{number:02d}" for number in range(1, 7)}
DEVICE_INFO = characteristic(4)
SAVED_READINGS = characteristic(5)
SAVED_READINGS_PER_PACKET = 3
SAVED_READING_SIZE = 9
# the mantissa of a value the pen has not got, such as ec with the probe dry (f1d806)
NO_READING = -9999

ids = count(1)
# the commands sent and not answered yet, by id, so a failure can be printed with its command
pending: dict[int, tuple[str, str]] = {}
pen_name = ""
# true while the ml of a reading is being asked: readings that arrive then are thrown away
asking = False


def name(uuid: str) -> str:
    return PEN_CHARACTERISTICS.get(uuid, uuid)


def value(group: bytes) -> float | None:
    # mantissa as int16 little endian, then the exponent as int8: a negative one multiplies
    mantissa = int.from_bytes(group[:2], "little", signed=True)
    if mantissa == NO_READING:
        return None
    exponent = int.from_bytes(group[2:3], "little", signed=True)
    return mantissa / 10**exponent if exponent >= 0 else mantissa * 10**-exponent


def saved_readings(data: bytes) -> list[tuple[float | None, float | None, float | None]]:
    # byte 0 is a count, then up to 3 readings of ec, ph and temperature. whether the count is the
    # readings in this packet or the readings still to come is not known yet
    readings = []
    for index in range(min(data[0], SAVED_READINGS_PER_PACKET)):
        start = 1 + index * SAVED_READING_SIZE
        ec, ph, temperature = (value(data[start + offset : start + offset + 3]) for offset in (0, 3, 6))
        readings.append((ec, ph, temperature))
    return readings


def read_csv() -> list[dict]:
    """The rows of the csv, without empty lines. Creates the csv with its header if it is missing or empty."""
    if not CSV_PATH.exists() or not CSV_PATH.read_text().strip():
        CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
    with CSV_PATH.open(newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(f"the header of {CSV_PATH.name} is not {','.join(CSV_COLUMNS)}")
        return [row for row in reader if any((cell or "").strip() for cell in row.values())]


def next_room(rows: list[dict]) -> str | None:
    """The room of the next reading, continuing from the last row. None when every room is done."""
    if not rows:
        return ROOMS[0]
    last = rows[-1]["tags"]
    if last not in ROOMS:
        raise ValueError(f"the last row of {CSV_PATH.name} has tags {last!r}, which is not a room")
    index = ROOMS.index(last)
    # the rows of the last room are the ones at the end with its tags
    in_room = 0
    for row in reversed(rows):
        if row["tags"] != last:
            break
        in_room += 1
    if in_room < READINGS_PER_ROOM:
        return ROOMS[index]
    return ROOMS[index + 1] if index + 1 < len(ROOMS) else None


def append_row(row: dict) -> None:
    # a hand edit can leave empty lines (blank, or only commas when excel empties a row) at the end,
    # or no newline after the last row, so they are removed before the row is appended
    content = CSV_PATH.read_text()
    lines = content.splitlines()
    while len(lines) > 1 and not lines[-1].strip(" ,\t"):
        lines.pop()
    tidy = "\n".join(lines) + "\n"
    if tidy != content:
        CSV_PATH.write_text(tidy)
    with CSV_PATH.open("a", newline="") as file:
        csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerow(row)


def ask_ml(room: str) -> str:
    # the prompt and any retries are erased once answered, so only the saved rows stay on screen
    lines = 0
    while True:
        answer = input(f"ml for room {room} (empty to discard): ").strip()
        lines += 1
        if answer == "" or answer.isdecimal():
            print(ERASE_LINE * lines, end="", flush=True)
            return answer
        print("not a whole number, try again")
        lines += 1


async def record(date_time: str, ec: float | None, ph: float | None, temperature: float | None) -> None:
    """Asks the ml of one reading and appends it to the csv."""
    global asking
    asking = True
    try:
        room = next_room(read_csv())
        if room is None:
            print("# all rooms done, reading ignored", flush=True)
            return
        # a dry probe has no ec, and its ph and temperature are not of the water either
        if ec is None:
            values = {"ec": "", "ph": "", "temp": ""}
        else:
            values = {
                "ec": f"{ec:.2f}",
                "ph": "" if ph is None else f"{ph:.2f}",
                "temp": "" if temperature is None else f"{temperature:.1f}",
            }
        # input blocks, so it runs in a thread to keep the bridge's messages coming
        ml = await asyncio.to_thread(ask_ml, room)
        if ml == "":
            print("# reading discarded", flush=True)
            return
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            date_time=date_time,
            subject=f"{pen_name} - Measurement",
            notes=str(int(ml)),
            type="measurement",
            tags=room,
            **values,
        )
        while True:
            try:
                append_row(row)
                break
            except PermissionError:
                await asyncio.to_thread(input, f"{CSV_PATH.name} is open in another program, close it and press enter")
        saved = {key: values[key] or "-" for key in values}
        line = f"ROOM: {room} | PH: {saved['ph']} | EC: {saved['ec']} | T: {saved['temp']} | ML: {row['notes']}"
        print(line, flush=True)
        # the room is full once the next reading goes elsewhere
        if next_room(read_csv()) != room:
            print(ROOM_SEPARATOR, flush=True)
    except ValueError as error:
        print(f"# reading ignored: {error}", flush=True)
    finally:
        asking = False


async def record_all(date_time: str, readings: list) -> None:
    # more than one reading in a packet only if several were saved between two polls
    for reading in readings:
        await record(date_time, *reading)


def command(writer: asyncio.StreamWriter, op: str, uuid: str, **fields: str) -> None:
    request_id = next(ids)
    pending[request_id] = (op, uuid)
    writer.write((json.dumps({"id": request_id, "op": op, "uuid": uuid, **fields}) + "\n").encode())


def on_notify(message: dict) -> None:
    # only the saved readings are used. an empty list comes as a packet of zeros after every subscribe
    data = bytes.fromhex(message["hex"])
    if message["uuid"] != SAVED_READINGS or not any(data):
        return
    if asking:
        print("\n# reading ignored, the ml of the previous one is being asked", flush=True)
        return
    asyncio.create_task(record_all(message["time"], saved_readings(data)))


def on_message(message: dict) -> None:
    global pen_name
    kind = message["type"]
    if kind == "notify":
        on_notify(message)
    elif kind == "result":
        op, uuid = pending.pop(message["id"], ("command", str(message["id"])))
        if "error" in message:
            print(f"# {op} {name(uuid)} failed: {message['error']}", flush=True)
        elif op == "read" and uuid == DEVICE_INFO:
            # byte 1 of 04 is the battery in percent
            print(f"# battery {bytes.fromhex(message['hex'])[1]}%", flush=True)
    elif kind == "connected":
        pen_name = message["name"]
        print(f"# pen {message['name']} {message['address']} connected", flush=True)
    else:
        print(f"# {json.dumps(message)}", flush=True)


async def poll_saved_readings(writer: asyncio.StreamWriter, poll_seconds: float) -> None:
    while True:
        await asyncio.sleep(poll_seconds)
        command(writer, "unsubscribe", SAVED_READINGS)
        command(writer, "subscribe", SAVED_READINGS)
        await writer.drain()


async def stream(host: str, port: int, poll_seconds: float) -> None:
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except OSError as error:
            print(f"# bridge not reachable: {error!r}", flush=True)
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            continue

        print(f"# connected to the bridge at {host}:{port}", flush=True)
        poller: asyncio.Task | None = None
        try:
            async for line in reader:
                message = json.loads(line)
                on_message(message)
                if message["type"] == "connected":
                    # subscriptions end with every pen connection, so they are made again on each
                    command(writer, "read", DEVICE_INFO)
                    for uuid in PEN_CHARACTERISTICS:
                        command(writer, "subscribe", uuid)
                    await writer.drain()
                    poller = asyncio.create_task(poll_saved_readings(writer, poll_seconds))
                elif message["type"] == "disconnected" and poller is not None:
                    poller.cancel()
                    poller = None
        except ConnectionError:
            pass
        finally:
            if poller is not None:
                poller.cancel()
            writer.close()
            pending.clear()

        print("# bridge disconnected", flush=True)
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"host of the bridge (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port of the bridge (default {DEFAULT_PORT})")
    parser.add_argument(
        "--poll",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help=f"seconds between subscribes to 05, the saved readings (default {DEFAULT_POLL_SECONDS})",
    )
    args = parser.parse_args()
    if os.name == "nt":
        # an empty command switches the windows console to understand the escape codes of ERASE_LINE
        os.system("")
    # fails at the start rather than at the first reading when the csv cannot be used
    rows = read_csv()
    print(f"# {CSV_PATH.name}: {len(rows)} rows, next room {next_room(rows) or 'none, all rooms done'}", flush=True)
    await stream(args.host, args.port, args.poll)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
