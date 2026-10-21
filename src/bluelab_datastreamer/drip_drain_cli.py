"""Front end of the drip and drain readings: takes those of a part of the day, room by room, on the terminal.

At the start, it asks for the pen to be turned on, which enter confirms. Then the bridge scans
for SCAN_SECONDS: when it finds a single OnePen, that one is taken. Else the pen is chosen with
the up and down arrows and enter, from the OnePens in range that the bridge finds, with the
signal strength of each. Before it is connected to, it asks whether
the name chosen is the one on the back of the pen: yes goes on, no goes back to the list. The
bridge keeps reconnecting to the one chosen until q.

Then the morning or the afternoon, the same way. Each has its own rooms, in ROOMS of
drip_drain.py, and the csv may hold rows of the chosen one only. Once every room of it is done,
the csv is copied to --daily-dir as yymmdd-1.csv for the morning or yymmdd-2.csv for the
afternoon, and emptied to its header. When that file is there already, it asks whether to
overwrite it: no keeps the csv as it is and shows it on screen. The first room is shown once the pen is connected.

The readings are taken a room at a time, 4 per room, in the order of ROOMS. A room starts with
its 4 lines on screen and the water amounts in ml are typed first, one per line (enter goes to
the next empty line, backspace or delete removes the whole amount, and on an empty line goes back to the
one before). When every line has its ml, the first line streams the live readings, and enter
records them in that line and moves on to the next empty one. The button of the pen records
nothing here: what it saves stays on the pen.
Backspace or delete removes the reading of the line, and on a line without one goes back to the
line before. The up and down arrows move between the lines in both, the right arrow goes from the
ml to the readings at any time, and the left arrow back to the ml, as they are on the line. When
every line of one is filled, the next empty line of the other is taken. A value the pen has not
got, such as with the probe in the air, shows as n.a., a line not recorded yet as -. When every
line has both its ml and its reading, a confirmation is shown below the lines (up goes back to
change them). Enter on it appends the room to drip_drain.csv, next to this file, in the shape of
a journal entries export, and the next room starts. While a room is shown, q quits after enter to
confirm (any other key stays and does nothing else), and a room that is not complete then is not
written. s skips the room at any time, after enter to confirm (any other key keeps the room and
does nothing else): what was typed or recorded in it is dropped, nothing of it is
written, and the next room starts. The room continues from the last row of the csv, past
the rooms skipped since the start, so rows can be deleted by hand between rooms. The skips are not
kept after q: a room skipped is taken again when the readings are started again.

It runs in its own container (the datastreamer service, docker/datastreamer/Dockerfile), in an
interactive terminal (no -T), or no key can be read, next to the bridge (onepen_bridge.py) on
Windows. OnePen.cmd, next to this file, starts both. Compose mounts the daily folder at --daily-dir. By
hand, from the repo root:

    docker compose -f compose.yaml -f compose.dev.yaml run --rm datastreamer

This file only draws and reads keys: the pen is in onepen.py, the rooms and the csv in
drip_drain.py, the terminal in cli_terminal.py. Only the standard library is used.
"""

import argparse
import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import TypeVar

import cli_terminal
import drip_drain
from cli_terminal import (
    ARROW_DOWN,
    ARROW_LEFT,
    ARROW_RIGHT,
    ARROW_UP,
    BLINK,
    CYAN,
    DELETE_KEYS,
    ENTER,
    ENTER_TO_CONFIRM,
    KEY_POLL_SECONDS,
    PLAIN,
    YELLOW,
    Screen,
    fit,
)
from drip_drain import CSV_PATH, NO_VALUES, Room
from onepen import BridgeGone, PenClient, label, now

# the bridge runs on windows, outside the container
DEFAULT_HOST = "host.docker.internal"
DEFAULT_PORT = 8765
CSV_RETRY_SECONDS = 1
# how long the bridge scans after the pen is turned on before a single pen found is taken as the only
# one in range. a OnePen advertises several times a second
SCAN_SECONDS = 3

