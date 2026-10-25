# Corrected Kaia.ai telemetry bridge

This locally modified [Kaia.ai package](https://github.com/kaiaai/kaiaai_telemetry)
converts `kaiaai_msgs/msg/KaiaaiTelemetry2` into ROS scans, odometry, wheel
joints, odometry TF, battery, and Wi-Fi state. It is the selected bridge from
the car investigation, not a complete robot launch system.

All bundled decoder headers are retained because `telem.cpp` includes and
constructs those decoder classes. RPLIDAR A1 was used on this project; retaining
compile dependencies does not mean every decoder was physically tested.
The unused `telem_test_pub` application and target are intentionally omitted.

## How to run the standalone timing regression

Prerequisites: Python 3 and a C++17 compiler on Linux. From the repository root:

```bash
python3 ros_ws/src/kaiaai_telemetry/test/test_timing.py --unit --compiler c++
```

Expected output:

```text
Timing/order edge cases and 10000 non-overlapping windows passed
```

The test compiles the actual timing header with `-Wall -Wextra -Werror`.
It covers initial/invalid/broken scan boundaries, duration recovery,
nanosecond rollover, float rounding, reset, sequence wrap, gaps, duplicate
and stale messages, and non-increasing timestamps.
It does not connect to a robot or require ROS.

## How to build the ROS 2 package

Prerequisites: Ubuntu with ROS 2 Jazzy, colcon, a C++ compiler, and the standard
ROS build dependencies in `package.xml`. Follow
[upstream installation guidance](https://github.com/kaiaai/install) for the
larger Kaia.ai environment. Do not run a live robot launch for an offline build.

The required message package is not vendored here. For a clean workspace,
obtain this pinned upstream interface snapshot:

```bash
source /opt/ros/jazzy/setup.bash
cd ros_ws
git clone https://github.com/kaiaai/kaiaai_msgs.git src/kaiaai_msgs
git -C src/kaiaai_msgs checkout --detach e17a601a3f748d10513e274aa65aaf77f96d7728
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-up-to kaiaai_telemetry \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
colcon test --packages-select kaiaai_telemetry --ctest-args -R telemetry_timing
colcon test-result --verbose
```

The explicit interpreter avoids accidentally using an unrelated user-installed
Python without ROS dependencies. If compatible `kaiaai_msgs` is already supplied by a sourced overlay, do not
clone another copy. The schema must match the bridge and recorded firmware
telemetry; building the interface is not proof of a full firmware match.
This release does not provide firmware, agent configuration, robot URDF,
Cartographer launch/configuration, or Nav2 tuning.

For reference, an isolated bridge invocation after building is:

```bash
ros2 run kaiaai_telemetry telem --ros-args \
  --params-file src/kaiaai_telemetry/config/telem.yaml \
  -p laser_scan.lidar_model:=SLAMTEC-RPLIDAR-A1
```

This only starts the telemetry subscriber/publishers; it cannot produce real
scans without compatible input. Use the replay procedure below for recorded
data in an isolated domain, not alongside a live robot.

## Timing behavior and configuration limits

[`config/telem.yaml`](config/telem.yaml) preserves the multi-model upstream
configuration. Select the actual model explicitly: the node's default model is
YDLIDAR-X4, **not** this car's A1.

| Setting | Meaning / caution |
|---|---|
| `laser_scan.min_scan_time` | Legacy name: maximum accepted measured scan interval, default 0.25 s; never a minimum-duration fallback |
| `laser_scan.discard_broken_scans` | The supplied file enables discarding scans interrupted by telemetry gaps |
| `lidar.angle_offset_deg` | RPLIDAR A1 entry is -180 degrees; evaluate jointly with the selected robot transform |
| `laser_scan.frame_id` | `base_scan` in the supplied file; no static sensor transform is supplied |
| `tf.child_frame_id` / `odometry.child_frame_id` | `base_footprint`; must match your actual frame tree |
| `battery.voltage_full` / `battery.voltage_empty` | Upstream defaults 25.2/22.2 V, **not calibrated for this car's 7.4 V rail** |

Do not use battery percentage from these defaults as a power safety measure.
The reference firmware disables battery ADC input. Battery monitoring must be
configured and independently verified before relying on it.

Consecutive completed revolutions determine acquisition boundaries. Initial,
invalid, or discarded broken intervals do not get fabricated durations.
Stale/duplicate/non-increasing telemetry is rejected with a warning. A detected
sequence restart clears decoder/timing state and emits an error: preserve
diagnostics and start a fresh mapping trajectory. This is not a universal
odometry-discontinuity detector.

## How to replay recorded telemetry offline

Prerequisites: a built/sourced bridge; compatible ROS Python interfaces;
a SQLite rosbag directory containing exactly one `.db3` with `/telemetry`
and `/tf_static`. Bags and local diagnostic data are not published here.

From `ros_ws`, use a fresh report path and a nonzero domain different from
your active domain:

```bash
python3 src/kaiaai_telemetry/test/test_timing.py \
  --bag /path/to/recorded-bag \
  --node "$PWD/install/kaiaai_telemetry/lib/kaiaai_telemetry/telem" \
  --params /path/to/replay-params.yaml \
  --domain 173 \
  --report /tmp/car-replay-new.json
```

`replay-params.yaml` must contain the supplied decoder arrays and explicitly
select `laser_scan.lidar_model: SLAMTEC-RPLIDAR-A1` under the node's
`ros__parameters`. Use the recorded robot's actual settings, not a guessed
sensor transform. The tool enables simulated time and local-only discovery,
refuses an occupied domain, and never publishes motor commands.

It checks overlap, odometry ordering, output counts, unchanged odometry
positions, and wheel-joint positions. It exits nonzero on violations.
It refuses to overwrite a report or associated process log.

Optional `--cartographer-config /path/to/config-directory` also launches
Jazzy's Cartographer node using `cartographer_lds_2d.lua` and reports
`map -> odom` yaw span and dropped-point warnings. That directory and matching
robot transforms must come from the recording setup. This optional integration
is not reproducible from this repository alone.

`--check-report /path/to/report.json` checks only recorded overlap/order
counts, not a new replay. `--allow-defects` is for comparison diagnostics
and bypasses normal output checks; it is **not** an acceptance test.

## Troubleshooting and evidence limits

- **`kaiaai_msgs` not found:** build the pinned interface package or source its
  compatible installed overlay before building the bridge.
- **No scans:** verify actual telemetry input and explicit A1 selection.
  A discovered publisher is not proof of live sensor data.
- **Invalid interval warnings:** inspect source timestamps, loss, and clock
  steps. Do not increase a fallback duration or tune Cartographer to hide them.
- **Sequence restarted:** do not navigate on the old mapping trajectory.
- **Replay domain occupied:** choose another isolated domain; do not stop
  unknown ROS processes.
- **Full package test failures:** the original investigation passed the targeted
  timing regression but reported pre-existing `flake8` and `uncrustify`
  failures in the broader package suite. No full-suite-green claim is made.

Historical offline/live observations and their limits are in the
[project conclusion](../../../docs/project-conclusion.md). Stationary yaw
stability is not moving-yaw or navigation validation.

[Apache-2.0 license](LICENSE) |
[Modification notices](../../../THIRD_PARTY_NOTICES.md) |
[Project overview](../../../README.md)
