"""Backend of the OnePen: connects to the bridge (ble_bridge.py) and does everything with the bytes.

Every press of the pen's button saves a reading on the pen. This subscribes to 05 again every
--poll seconds, because the pen sends its saved readings only right after a subscribe, and
deletes them once sent.

At the start, the morning or the afternoon is chosen with the up and down arrows and enter. Each
has its own rooms, in ROOMS, and the csv may hold rows of the chosen one only. Once every room of
it is done, the csv is copied to --daily-dir as yymmdd-1.csv for the morning or yymmdd-2.csv for
the afternoon, and emptied to its header.

The readings are taken a room at a time, 4 per room, in the order of ROOMS. A room starts with
its 4 lines on screen and the water amounts in ml are typed first, one per line (enter goes to
the next empty line, backspace or delete removes one digit, and on an empty line goes back to the
one before). When every line has its ml, the first line streams the live readings, and a press
of the button (or enter) records them in that line, beeps and moves on to the next empty one.
Backspace or delete removes the reading of the line, and on a line without one goes back to the
line before. The up and down arrows move between the lines in both, the right arrow goes from the
ml to the readings at any time, and the left arrow back to the ml, as they are on the line. When every line of one is
filled, the next empty line of the other is taken. A value the pen has not got, such as with the
probe in the air, shows as n.a., a line not recorded yet as -. When every line has both its ml
and its reading, a confirmation is shown below the lines (up goes back to change them). Enter on
it appends the room to datastreamer.csv, next to
this file, in the shape of a journal entries export, and the next room starts. A room that is not
complete when q is pressed is not written. The room continues from the last row of the csv, so
rows can be deleted by hand between rooms.

    uv run --no-project src\\bluelab_datastreamer\\datastreamer.py

What the bytes mean is in edenic_decompiling_result.md, next to this file. Only the standard
library is used. From a container, pass --host host.docker.internal and run it in an interactive
terminal (docker exec -it), or no key can be read.
"""

import argparse
import asyncio
import csv
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from pathlib import Path

if os.name == "nt":
    import msvcrt
    import winsound
else:
    import select
    import termios
    import tty

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
RECONNECT_DELAY_SECONDS = 2
DEFAULT_POLL_SECONDS = 0.5
KEY_POLL_SECONDS = 0.05
CSV_RETRY_SECONDS = 1

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
# the rooms of each part of the day, in the order they are taken. which one is asked at the start
ROOMS = {
    "morning": ("1.30", "1.29", "1.28", "1.27", "1.26", "1.25", "1.24", "0.31", "0.32", "0.33"),
    "afternoon": ("1.23", "1.22", "1.21", "1.20", "1.19", "1.18", "1.17", "0.27", "0.28", "0.29"),
}
# once every room of the part of the day is done, the csv is moved to this folder, named by the
# date and the number of the part of the day, such as 261020-1.csv
DEFAULT_DAILY_DIR = Path(r"C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\Leone\Drip and Drain\daily_raw_csv")
PART_NUMBERS = {"morning": 1, "afternoon": 2}
CHOOSE_HINT = "MORNING OR AFTERNOON? UP AND DOWN TO CHOOSE, ENTER TO CONFIRM, Q TO QUIT"
READINGS_PER_ROOM = 4
ROOM_SEPARATOR = "-" * 25
# terminal escape codes. the lines of the room are redrawn by moving the cursor up over them and
# clearing the screen from there down
UP = "\x1b[{}A"
CLEAR_DOWN = "\r\x1b[J"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
# what can be typed or recorded on the active line is yellow, the rest in the terminal's own colour
YELLOW = "\x1b[33m"
RESET_COLOR = "\x1b[0m"
TYPE_HINT = "TYPE THE ML AMOUNT, RIGHT TO MEASURE, Q TO QUIT"
RECORD_HINT = "PRESS BUTTON OR ENTER TO TAKE MEASUREMENT, LEFT FOR ML, Q TO QUIT"
RECORDED_HINT = "BACKSPACE TO DELETE THE MEASUREMENT, LEFT FOR ML, Q TO QUIT"
CONFIRM_HINT = "ENTER TO CONFIRM, IT CANNOT BE CHANGED AFTER. UP TO CHANGE IT, Q TO QUIT"
# the lines of a room, in the order they are taken
LINE_NAMES = ("Drip Left", "Drip Right", "Drain Left", "Drain Right")
LINE_NAME_WIDTH = max(len(line_name) for line_name in LINE_NAMES)
SEPARATOR = " || "
# every value is padded to the width of one such as 7.46, 0.42 or 26.1, so the | line up
VALUE_WIDTH = 4
NOT_RECORDED = "-"
NOT_AVAILABLE = "n.a."
ENTER = ("\r", "\n")
# the keys that are more than one character are given these names, which no single key can be
ARROW_UP = "up"
ARROW_DOWN = "down"
ARROW_LEFT = "left"
ARROW_RIGHT = "right"
DELETE = "delete"
DELETE_KEYS = ("\b", "\x7f", DELETE)
# on windows, a function or arrow key comes as one of these, followed by its code
WINDOWS_KEY_PREFIXES = ("\x00", "\xe0")
WINDOWS_KEYS = {"H": ARROW_UP, "P": ARROW_DOWN, "K": ARROW_LEFT, "M": ARROW_RIGHT, "S": DELETE}
# outside windows, they come as an escape sequence. the ones with O are the arrows in the cursor
# mode some terminals switch to
ESCAPE_SEQUENCE = re.compile(r"\x1b(\[[0-9;]*[A-Za-z~]|O[A-Za-z])?")
ESCAPE_KEYS = {
    "\x1b[A": ARROW_UP,
    "\x1bOA": ARROW_UP,
    "\x1b[B": ARROW_DOWN,
    "\x1bOB": ARROW_DOWN,
    "\x1b[D": ARROW_LEFT,
    "\x1bOD": ARROW_LEFT,
    "\x1b[C": ARROW_RIGHT,
    "\x1bOC": ARROW_RIGHT,
    "\x1b[3~": DELETE,
}