PART_OF_DAY_QUESTION = "MORNING OR AFTERNOON?"
CHOOSE_HINT = "WITH THE KEYBOARD, PRESS UP AND DOWN ARROW KEYS TO CHOOSE, ENTER TO CONFIRM, Q TO QUIT"
PEN_QUESTION = "WHICH PEN?"
PEN_HINT = "WITH THE KEYBOARD, PRESS UP AND DOWN ARROW KEYS TO CHOOSE, ENTER TO CONNECT, Q TO QUIT"
NO_PEN_YET = "  no pen found yet, scanning..."
TYPE_HINT = "TYPE THE ML AMOUNT, RIGHT TO MEASURE, S TO SKIP THE ROOM, Q TO QUIT"
RECORD_HINT = "ENTER TO TAKE MEASUREMENT, LEFT FOR ML, S TO SKIP THE ROOM, Q TO QUIT"
RECORDED_HINT = "BACKSPACE TO DELETE THE MEASUREMENT, LEFT FOR ML, S TO SKIP THE ROOM, Q TO QUIT"
CONFIRM_HINT = "ENTER TO CONFIRM, IT CANNOT BE CHANGED AFTER. UP TO CHANGE IT, S TO SKIP THE ROOM, Q TO QUIT"
SKIP_HINT = "ENTER TO SKIP, WHAT IS IN IT IS LOST. ANY OTHER KEY TO KEEP IT"
QUIT_HINT = "ENTER TO QUIT, A ROOM NOT CONFIRMED IS LOST. ANY OTHER KEY TO STAY"
TURN_ON_QUESTION = "TURN ON THE PEN."
TURN_ON_HINT = "ENTER TO CONFIRM, Q TO QUIT"
TURNED_ON = {"yes": "> the pen is turned on"}
PEN_CHECK_QUESTION = "IS {} WRITTEN ON THE BACK OF THE PEN?"
PEN_CHECKED = {"yes": "> yes", "no": "> no"}
OVERWRITE_QUESTION = "{} IS IN THE DAILY FOLDER ALREADY. OVERWRITE IT?"
# no first, so an enter pressed without reading overwrites nothing
OVERWRITE = {"no": "> no, show the csv on screen", "yes": "> yes, overwrite it"}
ROOM_SEPARATOR = "-" * 25
LINE_NAME_WIDTH = max(len(line_name) for line_name in drip_drain.LINE_NAMES)
SEPARATOR = " || "
# every value is padded to the width of one such as 7.46, 0.42 or 26.1, so the | line up
VALUE_WIDTH = 4
NOT_RECORDED = "-"
NOT_AVAILABLE = "n.a."
T = TypeVar("T")

# the part of the day chosen at the start, a key of ROOMS
part_of_day = ""
daily_dir = drip_drain.DEFAULT_DAILY_DIR
# None before the first room and after the last
room: Room | None = None
# true once every room of the part of the day is done, for the csv to be saved to the daily folder
all_done = False
# the rooms skipped since the start, which leave no row in the csv to continue from
skipped: set[str] = set()
# "s" or "q" after the first press, while the skip or the quit waits for the second. empty otherwise
asked = ""
pen: PenClient | None = None


def values_text(values: dict, missing: str) -> str:
    shown = {key: (values[key] or missing).ljust(VALUE_WIDTH) for key in values}
    return f"PH: {shown['ph']} | EC: {shown['ec']} | T: {shown['temp']}"


def room_separator(name: str | None) -> str:
    message = f"NEXT ROOM IS {name}" if name else "ALL ROOMS DONE, PRESS Q TO QUIT"
    return f"{ROOM_SEPARATOR} {message}   {ROOM_SEPARATOR}"


