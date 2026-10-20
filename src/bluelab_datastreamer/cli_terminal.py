"""Front end of drip_drain_cli.py: keys, colours and lines redrawn in place, on the terminal of a container.

Knows nothing of pens, rooms or csv files. Linux only, as it runs in a container, and in an
interactive terminal, or no key can be read. Only the standard library.
"""

import asyncio
import os
import re
import select
import shutil
import sys
import termios
import tty
from collections.abc import Callable, Iterator
from contextlib import contextmanager

KEY_POLL_SECONDS = 0.05
# terminal escape codes. lines are redrawn by moving the cursor up over them and clearing the
# screen from there down
UP = "\x1b[{}A"
CLEAR_DOWN = "\r\x1b[J"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
BELL = "\a"
# what can be typed, chosen or recorded is yellow, the rest in the terminal's own colour
YELLOW = "\x1b[33m"
RESET_COLOR = "\x1b[0m"
ENTER = ("\r", "\n")
# the keys that are more than one character are given these names, which no single key can be
ARROW_UP = "up"
ARROW_DOWN = "down"
ARROW_LEFT = "left"
ARROW_RIGHT = "right"
DELETE = "delete"
DELETE_KEYS = ("\b", "\x7f", DELETE)
# they come as an escape sequence. the ones with O are the arrows in the cursor mode some terminals
# switch to
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

# the terminal settings from before interactive: keys are read one at a time without them. None
# outside interactive, or when stdin is not a terminal
terminal_settings: list | None = None


@contextmanager
def interactive() -> Iterator[None]:
    """The cursor hidden and keys read one at a time, until the end of the block."""
    global terminal_settings
    if sys.stdin.isatty():
        terminal_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
    print(HIDE_CURSOR, end="", flush=True)
    try:
        yield
    finally:
        if terminal_settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, terminal_settings)
            terminal_settings = None
        print(SHOW_CURSOR, end="", flush=True)


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


def keys_pressed() -> list[str]:
    """The keys pressed since the last call, without waiting. An arrow or delete comes by its name.

    A key this does not know that is more than one character is left out, as its characters could
    be read as a digit or a q.
    """
    keys = []
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


def beep() -> None:
    # the terminal outside the container plays it
    print(BELL, end="", flush=True)


class Screen:
    """Lines at the bottom of the terminal that are redrawn in place, and lines printed above them that stay."""

    def __init__(self, render: Callable[[], list[str]]) -> None:
        # gives the lines to draw, from the state at the time of the draw
        self.render = render
        # the lines on screen, which the next draw moves up over
        self.shown: list[str] = []
        self.drawn = 0

    def draw(self) -> None:
        """Redraws the lines in place of the ones on screen. Nothing is printed when they have not changed."""
        lines = self.render()
        if self.drawn and lines == self.shown:
            return
        self._print("".join(f"{line}\n" for line in lines), end="")
        self.shown, self.drawn = lines, len(lines)

    def say(self, text: str) -> None:
        """Prints a line that stays, above the lines redrawn."""
        self._print(text)
        self.drawn = 0
        self.draw()

    def keep(self) -> None:
        """Leaves the lines on screen as they are, the next draw goes below them."""
        self.drawn = 0

    def clear(self) -> None:
        """Removes the lines from the screen."""
        self._print("", end="")
        self.shown, self.drawn = [], 0

    def _print(self, text: str, end: str = "\n") -> None:
        print((UP.format(self.drawn) if self.drawn else "") + CLEAR_DOWN + text, end=end, flush=True)


async def choose(screen: Screen, hint: str, options: Callable[[], dict[str, str]], waiting: str = "") -> str | None:
    """Lists the options under the hint until one is chosen with the up and down arrows and enter. Its key, None on q.

    options gives the label of each option by its key, and is asked again at every redraw, so options
    can come in while the list is shown. The first one is chosen at the start, and the choice follows
    the key, so it does not move when the labels change. waiting is shown while there is none. The
    list takes the place of what the screen draws until the choice, so what is said meanwhile goes
    above it.
    """
    chosen: str | None = None

    def render() -> list[str]:
        rows = [fit([(label, key == chosen)]) for key, label in options().items()] or [fit([(waiting, False)])]
        return [fit([(hint, True)]), *rows]

    render_before, screen.render = screen.render, render
    try:
        while True:
            keys = list(options())
            if chosen is None and keys:
                chosen = keys[0]
            screen.draw()
            await asyncio.sleep(KEY_POLL_SECONDS)
            for key in keys_pressed():
                if key.lower() == "q":
                    return None
                if chosen is None:
                    continue
                if key in ENTER:
                    # the choice goes from the screen, the caller says which one it was
                    screen.clear()
                    return chosen
                if key in (ARROW_UP, ARROW_DOWN):
                    index = keys.index(chosen) + (1 if key == ARROW_DOWN else -1)
                    chosen = keys[max(0, min(len(keys) - 1, index))]
    finally:
        screen.render = render_before