def characteristic(number: int) -> str:
    # the characteristics of the pen service differ only in the two digits before c278b6b50a
    return f"983dd3da-d46f-bc05-0100-{number:02d}c278b6b50a"


PEN_CHARACTERISTICS = {characteristic(number): f"{number:02d}" for number in range(1, 7)}
DEVICE_INFO = characteristic(4)
SAVED_READINGS = characteristic(5)
LIVE_READINGS = {characteristic(number) for number in (1, 2, 3)}
# byte 0 of a live reading is a tag that says which quantity its first value is
LIVE_TAGS = {ord("P"): "ph", ord("E"): "ec", ord("T"): "temperature"}
SAVED_READINGS_PER_PACKET = 3
SAVED_READING_SIZE = 9
# the mantissa of a value the pen has not got, such as ec with the probe dry (f1d806)
NO_READING = -9999


@dataclass
class Room:
    """The room being taken: the ml typed first, then the readings recorded, one per line."""

    name: str
    lines: int
    # an empty string for a line without ml, None for a line without a reading
    ml: list[str] = field(init=False)
    readings: list[dict | None] = field(init=False)
    # the line the arrows are on, which typing or a reading goes to. one past the last line is the
    # confirmation, which can be gone to only when the room is complete
    line: int = 0
    typing_ml: bool = True
    # true once the room is confirmed, while it is written to the csv. it cannot be changed after
    saving: bool = False

    def __post_init__(self) -> None:
        self.ml = [""] * self.lines
        self.readings = [None] * self.lines

    @property
    def complete(self) -> bool:
        return all(self.ml) and all(self.readings)

    @property
    def confirming(self) -> bool:
        return self.line == self.lines


ids = count(1)
# the commands sent and not answered yet, by id, so a failure can be printed with its command
pending: dict[int, tuple[str, str]] = {}
pen_name = ""
# the latest live values, shown on the line being recorded
live: dict[str, float | None] = dict.fromkeys(LIVE_TAGS.values())
# the part of the day chosen at the start, a key of ROOMS
part_of_day = ""
daily_dir = DEFAULT_DAILY_DIR
# None before the first room and after the last
room: Room | None = None
# the lines of the room on screen, which the next draw moves up over
drawn = 0
# the terminal settings at the start, outside windows: keys are read one at a time without them.
# None when stdin is not a terminal
terminal_settings: list | None = None


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


