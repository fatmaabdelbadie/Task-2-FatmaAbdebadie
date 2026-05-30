# 📟 IoT Multi-Sensor Data Simulation Engine

> **Decodelabs IoT Internship — Task 2**

A realistic, physics-inspired IoT sensor simulation engine that models **5 different sensor types** with authentic noise, drift, and environmental coupling — all visualised in a live coloured terminal dashboard with CSV data export.

---

## ✨ What Makes This Unique

Most sensor simulations use `random.randint()`. This one doesn't:

- **DHT22**: Gaussian noise + slow drift + temperature-humidity inverse correlation
- **LDR**: Follows a compressed day/night sine-wave cycle with random cloud flicker events
- **PIR**: Bernoulli detection probability increases during simulated daytime
- **MQ135**: Gradual indoor CO₂ accumulation model with random ventilation events
- **SW420**: Impulse-based vibration model with shock detection threshold

---

## 🗂️ Project Structure

```
task2_sensor_simulation/
│
├── sensor_simulation.py    # Full simulation engine + live dashboard
├── sensor_data.csv         # Auto-generated data log (created on run)
├── requirements.txt        # No external dependencies!
└── README.md               # This file
```

---

## 🌡️ Sensors Simulated

| Sensor | Model | Measures | Unit | Alert Threshold |
|--------|-------|----------|------|-----------------|
| DHT22 | Gaussian noise + drift | Temperature + Humidity | °C / % | Temp > 30°C, Humid > 70% |
| LDR | Day/night sine cycle | Light Level | lux | < 50 lux |
| PIR | Time-weighted Bernoulli | Motion Detection | binary | Any detection |
| MQ-135 | Accumulation model | CO₂ / Air Quality | ppm | > 800 ppm |
| SW-420 | Shock impulse model | Vibration | g | > 0.5 g |

---

## 🚀 Getting Started

### No installation needed!

```bash
python sensor_simulation.py
```

### Customise behaviour (top of file):
```python
SAMPLING_INTERVAL = 1.5   # seconds between readings
SYSTEM_RUNTIME    = 90    # total runtime (0 = infinite)
CSV_FILE          = "sensor_data.csv"
```

---

## 📸 Sample Terminal Output

```
╔══════════════════════════════════════════════════════════════╗
║        IoT Multi-Sensor Dashboard  —  Decodelabs Task 2      ║
╚══════════════════════════════════════════════════════════════╝
  Time: 2025-06-01  14:23:41  |  Cycle: ☀  Day  |  Samples: 12  |  Runtime: 18s

  ──────────────────────────────────────────────────────────
  DHT22 Temp/Humid                Status: WARNING
    28.4 °C
    [████████████████░░░░]   72.0%
    humidity_pct=52.1
    Stats (last 50):  min=22.1  max=28.4  avg=24.8

  ──────────────────────────────────────────────────────────
  PIR Motion                      Status: WARNING
    DETECTED ⚠  confidence=0.87

  ──────────────────────────────────────────────────────────
  MQ135 Air Quality               Status: NORMAL
    487 ppm
    [████████░░░░░░░░░░░░]   42.8%
    voc_ppb=134  aqi=112
```

---

## 📊 CSV Log Format

`sensor_data.csv` is created automatically with one row per sample:

| Column | Description |
|--------|-------------|
| Timestamp | ISO datetime |
| Temperature_C | DHT22 temperature |
| Humidity_Pct | DHT22 humidity |
| Light_Lux | LDR light level |
| TimeOfDay | Simulated time of day |
| Motion | PIR detection (0/1) |
| CO2_PPM | MQ135 CO₂ reading |
| AQI | Air Quality Index |
| Vibration_G | SW420 magnitude |
| ShockEvent | Shock detected (0/1) |
| *_Status | NORMAL/WARNING/CRITICAL |

---

## 🔑 Key IoT Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| Sensor data generation | 5 physics-inspired sensor models |
| Realistic noise/drift | Gaussian noise, drift walk, impulse model |
| Environmental coupling | Light and temperature follow day/night cycle |
| Data display | Live terminal dashboard with colour status bars |
| Data storage | CSV logging — every sample persisted |
| Rolling statistics | Min/Max/Average over last 50 readings |
| Alert thresholds | Per-sensor WARNING and CRITICAL levels |

---

## 📦 Requirements

```
Python >= 3.10  (standard library only — nothing to install)
```

---

## 👤 Author

Decodelabs IoT Internship Project
