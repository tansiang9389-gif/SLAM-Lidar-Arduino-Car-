# Credits, licenses, and modification notices

## Independent project

This is an independent learning project by the repository owner.
[Maker's Pet](https://makerspet.com/) and [Kaia.ai](https://kaia.ai/) are
credited as upstream resources and technology foundations, not as sponsors,
official affiliates, partners, or endorsers of this car.

## Included material

| Material | Source / attribution | License |
|---|---|---|
| `ros_ws/src/kaiaai_telemetry` | [Kaia.ai telemetry](https://github.com/kaiaai/kaiaai_telemetry); retained REMAKE.AI, KAIA.AI, MAKERSPET.COM and file-specific notices | [Apache-2.0](ros_ws/src/kaiaai_telemetry/LICENSE) |
| Bundled LiDAR decoder headers | Same telemetry package; some retain EAI/YDLIDAR and other source-specific acknowledgments | Apache-2.0 as stated in those files |
| S3 firmware configuration reference | Local adaptation associated with [Kaia.ai firmware](https://github.com/kaiaai/firmware) | [Apache-2.0](firmware/LICENSE) |
| Original project documentation and owner-supplied photos | Repository owner | Existing root [MIT license](LICENSE), except identified third-party material |

The supplied wiring illustration is reproduced as an owner-supplied reference
with its original notices and warnings intact. No simulation or electrical
verification is claimed.

The root MIT license does not relicense the Apache-licensed subtrees.
Original copyright, license, and upstream acknowledgments remain in source.

## Changes in the released bridge

This is a locally modified snapshot, not a pristine upstream release:

- `src/telem.cpp`: telemetry ordering checks and reset diagnostics; measured
  scan-window timing replaces duration inflation/fallback behavior.
- `src/telemetry_timing.hpp`: timing and stream-order helper.
- `test/test_timing.py`: standalone edge-case regression and isolated
  recorded-telemetry replay with optional Cartographer observation; expanded
  interval, rounding, sequence-boundary, and rejection-recovery regression cases.
- `CMakeLists.txt`: timing regression registration; unused test-publisher
  target omitted from this curated copy.
- `package.xml`: direct `tf2` and `tf2_ros` dependencies declared.
- Documentation: local evidence limits, offline build/test instructions, and
  provenance notes.

The imported local telemetry snapshot had no committed upstream HEAD recorded.
No exact upstream revision is invented here. The included source and retained
license are the release artifact. Firmware provenance is separately described
in the [firmware note](firmware/README.md); no matched firmware source or binary
is included.

## Related software, not vendored here

- [Kaia.ai platform](https://github.com/kaiaai/kaiaai) and
  [bringup](https://github.com/kaiaai/kaiaai_bringup)
- [Kaia.ai firmware](https://github.com/kaiaai/firmware)
- [Kaia.ai message interfaces](https://github.com/kaiaai/kaiaai_msgs)
- [Kaia.ai micro-ROS Arduino integration](https://github.com/kaiaai/micro_ros_arduino_kaia)
- [Maker's Pet](https://github.com/makerspet)
- [ROS 2](https://docs.ros.org/en/jazzy/),
  [micro-ROS](https://micro.ros.org/),
  [Cartographer ROS](https://github.com/cartographer-project/cartographer_ros),
  and [Nav2](https://github.com/ros-navigation/navigation2)

Each external project retains its own license and compatibility requirements.

[Project overview](README.md)