def next_room(rows: list[dict], rooms: tuple[str, ...]) -> tuple[str, int] | None:
    """The room of rooms that continues from the last row, and the readings it still needs. None when every room is done.

    Every row must be of rooms: a csv of the other part of the day is not continued.
    """
    others = sorted({row["tags"] for row in rows} - set(rooms))
    if others:
        raise ValueError(f"{CSV_PATH.name} has rows with tags {', '.join(others)}, which are not rooms of this part of the day")
    if not rows:
        return rooms[0], READINGS_PER_ROOM
    last = rows[-1]["tags"]
    index = rooms.index(last)
    # the rows of the last room are the ones at the end with its tags
    in_room = 0
    for row in reversed(rows):
        if row["tags"] != last:
            break
        in_room += 1
    if in_room < READINGS_PER_ROOM:
        return rooms[index], READINGS_PER_ROOM - in_room
    return (rooms[index + 1], READINGS_PER_ROOM) if index + 1 < len(rooms) else None


def append_rows(rows: list[dict]) -> None:
    # a hand edit can leave empty lines (blank, or only commas when excel empties a row) at the end,
    # or no newline after the last row, so they are removed before the rows are appended
    content = CSV_PATH.read_text()
    lines = content.splitlines()
    while len(lines) > 1 and not lines[-1].strip(" ,\t"):
        lines.pop()
    tidy = "\n".join(lines) + "\n"
    if tidy != content:
        CSV_PATH.write_text(tidy)
    with CSV_PATH.open("a", newline="") as file:
        csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerows(rows)


def csv_values(ec: float | None, ph: float | None, temperature: float | None) -> dict:
    """The values as the csv stores them, an empty string for none."""
    # a dry probe has no ec, and its ph and temperature are not of the water either
    if ec is None:
        return {"ec": "", "ph": "", "temp": ""}
    return {
        "ec": f"{ec:.2f}",
        "ph": "" if ph is None else f"{ph:.2f}",
        "temp": "" if temperature is None else f"{temperature:.1f}",
    }


NO_VALUES = csv_values(None, None, None)


def values_text(values: dict, missing: str) -> str:
    shown = {key: (values[key] or missing).ljust(VALUE_WIDTH) for key in values}
    return f"PH: {shown['ph']} | EC: {shown['ec']} | T: {shown['temp']}"


def room_separator(name: str | None) -> str:
    message = f"NEXT ROOM IS {name}" if name else "ALL ROOMS DONE, PRESS Q TO QUIT"
    return f"{ROOM_SEPARATOR} {message}   {ROOM_SEPARATOR}"


def fit(parts: list[tuple[str, bool]]) -> str:
    """The parts of a line, yellow where marked, cut to the terminal width.

    A line that wrapped would take two lines on screen, and the next draw would move up too few.
    """
    width_left = shutil.get_terminal_size().columns - 1
    line = ""
    for text, yellow in parts:
        text = text[:width_left]
        width_left -= len(text)
        line += f"{YELLOW}{text}{RESET_COLOR}" if yellow else text
    return line


def room_lines(current: Room) -> list[str]:
    lines = []
    # a room continued from the csv has only its last lines left
    names = LINE_NAMES[READINGS_PER_ROOM - current.lines :]
    for index in range(current.lines):
        start = f"[{current.name}] {names[index].ljust(LINE_NAME_WIDTH)}{SEPARATOR}"
        ml = f"ML: {(current.ml[index] or NOT_RECORDED).ljust(VALUE_WIDTH)}"
        reading = current.readings[index]
        values = values_text(reading, NOT_AVAILABLE) if reading else values_text(NO_VALUES, NOT_RECORDED)
        active = index == current.line and not current.saving
        if active and current.typing_ml:
            parts = [(start, False), (ml, True), (f"{SEPARATOR}{values}{SEPARATOR}", False), (TYPE_HINT, True)]
        elif active and reading is None:
            # - until the pen has sent a live value, n.a. for the ones it has not got after that
            missing = NOT_AVAILABLE if any(live_value is not None for live_value in live.values()) else NOT_RECORDED
            live_values = values_text(csv_values(**live), missing)
            parts = [(f"{start}{ml}{SEPARATOR}", False), (live_values, True), (SEPARATOR, False), (RECORD_HINT, True)]
        elif active:
            parts = [(f"{start}{ml}{SEPARATOR}", False), (values, True), (SEPARATOR, False), (RECORDED_HINT, True)]
        else:
            parts = [(f"{start}{ml}{SEPARATOR}{values}", False)]
        lines.append(fit(parts))
    if current.saving:
        lines.append(fit([(f"> ROOM {current.name} CONFIRMED", False)]))
    elif current.confirming:
        lines.append(fit([(f"> CONFIRM ROOM {current.name}", True), (SEPARATOR, False), (CONFIRM_HINT, True)]))
    elif current.complete:
        lines.append(fit([(f"> CONFIRM ROOM {current.name}", False)]))
    return lines


