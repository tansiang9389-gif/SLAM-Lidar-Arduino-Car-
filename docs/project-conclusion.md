# Project conclusion: what I built, achieved, and would improve

## My starting goal

I wanted to build an affordable LiDAR car that could observe an indoor space,
make a map, and eventually navigate through it. The project became as much
about measurement and integration as it was about getting software to run.
I learned that a visible map is an important result, but it is not the same
as dependable navigation.

**My conclusion:** the system works as a driving, sensing, and experimental
mapping prototype. My latest map is stable. ROS 2 navigation still needs
tedious, careful commissioning, and I do not claim repeatable autonomous
missions or a finished Nav2 robot.

## What I worked on

### The original `slam` experience

I split the early work into LiDAR/Wi-Fi, motor control, and a combined car.
The original folder contains those separate modules and custom host-side
visualization/mapping work. Arduino motor control and earlier driver/wiring
variants belong to this experimental background.

That separation helped me understand individual components before integrating
them. It also created several possible software paths. A feature described
in an experimental README was not automatically something I had demonstrated
on the physical car.

### The `SLAM V2` experience

V2 explored a more structured ROS 2 Jazzy system with custom firmware/interfaces,
calibration handling, scan-only bringup, and explicit physical acceptance gates.
This was useful engineering work even where the physical gates stayed blocked.
Synthetic bench exercises tested software behavior, not real exploration or
collision avoidance.

I have kept that experience in this conclusion without shipping its alternative
applications as if they were the final deployed system.

### The selected Kaia.ai-based implementation

For the used stack, I integrated Kaia.ai-derived firmware with the ROS
`kaiaai_telemetry` bridge and investigated the sensor-to-map path. The ESP32
handles the embedded side and exchanges data with the PC over Wi-Fi/micro-ROS.
The PC decodes telemetry and runs ROS 2 mapping tools.

I did not write the entire robotics platform from scratch. Maker's Pet and
Kaia.ai supplied important foundations. My contribution was adapting and
debugging the car integration, hardware configuration, telemetry timing,
and evaluation. [Credits and license details](../THIRD_PARTY_NOTICES.md)
identify that boundary.

## What I achieved, and what the evidence means

| Evidence type | Achievement | What it does not prove |
|---|---|---|
| Physical integration and driving observations | Built the robot and exercised manual motion and sensing | Calibrated travel accuracy or safe unattended operation |
| Live telemetry | Recovered scans, odometry, joints, transforms, and a mapping stream | Correct wheel scale, mounting, or motion-time alignment |
| Standalone software regression | Exercised timing/order edge cases and 10,000 non-overlapping windows | Actual network delivery or Cartographer behavior |
| Historical offline replay | Corrected data produced zero overlapping scan windows and no reversed odometry timestamps in the measured replay | That timing defects caused every historical large yaw jump |
| Stationary live verification | Small measured yaw spans after the corrections and sensor recovery | Moving-yaw accuracy or successful navigation |
| My latest reported outcome | Stable mapping | A quantified map error, route success rate, or Nav2 acceptance |

![Assembled LiDAR car](images/robot-build.png)

*The assembled car. The photo is a build record, not proof of every controller
revision or feature discussed here.*

## Engineering challenges

### Power, wiring, and controller revisions

Motor loads, LiDAR power, logic levels, and pin assignments all needed attention.
Replacing a controller meant I could not assume an older board's encoder
directions or channels were still correct.

I installed two separate capacitors:

| Placement | Installed value | Intended role |
|---|---|---|
| LiDAR 5 V to GND | 0.1 uF | Local high-frequency decoupling |
| DRV8833 7.4 V to GND | 100 uF | Bulk buffering during load changes |

These describe my installed wiring. I did not measure before/after rail noise,
so I cannot quantify their benefit or claim they fixed mapping or yaw.
This record does not establish component ratings or polarity. Those still
need checking against the actual parts.

The [wiring drawing](images/wiring-reference.jpg) is a supplied reference with
its warnings retained. It does not substitute for a verified netlist or an
as-built electrical inspection. It must not be used to infer the replacement
S3 pinout.

### Wheel directions, channel assignment, and scale