def room_lines(current: Room) -> list[str]:
    lines = []
    for index, line_name in enumerate(current.line_names):
        start = f"[{current.name}] {line_name.ljust(LINE_NAME_WIDTH)}{SEPARATOR}"
        ml = f"ML: {(current.ml[index] or NOT_RECORDED).ljust(VALUE_WIDTH)}"
        reading = current.readings[index]
        values = values_text(reading, NOT_AVAILABLE) if reading else values_text(NO_VALUES, NOT_RECORDED)
        active = index == current.line and not current.saving
        if active and current.typing_ml:
            parts = [
                (start, PLAIN),
                (ml, YELLOW + BLINK),
                (f"{SEPARATOR}{values}{SEPARATOR}", PLAIN),
                (TYPE_HINT, CYAN),
            ]
        elif active and reading is None:
            # - until the pen has sent a live value, n.a. for the ones it has not got after that
            missing = NOT_AVAILABLE if pen.has_live else NOT_RECORDED
            live_values = values_text(drip_drain.csv_values(*pen.live_reading()), missing)
            parts = [
                (f"{start}{ml}{SEPARATOR}", PLAIN),
                (live_values, YELLOW + BLINK),
                (SEPARATOR, PLAIN),
                (RECORD_HINT, CYAN),
            ]
        elif active:
            parts = [(f"{start}{ml}{SEPARATOR}", PLAIN), (values, YELLOW), (SEPARATOR, PLAIN), (RECORDED_HINT, CYAN)]
        else:
            parts = [(f"{start}{ml}{SEPARATOR}{values}", PLAIN)]
        lines.append(fit(parts))
    if current.saving:
        lines.append(fit([(f"> ROOM {current.name} CONFIRMED", PLAIN)]))
    elif current.confirming:
        lines.append(
            fit(
                [
                    (f"> CONFIRM ROOM {current.name}{ENTER_TO_CONFIRM}", YELLOW),
                    (SEPARATOR, PLAIN),
                    (CONFIRM_HINT, CYAN),
                ]
            )
        )
    elif current.complete:
        lines.append(fit([(f"> CONFIRM ROOM {current.name}", PLAIN)]))
    if asked == "s":
        lines.append(
            fit(
                [
                    (f"> SKIP ROOM {current.name}?{ENTER_TO_CONFIRM}", YELLOW),
                    (SEPARATOR, PLAIN),
                    (SKIP_HINT, CYAN),
                ]
            )
        )
    elif asked == "q":
        lines.append(fit([(f"> QUIT?{ENTER_TO_CONFIRM}", YELLOW), (SEPARATOR, PLAIN), (QUIT_HINT, CYAN)]))
    return lines


def render() -> list[str]:
    # the separator is drawn with the room, so what say prints goes above it
    return [room_separator(room.name)] + room_lines(room) if room is not None else []


screen = Screen(render)
draw = screen.draw
say = screen.say


def start_room() -> None:
    """Starts the room that continues from the csv. When every room is done, read_keys returns, to save the csv."""
    global room, all_done
    try:
        room = drip_drain.next_room(drip_drain.read_csv(), part_of_day, frozenset(skipped))
    except ValueError as error:
        room = None
        say(f"# no room can start: {error}")
        return
    if room is None:
        all_done = True
        return
    draw()


async def save_csv() -> None:
    """Saves the csv to the daily folder and empties it.

    Asks before a file there is overwritten, and when it is not, keeps the csv and shows it.
    """
    target = drip_drain.daily_csv(daily_dir, part_of_day)
    if target.exists():
        question = OVERWRITE_QUESTION.format(target.name)
        if await cli_terminal.choose(screen, question, CHOOSE_HINT, lambda: OVERWRITE) != "yes":
            # the csv is kept as it is, so it can be saved by hand
            say(f"# {target} not overwritten, {CSV_PATH.name} is kept as it is:\n{CSV_PATH.read_text().rstrip()}")
            return
    try:
        drip_drain.archive_csv(target)
        say(f"# {CSV_PATH.name} saved as {target} and emptied")
    except OSError as error:
        # the csv is kept as it is, so it can be saved by hand
        say(f"# {CSV_PATH.name} not saved to the daily folder, and not emptied: {error}")