def draw() -> None:
    """Redraws the separator and the lines of the room, in place of the ones on screen."""
    global drawn
    # the separator is drawn with the room, so what say prints goes above it
    lines = [room_separator(room.name)] + room_lines(room) if room is not None else []
    print((UP.format(drawn) if drawn else "") + CLEAR_DOWN + "".join(f"{line}\n" for line in lines), end="", flush=True)
    drawn = len(lines)


def say(text: str) -> None:
    """Prints a line that stays, above the lines of the room."""
    global drawn
    print((UP.format(drawn) if drawn else "") + CLEAR_DOWN + text, flush=True)
    drawn = 0
    draw()


def beep() -> None:
    if os.name == "nt":
        # plays the windows default sound without blocking
        winsound.MessageBeep()
    else:
        print("\a", end="", flush=True)


def keys_pressed() -> list[str]:
    """The keys pressed since the last call, without waiting. An arrow or delete comes by its name.

    A key this does not know that is more than one character is left out, as its characters could
    be read as a digit or a q.
    """
    keys = []
    if os.name == "nt":
        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in WINDOWS_KEY_PREFIXES:
                key = WINDOWS_KEYS.get(msvcrt.getwch())
            if key is not None:
                keys.append(key)
        return keys
    if terminal_settings is None or not select.select([sys.stdin], [], [], 0)[0]:
        return keys
    # read straight from the terminal, so an escape sequence comes whole and none of it stays
    # behind in the buffer of sys.stdin, where select does not see it
    text = os.read(sys.stdin.fileno(), 64).decode(errors="ignore")
    while text:
        escape = ESCAPE_SEQUENCE.match(text)
        if escape:
            key, text = ESCAPE_KEYS.get(escape.group()), text[escape.end() :]
        else:
            key, text = text[0], text[1:]
        if key is not None:
            keys.append(key)
    return keys


def archive_csv() -> Path:
    """Copies the csv to the daily folder and leaves it with its header only. Never overwrites a file there."""
    target = daily_dir / f"{datetime.now():%y%m%d}-{PART_NUMBERS[part_of_day]}.csv"
    if target.exists():
        raise FileExistsError(f"{target} exists already")
    shutil.copyfile(CSV_PATH, target)
    CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
    return target


def start_room() -> None:
    """Starts the room that continues from the csv, or archives the csv when every room is done."""
    global room
    try:
        following = next_room(read_csv(), ROOMS[part_of_day])
    except ValueError as error:
        room = None
        say(f"# no room can start: {error}")
        return
    room = Room(*following) if following else None
    if room is not None:
        draw()
        return
    try:
        say(f"# {CSV_PATH.name} saved as {archive_csv()} and emptied")
    except OSError as error:
        # the csv is kept as it is, so it can be saved by hand
        say(f"# {CSV_PATH.name} not saved to the daily folder, and not emptied: {error}")
    say(room_separator(None))


async def save_room() -> None:
    """Appends the recorded room to the csv and starts the next one."""
    global drawn
    rows = []
    for ml, reading in zip(room.ml, room.readings):
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            subject=f"{pen_name} - Measurement",
            notes=str(int(ml)),
            type="measurement",
            tags=room.name,
            **reading,
        )
        rows.append(row)
    while True:
        try:
            append_rows(rows)
            break
        except PermissionError:
            say(f"# {CSV_PATH.name} is open in another program, close it. trying again every {CSV_RETRY_SECONDS} s")
            await asyncio.sleep(CSV_RETRY_SECONDS)
    # the lines of the saved room stay on screen, the next room is drawn below them
    drawn = 0
    start_room()


