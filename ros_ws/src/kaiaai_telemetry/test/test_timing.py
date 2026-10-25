import argparse
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import tempfile
import time


UNIT_SOURCE = r"""
#include "telemetry_timing.hpp"
#include <cassert>
#include <iostream>
using namespace telemetry_timing;
int main() {
  const auto second = 1000000000LL;
  assert(nanoseconds(11, 20000000) - nanoseconds(10, 980000000) == 40000000);
  ScanWindows scans;
  assert(scans.advance(second, 720, .25, false, true).status == WindowStatus::first);
  auto w = scans.advance(second + 140000000, 720, .25, false, true);
  assert(w.status == WindowStatus::valid && w.start == second);
  assert(double(w.increment) * 719 <= .14);
  w = scans.advance(second + 250000000, 720, .25, true, false);
  assert(w.status == WindowStatus::valid);
  assert(std::abs(w.duration - .11) < 1e-7);
  assert(double(w.increment) * 719 <= .11);
  assert(scans.advance(second + 380000000, 720, .25, true, true).status == WindowStatus::broken);
  w = scans.advance(second + 500000000, 720, .25, false, true);
  assert(w.status == WindowStatus::valid && w.start == second + 380000000);
  assert(std::abs(w.duration - .12) < 1e-7);
  assert(scans.advance(second + 900000000, 720, .25, false, true).status == WindowStatus::invalid);
  w = scans.advance(2 * second, 720, .25, false, true);
  assert(w.status == WindowStatus::valid && w.start == second + 900000000);
  assert(scans.advance(2 * second, 720, .25, false, true).status == WindowStatus::invalid);
  assert(scans.advance(2 * second - 1, 720, .25, false, true).status == WindowStatus::invalid);
  assert(scans.advance(2 * second + 100000000, 1, .25, false, true).status == WindowStatus::invalid);
  assert(scans.advance(2 * second + 200000000, 720,
    std::numeric_limits<double>::quiet_NaN(), false, true).status == WindowStatus::invalid);
  scans.reset();
  assert(scans.advance(3 * second, 720, .25, false, true).status == WindowStatus::first);
  for (int i = 1; i <= 10000; ++i) {
    const int64_t end = 3 * second + static_cast<int64_t>(i) * 123456789;
    w = scans.advance(end, 720, .25, false, true);
    assert(w.status == WindowStatus::valid);
    assert(double(w.increment) * 719 <= .123456789);
  }
  StreamOrder order;
  assert(order.observe(100, second) == Order::first);
  assert(order.observe(101, second + 1) == Order::forward);
  assert(order.observe(101, second + 1) == Order::duplicate);
  assert(order.observe(99, second - 1) == Order::stale);
  assert(order.observe(102, second) == Order::clock_backward);
  assert(order.observe(102, second + 2) == Order::forward);
  assert(order.observe(105, second + 3) == Order::gap);
  assert(order.observe(0, second + 4) == Order::reset);
  assert(order.observe(1, second + 5) == Order::forward);
  StreamOrder wrap;
  assert(wrap.observe(UINT32_MAX, second) == Order::first);
  assert(wrap.observe(0, second + 1) == Order::forward);
  {
    ScanWindows limits;
    assert(limits.advance(second, 2, .25, false, true).status == WindowStatus::first);
    auto exact = limits.advance(second + 250000000, 2, .25, false, true);
    assert(exact.status == WindowStatus::valid && exact.duration == .25f);
    assert(exact.increment == .25f);
    assert(limits.advance(second + 500000001, 2, .25, false, true).status ==
      WindowStatus::invalid);
    auto recovered = limits.advance(second + 600000001, 2, .25, false, true);
    assert(recovered.status == WindowStatus::valid &&
      recovered.start == second + 500000001);
  }
  {
    ScanWindows rounding;
    rounding.advance(second, 2, .25, false, false);
    auto rounded = rounding.advance(second + 100000000, 2, .25, false, false);
    assert(rounded.status == WindowStatus::valid);
    assert(double(rounded.increment) <= .1);
    assert(std::nextafter(rounded.increment, std::numeric_limits<float>::infinity()) ==
      static_cast<float>(.1));
  }
  {
    ScanWindows invalid_limits;
    invalid_limits.advance(second, 720, .25, false, true);
    int64_t end = second;
    for (double maximum : {0.0, -.25, std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity()}) {
      end += 100000000;
      assert(invalid_limits.advance(end, 720, maximum, false, true).status ==
        WindowStatus::invalid);
      auto recovered = invalid_limits.advance(end + 100000000, 720, .25, false, true);
      assert(recovered.status == WindowStatus::valid && recovered.start == end);
      end += 100000000;
    }
  }
  {
    ScanWindows point_limits;
    point_limits.advance(second, 720, .25, false, true);
    assert(point_limits.advance(second + 100000000, 0, .25, false, true).status ==
      WindowStatus::invalid);
    assert(point_limits.advance(second + 200000000, -1, .25, false, true).status ==
      WindowStatus::invalid);
    auto recovered = point_limits.advance(second + 300000000, 2, .25, false, true);
    assert(recovered.status == WindowStatus::valid &&
      recovered.start == second + 200000000);
  }
  {
    ScanWindows precedence;
    assert(precedence.advance(second, 0, .25, true, true).status == WindowStatus::first);
    assert(precedence.advance(second + 400000000, 720, .25, true, true).status ==
      WindowStatus::invalid);
    assert(precedence.advance(second + 500000000, 720, .25, false, true).status ==
      WindowStatus::valid);
  }
  {
    StreamOrder rejected;
    assert(rejected.observe(100, second) == Order::first);
    assert(rejected.observe(100, second + 100) == Order::duplicate);
    assert(rejected.observe(99, second) == Order::stale);
    assert(rejected.observe(101, second - 1) == Order::clock_backward);
    assert(rejected.observe(101, second + 1) == Order::forward);
  }
  {
    StreamOrder half_range;
    assert(half_range.observe(0, second) == Order::first);
    assert(half_range.observe(INT32_MAX, second + 1) == Order::gap);
    assert(half_range.observe(UINT32_MAX, second + 2) == Order::reset);
  }
  {
    StreamOrder restart;
    assert(restart.observe(100, second) == Order::first);
    assert(restart.observe(50, second + 1) == Order::reset);
    assert(restart.observe(51, second + 2) == Order::forward);
    assert(restart.observe(0, second + 2) == Order::stale);
    assert(restart.observe(52, second + 3) == Order::forward);
  }
  {
    StreamOrder wrap_gap;
    assert(wrap_gap.observe(UINT32_MAX - 1, second) == Order::first);
    assert(wrap_gap.observe(1, second + 1) == Order::gap);
    assert(wrap_gap.observe(2, second + 2) == Order::forward);
  }
  std::cout << "Timing/order edge cases and 10000 non-overlapping windows passed\n";
}
"""