async def save_room() -> None:
    """Appends the confirmed room to the csv and starts the next one."""
    rows = room.rows(pen.name)
    while True:
        try:
            drip_drain.append_rows(rows)
            break
        except PermissionError:
            say(f"# {CSV_PATH.name} is open in another program, close it. trying again every {CSV_RETRY_SECONDS} s")
            await asyncio.sleep(CSV_RETRY_SECONDS)
    # the lines of the saved room stay on screen, the next room is drawn below them
    screen.keep()
    start_room()


def skip_room() -> None:
    """Drops the room without writing it and starts the next one."""
    skipped.add(room.name)
    say(f"# room {room.name} skipped, not written to {CSV_PATH.name}")
    start_room()


def record_live() -> None:
    """Puts the live values in the line of the room the arrows are on."""
    if not pen.has_live:
        say("# no live values yet, nothing recorded")
        return
    reason = room.record(now(), *pen.live_reading())
    if reason is not None:
        say(f"# reading ignored, {reason}")
        return
    draw()


def on_live() -> None:
    # only the line being recorded shows the live values
    if room is not None and not room.typing_ml:
        draw()


def press(key: str) -> None:
    """Does what the key does to the room."""
    global asked
    if asked:
        # only enter skips (enter on the quit is read_keys'), any other key does nothing else
        was, asked = asked, ""
        if was == "s" and key in ENTER:
            # start_room draws
            skip_room()
            return
    elif key.lower() in ("s", "q"):
        asked = key.lower()
    elif key in (ARROW_UP, ARROW_DOWN):
        room.move(1 if key == ARROW_DOWN else -1)
    elif key in (ARROW_LEFT, ARROW_RIGHT):
        room.switch(to_ml=key == ARROW_LEFT)
    elif key in DELETE_KEYS:
        room.delete()
    elif key in ENTER and room.confirming:
        room.confirm()
        asyncio.create_task(save_room())
    elif key in ENTER and room.typing_ml:
        room.next_line()
    elif key in ENTER:
        # record draws
        record_live()
        return
    elif room.typing_ml and not room.confirming and key.isdecimal() and key.isascii():
        room.type_digit(key)
    draw()


async def read_keys() -> None:
    """Passes the keys to the room until every room is done, q confirmed with enter, or q alone without a room."""
    while not all_done:
        await asyncio.sleep(KEY_POLL_SECONDS)
        for key in cli_terminal.keys_pressed():
            if (asked == "q" and key in ENTER) or (key.lower() == "q" and (room is None or room.saving)):
                return
            if room is None or room.saving:
                continue
            press(key)


async def main() -> None:
    global daily_dir, pen
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"host of the bridge (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port of the bridge (default {DEFAULT_PORT})")
    parser.add_argument(
        "--daily-dir",
        type=Path,
        default=drip_drain.DEFAULT_DAILY_DIR,
        help=f"folder the csv is saved to once every room is done (default {drip_drain.DEFAULT_DAILY_DIR})",
    )
    args = parser.parse_args()
    daily_dir = args.daily_dir
    pen = PenClient(args.host, args.port, on_live, lambda text: say(f"# {text}"))
    with cli_terminal.interactive():
        await take_rooms()


def pen_options() -> dict[str, str]:
    return {address: f"> {label(name)}  {address}  {rssi} dBm" for address, (name, rssi) in pen.pens.items()}


async def alongside(pen_task: asyncio.Task, work: Coroutine[None, None, T]) -> T:
    """Does the work while the pen runs. An error of the pen ends the work."""
    task = asyncio.create_task(work)
    await asyncio.wait({task, pen_task}, return_when=asyncio.FIRST_COMPLETED)
    if not task.done():
        task.cancel()
        # the pen runs until cancelled, so it ended with an error, which this raises
        pen_task.result()
    return task.result()