def next_empty(values: list, start: int) -> int | None:
    """The first empty line from start on, going round to the top. None when every line is filled."""
    for offset in range(len(values)):
        index = (start + offset) % len(values)
        if not values[index]:
            return index
    return None


def record(date_time: str, ec: float | None, ph: float | None, temperature: float | None) -> None:
    """Puts a reading in the line of the room the arrows are on."""
    if room is None:
        say("# reading ignored, every room is done")
        return
    if room.typing_ml:
        say("# reading ignored, press right to measure")
        return
    if room.saving:
        say("# reading ignored, the room is being written to the csv")
        return
    if room.confirming:
        say("# reading ignored, the room is complete. confirm it, or go up to change it")
        return
    if room.readings[room.line] is not None:
        say("# reading ignored, the line has one already. delete it first")
        return
    room.readings[room.line] = {"date_time": date_time, **csv_values(ec, ph, temperature)}
    beep()
    advance(room.readings)
    draw()


def advance(values: list) -> None:
    """After a line is filled: goes to the next empty line, or to the other mode when every line of this one is filled.

    When every line has both its ml and its reading, goes to the confirmation.
    """
    following = next_empty(values, room.line)
    if following is not None:
        room.line = following
        return
    following = next_empty(room.readings if room.typing_ml else room.ml, 0)
    if following is None:
        room.line = room.lines
        return
    room.typing_ml = not room.typing_ml
    room.line = following


def record_live() -> None:
    if all(reading is None for reading in live.values()):
        say("# no live values yet, nothing recorded")
        return
    # the same time format as the bridge's
    record(datetime.now().isoformat(timespec="microseconds"), live["ec"], live["ph"], live["temperature"])


def type_ml(key: str) -> None:
    if key.isdecimal() and key.isascii():
        room.ml[room.line] += key
    elif key in DELETE_KEYS:
        if room.ml[room.line]:
            room.ml[room.line] = room.ml[room.line][:-1]
        elif room.line > 0:
            # back to the line before, to correct it
            room.line -= 1
    elif key in ENTER and room.ml[room.line]:
        advance(room.ml)
    draw()


def measure(key: str) -> None:
    if key in ENTER:
        # record draws
        record_live()
        return
    if key in DELETE_KEYS:
        if room.readings[room.line] is not None:
            room.readings[room.line] = None
        elif room.line > 0:
            room.line -= 1
    draw()


def confirm(key: str) -> None:
    if key in ENTER:
        room.saving = True
        asyncio.create_task(save_room())
    elif key in DELETE_KEYS:
        room.line -= 1
    draw()


def switch_mode(key: str) -> None:
    """Right goes from the ml to the readings, left from the readings back to the ml, as they are on the line."""
    room.typing_ml = key == ARROW_LEFT
    draw()


async def read_keys() -> None:
    """Types the ml, records the live values on enter, moves between the lines on the arrows, and returns on q."""
    while True:
        await asyncio.sleep(KEY_POLL_SECONDS)
        for key in keys_pressed():
            if key.lower() == "q":
                return
            if room is None or room.saving:
                continue
            if key in (ARROW_UP, ARROW_DOWN):
                last = room.lines if room.complete else room.lines - 1
                room.line = max(0, min(last, room.line + (1 if key == ARROW_DOWN else -1)))
                draw()
            elif key in (ARROW_LEFT, ARROW_RIGHT):
                switch_mode(key)
            elif room.confirming:
                confirm(key)
            elif room.typing_ml:
                type_ml(key)
            else:
                measure(key)