During keyboard control, A turned the car right and D turned it left.
Backward travel also veered while forward travel appeared straight. Those
observations made direction/channel and asymmetric drive response worth
investigating; they did not justify a blind encoder sign flip.

In the investigated odometry convention, forward travel expected left counts
to decrease and right counts to increase. A negated wheel command and the
odometry calculation already compensated for that convention. Misleading
argument names were not evidence that the signs were wrong.

A static quadrature test produced +4/-4 for four transitions. Software decoding
already used four counts per cycle and converted PPR accordingly. Halving
configured PPR alone would double reported travel, not correct a demonstrated
software double count.

The right-wheel measurement remained questionable. One recorded value was
about 27.4% lower than an older wheel-turn result; if the old result still
applied, the lower calibration would overestimate travel by about 37.7%.
Channel correction and controller changes also affected which stored value
belonged to which wheel. The released S3 reference remains **provisional**,
not a validated motion calibration.

### Odometry continuity and sensor recovery

An apparent odometry/counter discontinuity needed to be treated as a trajectory
boundary. A map spanning a reset is not navigation-ready just because it looks
plausible. The bridge logs detected sequence restarts, but that is not a
universal detector for every possible controller or odometry reset.

After sensor recovery, mapping was restarted as a fresh diagnostic trajectory.
This was deliberately separate from certifying navigation.

### Scan timing and telemetry ordering

LaserScan timestamps describe when points were acquired, not merely when a
message arrived. The earlier scan-duration fallback could assign a duration
that extended past the next scan. Overlapping acquisition windows and
Cartographer dropped-point warnings were confirmed.

The correction uses measured consecutive scan boundaries. It waits for a full
initial interval, rejects invalid intervals, advances the boundary even when
a broken scan is discarded, and limits floating-point time increments so the
final ray does not extend beyond the measured window. The legacy parameter
`laser_scan.min_scan_time` now acts as a **maximum accepted interval**, not a
minimum-duration replacement.

The bridge also rejects duplicate, stale, or non-increasing-timestamp telemetry.
On a detected sequence restart, it clears decoder/scan timing state and logs
that mapping must restart. It does not silently certify continuity.

The offline regression covers nanosecond rollover, duration boundaries, broken
scans, sequence wrap, gaps, duplicates, stale data, and detected restarts.
Historical recorded-data replay checked published scans and odometry, with
optional Cartographer observation. The original replay could crash
Cartographer; corrected replay removed the measured overlap/order defects.
**This did not prove those defects caused the large moving-yaw jumps.**

### Clock behavior, latency, and yaw

The Windows Docker Desktop/WSL runtime also showed backward Linux clock steps.
In an on/off/on experiment with the same Ubuntu clock:

| Runtime condition | Observation over 90 seconds |
|---|---|
| Docker running | Three backward steps, approximately 60-105 ms |
| Docker backend absent and its distro stopped | No backward steps observed |
| Docker restarted | Three backward steps, approximately 50-61 ms |

Kernel tracing saw an `init`-named caller invoking `settimeofday` at roughly
30-second intervals. Restricted process inspection did not establish the exact
executable owner. The experiment established Docker Desktop involvement in
that clock behavior, not a complete causal explanation for historical yaw.
Restarting Docker was not a remedy.

One three-minute stationary test measured a yaw span of about 0.114 degrees.
A later 60-second live recovery check recorded 437 scans, 1,746 odometry/joint
messages, and 60 map messages, with zero scan overlaps, zero reversed odometry
timestamps, and a stationary yaw span of about 0.091 degrees. No motion
commands were issued during that check.

These are bounded stationary measurements. They do not establish moving-yaw
accuracy, localization quality, or navigation readiness.

I suspect latency between the PC and ESP32 may contribute to the remaining
yaw behavior. That is a hypothesis, not a measured root cause. Network jitter,
clock discontinuities, wheel calibration, mounting, and motion-dependent
effects need separate tests. I would not describe the outcome as a fundamental
restriction of ESP32 or ROS 2.

### LiDAR mounting and transforms