async def scan() -> bool:
    """Waits SCAN_SECONDS for the pens in range to be found. False on q."""
    end = asyncio.get_running_loop().time() + SCAN_SECONDS
    while asyncio.get_running_loop().time() < end:
        await asyncio.sleep(KEY_POLL_SECONDS)
        if any(key.lower() == "q" for key in cli_terminal.keys_pressed()):
            return False
    return True


async def wait_for_q() -> None:
    while not any(key.lower() == "q" for key in cli_terminal.keys_pressed()):
        await asyncio.sleep(KEY_POLL_SECONDS)


async def wait_for_pen() -> bool:
    """Waits until the pen chosen is connected. False on q."""
    while not pen.connected:
        await asyncio.sleep(KEY_POLL_SECONDS)
        if any(key.lower() == "q" for key in cli_terminal.keys_pressed()):
            return False
    return True


async def take_rooms() -> None:
    """Asks for the pen and the part of the day, then takes the rooms until q."""
    global part_of_day
    # fails at the start rather than at the first room when the csv cannot be used
    rows = drip_drain.read_csv()
    # the bridge scans for the pens in range until one is chosen, and connects to it after
    pen_task = asyncio.create_task(pen.run())
    try:
        # the bridge scans meanwhile, so the pen is in the list sooner
        if (
            await alongside(pen_task, cli_terminal.choose(screen, TURN_ON_QUESTION, TURN_ON_HINT, lambda: TURNED_ON))
            is None
        ):
            return
        say("# looking for pens in range, Q TO QUIT")
        if not await alongside(pen_task, scan()):
            return
        # a single pen in range is taken without the list, but only the first time: after a no, the list
        only_pen = next(iter(pen.pens)) if len(pen.pens) == 1 else None
        # until the name on the back of the pen is the one chosen
        while True:
            if only_pen is not None:
                address, only_pen = only_pen, None
            else:
                address = await alongside(
                    pen_task, cli_terminal.choose(screen, PEN_QUESTION, PEN_HINT, pen_options, NO_PEN_YET)
                )
            if address is None:
                return
            check_question = PEN_CHECK_QUESTION.format(label(pen.pens[address][0]))
            checked = await alongside(
                pen_task, cli_terminal.choose(screen, check_question, CHOOSE_HINT, lambda: PEN_CHECKED)
            )
            if checked is None:
                return
            if checked == "yes":
                break
        pen.choose(address)
        say(f"# pen {label(pen.pens[address][0])} {address} chosen")
        part_of_days = {name: f"> {name}" for name in drip_drain.ROOMS}
        chosen = await alongside(
            pen_task, cli_terminal.choose(screen, PART_OF_DAY_QUESTION, CHOOSE_HINT, lambda: part_of_days)
        )
        if chosen is None:
            return
        part_of_day = chosen
        drip_drain.next_room(rows, part_of_day)
        say(f"# {part_of_day}, {CSV_PATH.name}: {len(rows)} rows")
        if not pen.connected:
            say("# waiting for the pen to connect. Make sure the pen is turned on, Q TO QUIT")
            if not await alongside(pen_task, wait_for_pen()):
                return
        start_room()
        # q ends read_keys, and so does the last room done
        await alongside(pen_task, read_keys())
        if all_done:
            await alongside(pen_task, save_csv())
            say(room_separator(None))
            await alongside(pen_task, wait_for_q())
    except BridgeGone as error:
        # the window was closed with the bridge in it, so nobody is left to press q
        say(f"# {error}, quitting")
    finally:
        pen_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    if room is not None and not room.saving and room.started:
        print(f"# room {room.name} not complete, not written to {CSV_PATH.name}")