async def choose_part_of_day() -> str | None:
    """Asks for the morning or the afternoon, with the arrows and enter. None on q."""
    names = list(ROOMS)
    chosen = 0
    # the hint and a line per name, drawn the same way as the lines of a room, over the ones on screen
    lines = len(names) + 1
    shown: int | None = None
    while True:
        if shown != chosen:
            text = "".join(f"{fit([(f'> {name}', index == chosen)])}\n" for index, name in enumerate(names))
            print((UP.format(lines) if shown is not None else "") + CLEAR_DOWN + fit([(CHOOSE_HINT, True)]) + "\n" + text, end="", flush=True)
            shown = chosen
        await asyncio.sleep(KEY_POLL_SECONDS)
        for key in keys_pressed():
            if key.lower() == "q":
                return None
            if key in ENTER:
                # the choice goes from the screen, the caller says which one it was
                print(UP.format(lines) + CLEAR_DOWN, end="", flush=True)
                return names[chosen]
            if key in (ARROW_UP, ARROW_DOWN):
                chosen = max(0, min(len(names) - 1, chosen + (1 if key == ARROW_DOWN else -1)))


def command(writer: asyncio.StreamWriter, op: str, uuid: str, **fields: str) -> None:
    request_id = next(ids)
    pending[request_id] = (op, uuid)
    writer.write((json.dumps({"id": request_id, "op": op, "uuid": uuid, **fields}) + "\n").encode())


def on_notify(message: dict) -> None:
    data = bytes.fromhex(message["hex"])
    if message["uuid"] in LIVE_READINGS:
        # the tag, not the characteristic, says which quantity it is
        if data and data[0] in LIVE_TAGS:
            live[LIVE_TAGS[data[0]]] = value(data[1:4])
            if room is not None and not room.typing_ml:
                draw()
        return
    # an empty list of saved readings comes as a packet of zeros after every subscribe
    if message["uuid"] != SAVED_READINGS or not any(data):
        return
    # more than one reading in a packet only if several were saved between two polls
    for reading in saved_readings(data):
        record(message["time"], *reading)


def on_message(message: dict) -> None:
    global pen_name
    kind = message["type"]
    if kind == "notify":
        on_notify(message)
    elif kind == "result":
        op, uuid = pending.pop(message["id"], ("command", str(message["id"])))
        if "error" in message:
            say(f"# {op} {name(uuid)} failed: {message['error']}")
        elif op == "read" and uuid == DEVICE_INFO:
            # byte 1 of 04 is the battery in percent
            say(f"# battery {bytes.fromhex(message['hex'])[1]}%")
    elif kind == "connected":
        pen_name = message["name"]
        say(f"# pen {message['name']} {message['address']} connected")
    else:
        if kind == "disconnected":
            # so the line being recorded does not show the values of a pen that is gone
            live.update(dict.fromkeys(live))
        say(f"# {json.dumps(message)}")


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
            say(f"# bridge not reachable: {error!r}")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            continue

        say(f"# connected to the bridge at {host}:{port}")
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

        live.update(dict.fromkeys(live))
        say("# bridge disconnected")
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
    parser.add_argument(
        "--daily-dir",
        type=Path,
        default=DEFAULT_DAILY_DIR,
        help=f"folder the csv is saved to once every room is done (default {DEFAULT_DAILY_DIR})",
    )
    args = parser.parse_args()
    global part_of_day, daily_dir
    daily_dir = args.daily_dir
    if os.name == "nt":
        # an empty command switches the windows console to understand the escape codes
        os.system("")
    print(HIDE_CURSOR, end="", flush=True)
    # fails at the start rather than at the first room when the csv cannot be used
    rows = read_csv()
    chosen = await choose_part_of_day()
    if chosen is None:
        return
    part_of_day = chosen
    next_room(rows, ROOMS[part_of_day])
    say(f"# {part_of_day}, {CSV_PATH.name}: {len(rows)} rows")
    start_room()
    # q ends read_keys, which stops the stream. an error in either ends both
    tasks = {asyncio.create_task(read_keys()), asyncio.create_task(stream(args.host, args.port, args.poll))}
    done, running = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in running:
        task.cancel()
    for task in done:
        task.result()


if __name__ == "__main__":
    if os.name != "nt" and sys.stdin.isatty():
        terminal_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        if terminal_settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, terminal_settings)
        print(SHOW_CURSOR, end="")
        if room is not None and not room.saving and (any(room.ml) or any(room.readings)):
            print(f"# room {room.name} not complete, not written to {CSV_PATH.name}")