def unit_tests(compiler):
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="kaiaai_timing_") as directory:
        source = Path(directory) / "timing.cpp"
        binary = Path(directory) / "timing_test"
        source.write_text(UNIT_SOURCE, encoding="ascii")
        subprocess.run(
            [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
             "-I", str(root / "src"), str(source), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


def check_report(summary):
    if summary["scan_overlaps"] or summary["odom_timestamp_reversals"]:
        raise AssertionError("Replay failed: overlapping scans or reversed odometry stamps")


def replay(args):
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
    from rclpy.serialization import deserialize_message
    from rosgraph_msgs.msg import Clock as ClockMessage
    from kaiaai_msgs.msg import KaiaaiTelemetry2
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import JointState, LaserScan
    from tf2_msgs.msg import TFMessage

    active_domain = int(os.environ.get("ROS_DOMAIN_ID", "0"))
    if not 1 <= args.domain <= 232 or args.domain == active_domain:
        raise ValueError("Replay requires a nonzero domain different from the live domain")
    os.environ["ROS_DOMAIN_ID"] = str(args.domain)
    os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "LOCALHOST"
    databases = list(Path(args.bag).glob("*.db3"))
    if len(databases) != 1:
        raise ValueError("Expected exactly one SQLite rosbag database")
    with sqlite3.connect(f"file:{databases[0]}?mode=ro", uri=True) as connection:
        topics = dict(connection.execute("SELECT id,name FROM topics"))
        rows = list(connection.execute(
            "SELECT topic_id,timestamp,data FROM messages ORDER BY timestamp,id"))
    raw = [(stamp, data) for tid, stamp, data in rows if topics[tid] == "/telemetry"]
    static = [data for tid, _, data in rows if topics[tid] == "/tf_static"]
    if not raw or not static:
        raise ValueError("Bag must contain raw telemetry and static sensor transforms")
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    bridge_log = report.with_suffix(".bridge.log")
    cartographer_log = report.with_suffix(".cartographer.log")
    for path in (report, bridge_log, cartographer_log):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    rclpy.init()
    node = Node("isolated_timing_replay")
    raw_pub = node.create_publisher(KaiaaiTelemetry2, "/telemetry", 100)
    clock_pub = node.create_publisher(ClockMessage, "/clock", 100)
    static_pub = node.create_publisher(
        TFMessage, "/tf_static",
        QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    scans, odom, joints, yaw = [], [], [], []
    node.create_subscription(LaserScan, "/scan", scans.append, qos_profile_sensor_data)
    node.create_subscription(Odometry, "/odom", odom.append, qos_profile_sensor_data)
    node.create_subscription(JointState, "/joint_states", joints.append, qos_profile_sensor_data)

    def transforms(message):
        for transform in message.transforms:
            if transform.header.frame_id == "map" and transform.child_frame_id == "odom":
                q = transform.transform.rotation
                yaw.append((transform.header.stamp.sec +
                            transform.header.stamp.nanosec * 1e-9,
                            math.atan2(2 * (q.w * q.z + q.x * q.y),
                                       1 - 2 * (q.y * q.y + q.z * q.z))))

    node.create_subscription(TFMessage, "/tf", transforms, 100)
    processes = []
    handles = []
    try:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
        others = [name for name, _ in node.get_node_names_and_namespaces()
                  if name != node.get_name()]
        if others:
            raise RuntimeError(f"Replay domain already occupied: {others}")
        handle = bridge_log.open("x", encoding="utf-8")
        handles.append(handle)
        processes.append(subprocess.Popen(
            [args.node, "--ros-args", "--params-file", args.params,
             "-p", "use_sim_time:=true"], stdout=handle, stderr=subprocess.STDOUT))
        if args.cartographer_config:
            handle = cartographer_log.open("x", encoding="utf-8")
            handles.append(handle)
            processes.append(subprocess.Popen(
                ["/opt/ros/jazzy/lib/cartographer_ros/cartographer_node",
                 "-configuration_directory", args.cartographer_config,
                 "-configuration_basename", "cartographer_lds_2d.lua",
                 "--ros-args", "-p", "use_sim_time:=true"],
                stdout=handle, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + 15
        while raw_pub.get_subscription_count() == 0:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("Replay process exited during startup; inspect its log")
            if time.monotonic() > deadline:
                raise TimeoutError("No isolated bridge subscription appeared")
            rclpy.spin_once(node, timeout_sec=.05)
        first_clock = ClockMessage()
        first_clock.clock.sec, first_clock.clock.nanosec = divmod(raw[0][0], 10**9)
        clock_pub.publish(first_clock)
        for data in static:
            static_pub.publish(deserialize_message(data, TFMessage))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)
        began = time.monotonic()
        for stamp, data in raw:
            due = began + (stamp - raw[0][0]) * 1e-9
            while time.monotonic() < due:
                rclpy.spin_once(node, timeout_sec=max(0, min(.01, due - time.monotonic())))
            clock = ClockMessage()
            clock.clock.sec, clock.clock.nanosec = divmod(stamp, 10**9)
            clock_pub.publish(clock)
            raw_pub.publish(deserialize_message(data, KaiaaiTelemetry2))
            rclpy.spin_once(node, timeout_sec=0)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)
        if not scans or not odom or not joints:
            raise RuntimeError("Replay produced no scans, odometry or joints")
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("Replay process exited unexpectedly; inspect its log")
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        for handle in handles:
            handle.close()
        node.destroy_node()
        rclpy.shutdown()

    def stamp_ns(stamp):
        return stamp.sec * 10**9 + stamp.nanosec

    overlaps = []
    for first, second in zip(scans, scans[1:]):
        excess = ((len(first.ranges) - 1) * first.time_increment -
                  (stamp_ns(second.header.stamp) - stamp_ns(first.header.stamp)) * 1e-9)
        if excess > 1e-8:
            overlaps.append(excess)
    odom_reversals = sum(stamp_ns(b.header.stamp) <= stamp_ns(a.header.stamp)
                         for a, b in zip(odom, odom[1:]))
    angles = [angle for _, angle in yaw]
    unwrapped = [angles[0]] if angles else []
    for a, b in zip(angles, angles[1:]):
        unwrapped.append(unwrapped[-1] + math.atan2(math.sin(b - a), math.cos(b - a)))
    settled = [angle for (stamp, _), angle in zip(yaw, unwrapped)
               if stamp >= yaw[0][0] + 10] if yaw else []
    accepted = []
    previous = None
    for _, data in raw:
        message = deserialize_message(data, KaiaaiTelemetry2)
        current = (message.seq, stamp_ns(message.stamp))
        if previous and (current[0] == previous[0] or current[1] <= previous[1]):
            continue
        previous = current
        accepted.append(message)
    import re
    cartographer_text = (cartographer_log.read_text(encoding="utf-8")
                        if cartographer_log.exists() else "")
    summary = {
        "domain": args.domain, "telemetry_input": len(raw), "scans_output": len(scans),
        "scan_overlaps": len(overlaps),
        "max_overlap_ms": max(overlaps, default=0) * 1000,
        "odom_output": len(odom), "odom_timestamp_reversals": odom_reversals,
        "expected_chronological_odom_output": len(accepted),
        "joints_output": len(joints),
        "joint_positions": sorted({tuple(m.position) for m in joints}),
        "odom_unique_poses": len({(m.pose.pose.position.x, m.pose.pose.position.y,
                                  m.pose.pose.orientation.z, m.pose.pose.orientation.w)
                                 for m in odom}),
        "scan_sizes": sorted({len(m.ranges) for m in scans}),
        "scan_angle_min": sorted({m.angle_min for m in scans}),
        "map_odom_samples": len(yaw),
        "map_odom_yaw_span_deg": math.degrees(max(unwrapped) - min(unwrapped)) if yaw else None,
        "map_odom_yaw_span_after_10s_deg": (
            math.degrees(max(settled) - min(settled)) if settled else None),
        "cartographer_dropped_point_warnings": cartographer_text.count("Dropped "),
        "cartographer_dropped_points": sum(map(int, re.findall(r"Dropped (\d+) earlier points", cartographer_text))),
    }
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if args.cartographer_config and not yaw:
        raise AssertionError("Cartographer produced no map->odom samples")
    if not args.allow_defects:
        check_report(summary)
        if len(odom) != len(accepted) or len(joints) != len(accepted):
            raise AssertionError("Replay lost or duplicated chronological odometry/joint messages")
        expected_poses = {(m.odom_pos_x, m.odom_pos_y) for m in accepted}
        if {(m.pose.pose.position.x, m.pose.pose.position.y) for m in odom} != expected_poses:
            raise AssertionError("Replay changed odometry positions")
        if {tuple(m.position) for m in joints} != {
                tuple(j.pos for j in m.joint[:2]) for m in accepted}:
            raise AssertionError("Replay changed wheel joint positions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", action="store_true")
    parser.add_argument("--compiler", default="c++")
    parser.add_argument("--bag")
    parser.add_argument("--node")
    parser.add_argument("--params")
    parser.add_argument("--domain", type=int, default=173)
    parser.add_argument("--report")
    parser.add_argument("--cartographer-config")
    parser.add_argument("--allow-defects", action="store_true")
    parser.add_argument("--check-report")
    arguments = parser.parse_args()
    if arguments.check_report:
        check_report(json.loads(Path(arguments.check_report).read_text(encoding="utf-8")))
        print("Recorded replay timing/ordering gate passed")
    elif arguments.unit:
        unit_tests(arguments.compiler)
    else:
        if not all((arguments.bag, arguments.node, arguments.params, arguments.report)):
            parser.error("Replay requires --bag, --node, --params and --report")
        replay(arguments)
