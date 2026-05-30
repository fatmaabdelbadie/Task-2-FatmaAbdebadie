import time
import random
import math
import csv
import os
import sys
from datetime import datetime
from collections import deque
from enum import Enum

SAMPLING_INTERVAL = 1.5   # seconds between readings
SYSTEM_RUNTIME    = 90    # total seconds to run (set to 0 for infinite)
CSV_FILE          = "sensor_data.csv"
HISTORY_LEN       = 50    # rolling stats window

class C:
    R  = "\033[0m"
    B  = "\033[1m"
    D  = "\033[2m"
    CY = "\033[96m"
    GN = "\033[92m"
    YL = "\033[93m"
    RD = "\033[91m"
    BL = "\033[94m"
    MG = "\033[95m"
    WH = "\033[97m"

def clr_screen():
    os.system("cls" if os.name == "nt" else "clear")

def bar(value, min_v, max_v, width=20, color=C.GN):
    """Render a visual progress bar."""
    pct   = max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))
    filled = int(pct * width)
    bar_s = "█" * filled + "░" * (width - filled)
    return f"{color}[{bar_s}]{C.R}  {pct*100:5.1f}%"

def status_color(level):
    """Return colour based on alert level string."""
    return {
        "NORMAL":   C.GN,
        "WARNING":  C.YL,
        "CRITICAL": C.RD,
        "OFFLINE":  C.D,
    }.get(level, C.WH)

class DayNightCycle:
    """
    Simulates a compressed day/night cycle.
    Every 60 seconds = 1 full day (adjustable).
    Returns a normalised sun intensity 0.0 (midnight) → 1.0 (noon).
    """
    CYCLE_DURATION = 60.0  # seconds per simulated day

    def __init__(self):
        self._start = time.time()

    def sun_intensity(self) -> float:
        elapsed  = (time.time() - self._start) % self.CYCLE_DURATION
        angle    = 2 * math.pi * elapsed / self.CYCLE_DURATION
        # Sine wave shifted so noon is at half-cycle
        raw      = math.sin(angle - math.pi / 2)
        return max(0.0, raw)  # clamp to [0, 1]

    def time_of_day(self) -> str:
        elapsed = (time.time() - self._start) % self.CYCLE_DURATION
        frac    = elapsed / self.CYCLE_DURATION
        if   frac < 0.25:  return "🌑 Night"
        elif frac < 0.35:  return "🌅 Dawn"
        elif frac < 0.65:  return "☀  Day"
        elif frac < 0.75:  return "🌇 Dusk"
        else:              return "🌑 Night"

class SensorReading:
    def __init__(self, name, value, unit, status, raw_dict=None):
        self.name      = name
        self.value     = value
        self.unit      = unit
        self.status    = status     # "NORMAL" | "WARNING" | "CRITICAL"
        self.raw       = raw_dict or {}
        self.timestamp = datetime.now().strftime("%H:%M:%S")


class BaseSensor:
    def __init__(self, sensor_id: str, name: str):
        self.sensor_id = sensor_id
        self.name      = name
        self._history  = deque(maxlen=HISTORY_LEN)

    def read(self, cycle: DayNightCycle) -> SensorReading:
        raise NotImplementedError

    def record(self, value: float):
        self._history.append(value)

    def stats(self):
        if not self._history:
            return None, None, None
        h = list(self._history)
        return min(h), max(h), sum(h) / len(h)

class DHT22Sensor(BaseSensor):
    """Temperature & Humidity — realistic Gaussian noise + drift."""

    BASE_TEMP  = 22.0
    BASE_HUMID = 50.0
    _temp_drift  = 0.0
    _humid_drift = 0.0

    TEMP_WARN  = 30.0;  TEMP_CRIT  = 35.0
    HUMID_WARN = 70.0;  HUMID_CRIT = 85.0

    def read(self, cycle):
        sun = cycle.sun_intensity()
        # Temperature rises with sun
        self._temp_drift  += random.gauss(0, 0.15)
        self._temp_drift   = max(-4, min(4, self._temp_drift))
        temp = self.BASE_TEMP + sun * 8 + self._temp_drift + random.gauss(0, 0.3)
        temp = round(max(10, min(45, temp)), 1)

        # Humidity inversely correlated with temperature (simplified)
        self._humid_drift += random.gauss(0, 0.2)
        self._humid_drift  = max(-8, min(8, self._humid_drift))
        humid = self.BASE_HUMID - (temp - self.BASE_TEMP) * 0.8 + self._humid_drift + random.gauss(0, 0.5)
        humid = round(max(10, min(100, humid)), 1)

        self.record(temp)
        status = ("CRITICAL" if temp > self.TEMP_CRIT or humid > self.HUMID_CRIT
                  else "WARNING" if temp > self.TEMP_WARN or humid > self.HUMID_WARN
                  else "NORMAL")
        return SensorReading(
            self.name, temp, "°C", status,
            raw_dict={"temperature_c": temp, "humidity_pct": humid}
        )


