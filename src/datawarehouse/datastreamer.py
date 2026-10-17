"""Connect to the first OnePen found over Bluetooth Low Energy and print its pH and EC when a key is pressed."""

import asyncio
import msvcrt
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner

DEVICE_NAME_FILTER = "ONE-"
CHARACTERISTICS = {
    "983dd3da-d46f-bc05-0100-01c278b6b50a": "ph",
    "983dd3da-d46f-bc05-0100-02c278b6b50a": "ec",
}
CSV_PATH = Path(__file__).with_suffix(".csv")
READ_KEY = "r"
QUIT_KEY = "q"
ROOMS = ("1.23", "1.22", "1.21", "1.20", "1.19", "1.18", "1.17", "0.27", "0.28", "0.29")
ROWS_PER_ROOM = 4


def decode(payload: bytearray) -> float:
    # [1] [2] little endian mantissa, [3] number of decimal places
    mantissa = payload[1] | (payload[2] << 8)
    return mantissa / 10 ** payload[3]


def ask_ml() -> str:
    while True:
        answer = input("ml: ").strip()
        if answer.isdecimal():
            return str(int(answer))
        print("not an integer, try again")


async def main() -> None:
    print("scanning...")
    device = await BleakScanner.find_device_by_filter(lambda d, _: d.name is not None and DEVICE_NAME_FILTER in d.name)
    if device is None:
        print("no device found")
        return

    print(f"connecting to {device.name} {device.address}")
    latest = {name: None for name in CHARACTERISTICS.values()}
    async with BleakClient(device) as client:
        for uuid, name in CHARACTERISTICS.items():
            await client.start_notify(uuid, lambda _, payload, name=name: latest.update({name: decode(payload)}))
        print(f"connected, press {READ_KEY} to read, {QUIT_KEY} to quit")
        while True:
            # getwch blocks, so it runs in a thread to keep the notifications coming
            key = await asyncio.to_thread(msvcrt.getwch)
            if key == READ_KEY:
                # read on every press, so rows deleted by hand are picked up
                text = CSV_PATH.read_text()
                rows_written = sum(1 for line in text.splitlines()[1:] if line.strip())
                if rows_written >= len(ROOMS) * ROWS_PER_ROOM:
                    print("all rooms done")
                    continue
                room = ROOMS[rows_written // ROWS_PER_ROOM]
                date_time = datetime.now().isoformat(timespec="microseconds")
                # taken before asking for ml, so the row has the values of the moment the key was pressed
                values = tuple("" if latest[name] is None else f"{latest[name]:.2f}" for name in ("ph", "ec"))
                ml = await asyncio.to_thread(ask_ml)
                row = ",".join((date_time, *values, room, ml))
                # a newline only if the last line lacks one, so no row is glued on and none is empty
                separator = "" if text.endswith("\n") else "\n"
                with CSV_PATH.open("a", newline="") as file:
                    file.write(separator + row + "\n")
                print(row)
            elif key == QUIT_KEY:
                break


if __name__ == "__main__":
    asyncio.run(main())
