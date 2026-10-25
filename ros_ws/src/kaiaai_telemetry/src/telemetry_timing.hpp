#pragma once

#include <cmath>
#include <cstdint>
#include <limits>

namespace telemetry_timing
{
inline int64_t nanoseconds(int32_t seconds, uint32_t nanos)
{
  return static_cast<int64_t>(seconds) * 1000000000LL + nanos;
}

enum class Order { first, forward, gap, duplicate, stale, clock_backward, reset };

class StreamOrder
{
public:
  Order observe(uint32_t sequence, int64_t stamp)
  {
    if (!initialized_) {
      initialized_ = true;
      last_sequence_ = sequence;
      last_stamp_ = stamp;
      return Order::first;
    }
    const uint32_t delta = sequence - last_sequence_;
    if (delta == 0) {
      return Order::duplicate;
    }
    if (delta > std::numeric_limits<int32_t>::max() && stamp <= last_stamp_) {
      return Order::stale;
    }
    if (stamp <= last_stamp_) {
      return Order::clock_backward;
    }
    last_sequence_ = sequence;
    last_stamp_ = stamp;
    if (delta > std::numeric_limits<int32_t>::max()) {
      return Order::reset;
    }
    return delta > 1 ? Order::gap : Order::forward;
  }

private:
  bool initialized_ = false;
  uint32_t last_sequence_ = 0;
  int64_t last_stamp_ = 0;
};

enum class WindowStatus { valid, first, broken, invalid };

struct Window
{
  WindowStatus status;
  int64_t start;
  float duration;
  float increment;
};

class ScanWindows
{
public:
  Window advance(int64_t end, int points, double maximum_duration,
    bool broken, bool discard_broken)
  {
    const int64_t start = boundary_;
    const bool first = !initialized_;
    boundary_ = end;
    initialized_ = true;
    if (first) {
      return {WindowStatus::first, start, 0.0f, 0.0f};
    }
    const double duration = static_cast<double>(end - start) * 1e-9;
    if (points < 2 || !std::isfinite(maximum_duration) ||
      duration <= 0.0 || duration > maximum_duration)
    {
      return {WindowStatus::invalid, start, 0.0f, 0.0f};
    }
    if (broken && discard_broken) {
      return {WindowStatus::broken, start, 0.0f, 0.0f};
    }
    float increment = static_cast<float>(duration / (points - 1));
    // Float rounding must not put the final ray beyond this revolution's end.
    if (static_cast<double>(increment) * (points - 1) > duration) {
      increment = std::nextafter(increment, 0.0f);
    }
    return {WindowStatus::valid, start, static_cast<float>(duration), increment};
  }

  void reset()
  {
    initialized_ = false;
    boundary_ = 0;
  }

private:
  bool initialized_ = false;
  int64_t boundary_ = 0;
};
}  // namespace telemetry_timing