class LDRSensor(BaseSensor):
    """Light Level — follows day/night cycle with cloud flicker."""

    WARN_LOW = 50;  CRIT_LOW = 10

    def read(self, cycle):
        sun   = cycle.sun_intensity()
        # Occasional cloud flicker
        cloud = random.random() < 0.1
        base  = sun * 950 + 20
        lux   = round(base * (0.3 if cloud else 1.0) + random.gauss(0, 15), 1)
        lux   = max(0, lux)

        self.record(lux)
        status = ("CRITICAL" if lux < self.CRIT_LOW
                  else "WARNING" if lux < self.WARN_LOW
                  else "NORMAL")
        return SensorReading(
            self.name, lux, "lux", status,
            raw_dict={"lux": lux, "time_of_day": cycle.time_of_day(),
                      "cloud_event": cloud}
        )


class PIRSensor(BaseSensor):
    """Motion Detection — Bernoulli with higher probability during day."""

    def read(self, cycle):
        # More movement during daytime
        p_motion = 0.15 + cycle.sun_intensity() * 0.30
        detected = random.random() < p_motion
        # Confidence score
        confidence = round(random.uniform(0.65, 0.99), 2) if detected else 0.0

        self.record(1 if detected else 0)
        status = "WARNING" if detected else "NORMAL"
        return SensorReading(
            self.name, int(detected), "", status,
            raw_dict={"motion": detected, "confidence": confidence}
        )


class MQ135Sensor(BaseSensor):
    """Air Quality / CO₂ — gradual accumulation model."""

    BASE_CO2  = 420    # outdoor baseline ppm
    _indoor_offset = 0

    CO2_WARN = 800;  CO2_CRIT = 1200

    def read(self, cycle):
        # CO₂ gradually rises indoors, reduced by ventilation events
        self._indoor_offset += random.gauss(5, 2)
        if random.random() < 0.05:   # window opened
            self._indoor_offset = max(0, self._indoor_offset - 100)
            ventilation = True
        else:
            ventilation = False

        self._indoor_offset = max(0, min(800, self._indoor_offset))
        co2 = int(self.BASE_CO2 + self._indoor_offset + random.gauss(0, 10))
        co2 = max(350, co2)

        voc = int(random.uniform(50, 400) + self._indoor_offset * 0.3)
        aqi = min(500, int(co2 / 5 + voc / 10))

        self.record(co2)
        status = ("CRITICAL" if co2 > self.CO2_CRIT
                  else "WARNING" if co2 > self.CO2_WARN
                  else "NORMAL")
        return SensorReading(
            self.name, co2, "ppm", status,
            raw_dict={"co2_ppm": co2, "voc_ppb": voc, "aqi": aqi,
                      "ventilation_event": ventilation}
        )


class SW420Sensor(BaseSensor):
    """Vibration / Shock — random impulse model."""

    def read(self, cycle):
        # Occasional vibration events (machinery, footsteps, etc.)
        if random.random() < 0.08:
            magnitude = round(random.uniform(0.5, 3.5), 2)
            event     = True
        else:
            magnitude = round(random.uniform(0.0, 0.15), 2)
            event     = False

        self.record(magnitude)
        status = ("CRITICAL" if magnitude > 2.5
                  else "WARNING" if magnitude > 0.5
                  else "NORMAL")
        return SensorReading(
            self.name, magnitude, "g", status,
            raw_dict={"magnitude_g": magnitude, "shock_event": event}
        )

_log_initialized = False

def log_to_csv(readings: list[SensorReading]):
    global _log_initialized
    if not _log_initialized:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Temperature_C", "Humidity_Pct",
                "Light_Lux", "TimeOfDay", "Motion", "Confidence",
                "CO2_PPM", "VOC_PPB", "AQI",
                "Vibration_G", "ShockEvent",
                "Temp_Status", "Light_Status", "Air_Status", "Vibration_Status"
            ])
        _log_initialized = True

    row = {}
    for r in readings:
        row.update(r.raw)
        row[r.name + "_status"] = r.status

    with open(CSV_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            row.get("temperature_c", ""),
            row.get("humidity_pct", ""),
            row.get("lux", ""),
            row.get("time_of_day", ""),
            int(row.get("motion", 0)),
            row.get("confidence", ""),
            row.get("co2_ppm", ""),
            row.get("voc_ppb", ""),
            row.get("aqi", ""),
            row.get("magnitude_g", ""),
            int(row.get("shock_event", 0)),
            row.get("DHT22_status", ""),
            row.get("LDR_status", ""),
            row.get("MQ135_status", ""),
            row.get("SW420_status", ""),
        ])

