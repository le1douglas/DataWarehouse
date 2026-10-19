# Bluelab OnePen: BLE protocol (from Edenic 1.15.3)

What the Bluelab OnePen sends over Bluetooth Low Energy, worked out by static analysis of the Edenic Android app (`com.bluelab.new_day_flutter.prod`, version 1.15.3, split APK in `apks/edenic_1.15.3`).

> **Status:** everything here comes from reading decompiled code. None of it has been checked against packets captured from a real pen. Treat byte layouts as strong hypotheses until confirmed with an HCI snoop log or nRF Connect.

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
- **No bonding, pairing or encryption** was found on the OnePen path in the native code.
- Notifications are enabled by writing `ENABLE_NOTIFICATION_VALUE` to the CCCD `00002902-0000-1000-8000-00805f9b34fb`.
- Writes use `WRITE_TYPE_DEFAULT` (write with response).
- The app doesn't request a larger MTU.

## Discovery

A device is classed as a OnePen when its advertisement lists service UUID:

```
983DD3DA-D46F-BC05-0100-00C278B6B50A
```

For comparison, the other device families advertise:

| Device | Service UUID |
|---|---|
| Intellilink | `12341000-1234-1234-1234-123456789abc` |
| Pulse | `9B3DD3DA-D46F-BC00-0100-00C278B6B50A` |
| Pulse (pairing) | `9B3DD3DA-D46F-BC00-0102-00C278B6B50A` |
| Pulse (configure) | `9B3DD3DA-D46F-BC00-0101-00C278B6B50A` |

The first manufacturer-data entry (2-byte company ID, little-endian, followed by its payload) is passed raw to Flutter. The native code doesn't decode it for the OnePen.

## Characteristics

All are in the OnePen service and follow the pattern `983dd3da-d46f-bc05-0100-XXc278b6b50a`.

| XX | Properties used | Content |
|---|---|---|
| `01` | notify | Live reading (tagged) |
| `02` | notify | Live reading (tagged) |
| `03` | notify | Live reading (tagged) |
| `04` | read, write | Device info / settings (read); command channel (write) |
| `05` | notify | Stored measurement log |
| `06` | notify | Calibration history |

## Number format

The same 3-byte value appears in live readings and in measurement records:

```
[int16 little-endian raw][int8 exponent e]
value = raw / 10^e        if e >= 0
value = raw * 10^(-e)     if e <  0
```

`raw` is signed.

## Live readings (notify on `01`, `02`, `03`)

Each notification is 4 bytes:

| Byte | Meaning |
|---|---|
| 0 | Tag, ASCII: `'P'` (0x50) = pH, `'E'` (0x45) = EC, `'T'` (0x54) = temperature. Other tags are dropped. |
| 1–2 | raw, int16 LE |
| 3 | exponent, int8 |

Example: `50 BC 02 02` → pH, raw 0x02BC = 700, exponent 2 → **7.00**.

The app subscribes to all three characteristics at once and keeps the latest pH, EC and temperature it has seen. The tag, not the characteristic, decides which quantity a packet is. Decode errors are logged as `BluelabOnePen: Error decoding telemetry`.

## Device info (read `04`)

The response is at least 29 bytes. Multi-byte fields are little-endian.

| Byte(s) | Field | Notes |
|---|---|---|
| 0 | (not used) | Possibly a length byte |
| 1 | battery | |
| 2–4 | (not used) | |
| 5–7 | firmware version | 3 separate bytes |
| 8 | brightness | |
| 9 | EC unit | 0 = EC, 1 = CF, 2 = ppm500, 3 = ppm700, 4 = mS/cm |
| 10 | temperature unit | 0 = °C, 1 = °F |
| 11–12 | number of stored measurements | uint16 |
| 13–14 | number of calibrations | uint16 |
| 15 | mV display enabled | 0 or 1 |
| 16–17 | backlight-on time, seconds | uint16 |
| 18–19 | auto-off time, seconds | uint16 |
| 20 | resolution | 0 = Standard, 1 = High |
| 21–24 | minutes since last pH calibration | int32 |
| 25–28 | minutes since last EC calibration | int32 |

## Commands (write to `04`)

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

```
[count (uint8, at most 3)] then count entries of 9 bytes:
  [EC: 3-byte value][pH: 3-byte value][temperature: 3-byte value]
```

- The app enables notifications and keeps collecting until a packet yields no records.
- **The packet carries no timestamp.** The app stamps each record with the phone's current time when it arrives.

## Calibration history (notify `06`, Flutter `syncCalibrations`)

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

## Open questions

1. **Live-reading units.** It isn't clear whether EC and temperature arrive in the pen's selected unit or a fixed unit. Capture readings, change the units with `0x71`, and compare.
2. **Which live characteristic carries which reading.** Not needed for decoding (the tag identifies it), but it can be confirmed with a capture.
3. **Unused device-info bytes** 0 and 2–4.
4. **Meaning of the raw pH calibration value**, possibly a mV offset.
5. **Firmware-update protocol.** Not analysed.
6. **Dart-side security code.** `bluetooth_security.dart` and X25519 crypto exist in the Dart code. Nothing on the OnePen path in the native code uses them; they probably serve Pulse or Intellilink, but this hasn't been verified.
7. **Scan classification quirk.** As decompiled, `W.a.h` decides on the first advertised service UUID only, so a OnePen that advertises another UUID first may be classed differently. This could be a decompiler artifact.

## Suggested verification

Capture a session with the real pen: enable Android's Bluetooth HCI snoop log or use nRF Connect. During it:

- connect and read `04`;
- watch notifications on `01`, `02` and `03`;
- run measurement and calibration syncs;
- change the units.

Then compare the bytes with the layouts above.

## Reproducing the analysis

REA's bundled JADX (`/opt/rea/android/jadx-headless-mcp-0.7.1-all.jar`) decompiled the base APK through a small launcher using the JADX API. The decompiled sources are in the session scratchpad: `/tmp/claude-1000/-home-node-work/9b434113-25a0-4b21-abf5-6a854c5f9ecf/scratchpad/all`.

REA evidence IDs:

| Evidence | ID |
|---|---|
| Dart AOT inspection | `ev_9483070dcb975cb7d7741246779ecc534e9fdf01ad98c1fe5969d8471420038f` |
| `TelemetryData` references | `ev_87e00eedf267385450f3c02ba15f8d4d953d766225298e7f35ff82b8249283c2` |