The investigated RPLIDAR A1 configuration applied a -180-degree angle offset,
paired with a -180-degree pitch in the selected robot model. Together they
put the raw zero-angle ray forward. Rotating the URDF alone would change that
relationship and could introduce a new error.

There was also a confirmed translation mismatch: the selected model placed
the scan at x=0, z=0.0704 m from `base_link`, while the recorded car mount was
x=0.01, z=0.13 m. The visual-only car URDF was not the model selected by that
launch. These are historical configuration findings, not a corrected and
validated mounting model shipped here. A real front/left/right obstacle check
and measured mount are still required.

## Why navigation remains tedious

SLAM (simultaneous localization and mapping) estimates a map and the robot's
position. Nav2 must then use localization, transforms, costmaps, planners,
controllers, and consistent sensor data to move safely. Each layer depends
on the earlier ones.

My experience was that bringing up the graph was easier than proving that
every timestamp, wheel movement, and frame matched physical reality.
Good-looking stationary mapping did not remove the need to calibrate moving
odometry, validate mounting, control command ownership, and repeat route tests.
I have not demonstrated a reliable route-success rate or unattended operation.

![Indoor mapping result](images/mapping-result.png)

*My reported stable mapping result. Screenshot evidence alone does not measure
dimensions, drift, loop-closure quality, or navigation success.*

The separate colored-overlay mapping photo was omitted from publication
because it contained a person's reflection.

## What I would improve next

1. **Prove safety before motion.** Verify independent physical motor cutoff,
   exclusive command control, and command-loss stopping. Use bounded trials,
   not a continuous ten-turn command.
2. **Use a stable, measured host runtime.** Prefer a native Linux evaluation
   and monitor clock monotonicity before comparing mapping runs. Do not hide
   discontinuities with Cartographer tuning.
3. **Calibrate wheels under motion.** Measure signed counts, channel ownership,
   loaded wheel circumference, and track width using repeatable forward,
   reverse, and bounded turn tests. Record uncertainty and repeatability.
4. **Measure the scan mount.** Correct the actual launched frame tree and
   verify front/left/right with physical obstacles as a combined
   angle-offset/transform check.
5. **Measure transport timing.** Log acquisition times, arrival delay, jitter,
   loss, and sequence resets together with motion. Test the latency hypothesis
   instead of assuming it is the answer.
6. **Evaluate simpler sensor paths if needed.** Direct host LiDAR connection
   or an independently validated IMU could help isolate faults. Neither is
   implemented or proven as the solution in this release.
7. **Make bringup reproducible.** Preserve matched source, pinned dependencies,
   launch parameters, calibration, and environment records. A clean offline
   build should be separate from any physical deployment.
8. **Commission Nav2 with acceptance tests.** Start with localization and
   bounded low-speed routes, then repeat trials and report distance/yaw error,
   route completion, recoveries, and stopping behavior.

## What I chose to publish

The release keeps the corrected bridge, all decoder headers needed by its
current source, its timing regression/replay tool, and a clearly labeled
S3 configuration reference. Extra decoder headers are build dependencies of
the used bridge, not claims that all those LiDAR models were used on this car.
The unused telemetry test publisher was removed along with its build target.

The older public Arduino and standalone Python LiDAR prototypes are superseded
and remain accessible in Git history rather than as competing active entry
points. V2 applications, raw bags/maps, diagnostics, binaries, network settings,
and duplicate experiment trees are excluded. Original local folders were not
cleaned or rewritten.

The exact flashed firmware source could not be matched safely: current local
source includes later changes that were not flashed. I chose to state that
limitation rather than publish a misleading "final" sketch. See the
[firmware provenance note](../firmware/README.md).

## Final reflection

I achieved a working robot integration and a stable mapping result, and I
learned how easily timing, direction conventions, calibration, and runtime
behavior can undermine navigation. I also learned to separate a successful
software test, a stationary measurement, and a physical autonomy claim.

The next milestone is not another screenshot. It is repeatable, measured,
safe navigation with matched source and configuration. That is the work still
needed to turn this prototype into a dependable robot.

[Back to the project overview](../README.md) |
[Build and offline tests](../ros_ws/src/kaiaai_telemetry/README.md)