def render_dashboard(readings: list[SensorReading],
                     cycle: DayNightCycle,
                     sensors: list[BaseSensor],
                     elapsed: float,
                     sample_count: int):
    clr_screen()

    print(f"{C.CY}{C.B}╔══════════════════════════════════════════════════════════════╗{C.R}")
    print(f"{C.CY}{C.B}║        IoT Multi-Sensor Dashboard  —  Decodelabs Task 2      ║{C.R}")
    print(f"{C.CY}{C.B}╚══════════════════════════════════════════════════════════════╝{C.R}")
    ts  = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    print(f"  {C.D}Time: {ts}  |  Cycle: {cycle.time_of_day()}  |  "
          f"Samples: {sample_count}  |  Runtime: {elapsed:.0f}s{C.R}\n")

    for i, (sensor, reading) in enumerate(zip(sensors, readings)):
        col = status_color(reading.status)
        mn, mx, avg = sensor.stats()

        print(f"  {col}{C.B}{'─'*58}{C.R}")
        print(f"  {col}{C.B}{reading.name:30s}{C.R}  "
              f"Status: {col}{C.B}{reading.status}{C.R}")

        # Primary value + bar
        if reading.name == "PIR Motion":
            motion_str = f"{C.B}{'DETECTED ⚠' if reading.value else 'No motion  ✓'}{C.R}"
            conf_str   = (f"  confidence={reading.raw.get('confidence',0):.2f}"
                          if reading.value else "")
            print(f"  {col}  {motion_str}{conf_str}{C.R}")
        elif reading.name == "SW420 Vibration":
            shock_str = "  💥 SHOCK EVENT" if reading.raw.get("shock_event") else ""
            print(f"  {col}  {reading.value} {reading.unit}{shock_str}{C.R}")
            print(f"  {bar(reading.value, 0, 4, width=30, color=col)}")
        else:
            print(f"  {col}  {reading.value} {reading.unit}{C.R}")
            lo, hi = {
                "DHT22 Temp/Humid": (10,  45),
                "LDR Light":        (0,  1000),
                "MQ135 Air Quality":(350, 2000),
            }.get(reading.name, (0, 100))
            print(f"  {bar(reading.value, lo, hi, width=30, color=col)}")

        # Extra fields
        extras = {k: v for k, v in reading.raw.items()
                  if k not in ("temperature_c", "lux", "co2_ppm", "magnitude_g",
                               "motion", "time_of_day", "shock_event")}
        if extras:
            extra_str = "  ".join(f"{k}={v}" for k, v in list(extras.items())[:3])
            print(f"  {C.D}  {extra_str}{C.R}")

        # Rolling stats
        if mn is not None:
            print(f"  {C.D}  Stats (last {HISTORY_LEN}):  "
                  f"min={mn:.1f}  max={mx:.1f}  avg={avg:.1f}{C.R}")

    print(f"\n  {C.D}Logging to: {os.path.abspath(CSV_FILE)}{C.R}")
    print(f"  {C.D}Press Ctrl+C to stop.{C.R}")

def print_summary(sensors: list[BaseSensor], sample_count: int):
    print(f"\n{C.CY}{C.B}{'═'*60}{C.R}")
    print(f"{C.CY}{C.B}  SIMULATION SUMMARY{C.R}")
    print(f"{C.CY}{'═'*60}{C.R}")
    print(f"  Total samples collected : {sample_count}")
    print(f"  Data saved to           : {os.path.abspath(CSV_FILE)}\n")
    print(f"  {C.B}Sensor Statistics (full session):{C.R}")
    for s in sensors:
        mn, mx, avg = s.stats()
        if mn is not None:
            print(f"    {s.name:25s}  min={mn:.2f}  max={mx:.2f}  avg={avg:.2f}")
    print(f"{C.CY}{'═'*60}{C.R}\n")

def main():
    sensors = [
        DHT22Sensor("dht22-01", "DHT22 Temp/Humid"),
        LDRSensor  ("ldr-01",   "LDR Light"),
        PIRSensor  ("pir-01",   "PIR Motion"),
        MQ135Sensor("mq135-01", "MQ135 Air Quality"),
        SW420Sensor("sw420-01", "SW420 Vibration"),
    ]
    cycle  = DayNightCycle()
    start  = time.time()
    count  = 0

    print(f"\n{C.GN}{C.B}  IoT Multi-Sensor Simulation starting...{C.R}")
    print(f"  {C.D}Runtime: {SYSTEM_RUNTIME}s  |  "
          f"Interval: {SAMPLING_INTERVAL}s  |  "
          f"Log: {CSV_FILE}{C.R}\n")
    time.sleep(1.0)

    try:
        while True:
            elapsed = time.time() - start
            if SYSTEM_RUNTIME > 0 and elapsed >= SYSTEM_RUNTIME:
                break

            readings = [s.read(cycle) for s in sensors]
            count   += 1

            render_dashboard(readings, cycle, sensors, elapsed, count)
            log_to_csv(readings)
            time.sleep(SAMPLING_INTERVAL)

    except KeyboardInterrupt:
        pass

    print_summary(sensors, count)


if __name__ == "__main__":
    main()
