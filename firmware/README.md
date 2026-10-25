# Firmware provenance and S3 configuration reference

The physical integration used firmware derived from
[Kaia.ai firmware](https://github.com/kaiaai/firmware), with local S3 and
per-wheel encoder configuration work.

## Why there is no final sketch here

The inspected local upstream baseline was
`e4d159c94321b1431e61f64f12c3a2da24cf2d19`. It is a provenance reference,
**not** the exact final deployed source revision.

The recorded final installed application preserved pre-flash watchdog/LiDAR
behavior and added per-wheel PPR handling. The remaining local source includes
later source-only watchdog/LiDAR changes that were not part of that flash.
The isolated source staging for the installed application was no longer
available. Copying the current sketch would therefore misrepresent the build.

With the owner's approval, this release omits unmatched firmware source,
compiled binaries, flash partitions, SPIFFS/NVS backups, and network settings.
It cannot reproduce the complete robot firmware or provide a verified flashing
procedure. Historical build records referenced Arduino ESP32 core 2.0.17;
that fact does not restore the missing source match.

## Included configuration

[`config_slam_car_makerhub_s3.yaml`](config_slam_car_makerhub_s3.yaml) is a
**reference-only local profile**, not a validated, ready-to-flash robot
configuration. Its own warnings remain intact.

- Target carrier: MakerHub/Smith3D ESP32-S3 N16R8.
- LiDAR: RPLIDAR A1; schema `tx` is MCU RX GPIO41, `rx` is MCU TX GPIO42,
  and motor PWM is GPIO2.
- Left encoder: GPIO21/48; left driver: GPIO40/47.
- Right encoder: GPIO1/14; right driver: GPIO38/39.
- Recorded wheel diameter: 0.065 m; track: 0.128 m.
- Wheel-specific PPR: left 462.125, right 629.083333; shared fallback 1035.
  These are stored profile values, **not validated moving calibration**.

Channel corrections and prior runtime records used different value allocations.
Do not infer a validated left/right calibration from this snapshot. Camera
GPIOs were reserved, but camera operation and powered validation of this
corrected profile were not established. Several pins borrow onboard LED,
microSD, or external JTAG functions.

Per-wheel PPR support depended on local firmware changes; an unmodified
upstream checkout must not be assumed to understand this profile fully.
Do not energize motors based on this file. Validate board/pins, power,
exclusive control, physical cutoff, and command timeout independently.

This reference is distributed under [Apache-2.0](LICENSE), with upstream
attribution in [third-party notices](../THIRD_PARTY_NOTICES.md).

[Project overview](../README.md) |
[Engineering conclusion](../docs/project-conclusion.md)
