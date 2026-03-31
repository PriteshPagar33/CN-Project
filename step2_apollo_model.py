"""
=================================================================
AoI Project — STEP 2: Apollo DAG Model
Command: python3 step2_apollo_model.py
=================================================================
This file builds the EXACT Apollo ADS model from the paper.

From Paper Figure 6 and Table:
  V1: Localization      WCET=18.2ms   driven by GNSS  (12.5 Hz)
  V2: Segmentation      WCET=49.8ms   driven by LiDAR (10 Hz)
  V3: Image Processing  WCET=26.3ms   driven by Cam1  (15 Hz)
  V4: Image Processing* WCET=24.9ms   driven by Cam2  (15 Hz)
  V5: Recognition       WCET=8.4ms    depends on V2
  V6: Traffic Light     WCET=48.4ms   depends on V3
  V7: Traffic Light*    WCET=39.2ms   depends on V4
  V8: Prediction        WCET=18.6ms   depends on V1,V5
  V9: Planning (final)  WCET=86.4ms   depends on V6,V7,V8

Sensors (from paper):
  Sensor 1: GNSS       → 12.5 Hz → period = 80ms
  Sensor 2: LiDAR      → 10 Hz   → period = 100ms
  Sensor 3: Camera 1   → 15 Hz   → period = 66.7ms ≈ 67ms
  Sensor 4: Camera 2   → 15 Hz   → period = 66.7ms ≈ 67ms
  Sensor 5: CANBUS     → 10 Hz   → period = 100ms

Hyper-period H = LCM(80,100,67) ≈ 400ms (as stated in paper)
=================================================================
"""

import json, os

# ── Task definitions from paper Table (Figure 6) ──────────────
TASKS = {
    "V1": {"name": "Localization",      "wcet": 18.2, "sensor": "GNSS",    "deps": []},
    "V2": {"name": "Segmentation",      "wcet": 49.8, "sensor": "LiDAR",   "deps": []},
    "V3": {"name": "Image Processing",  "wcet": 26.3, "sensor": "Camera1", "deps": []},
    "V4": {"name": "Image Processing*", "wcet": 24.9, "sensor": "Camera2", "deps": []},
    "V5": {"name": "Recognition",       "wcet": 8.4,  "sensor": None,      "deps": ["V2"]},
    "V6": {"name": "Traffic Light",     "wcet": 48.4, "sensor": None,      "deps": ["V3"]},
    "V7": {"name": "Traffic Light*",    "wcet": 39.2, "sensor": None,      "deps": ["V4"]},
    "V8": {"name": "Prediction",        "wcet": 18.6, "sensor": None,      "deps": ["V1", "V5"]},
    "V9": {"name": "Planning",          "wcet": 86.4, "sensor": None,      "deps": ["V6", "V7", "V8"]},
}

# ── Sensor definitions from paper ─────────────────────────────
SENSORS = {
    "GNSS":    {"freq_hz": 12.5, "period_ms": 80.0},
    "LiDAR":   {"freq_hz": 10.0, "period_ms": 100.0},
    "Camera1": {"freq_hz": 15.0, "period_ms": 66.7},
    "Camera2": {"freq_hz": 15.0, "period_ms": 66.7},
    "CANBUS":  {"freq_hz": 10.0, "period_ms": 100.0},
}

# Hyper-period as stated in paper
HYPER_PERIOD_MS = 400.0

# ── Compute execution order (topological sort) ─────────────────
def topological_order(tasks):
    visited, order = set(), []
    def visit(tid):
        if tid in visited: return
        visited.add(tid)
        for dep in tasks[tid]["deps"]:
            visit(dep)
        order.append(tid)
    for tid in tasks:
        visit(tid)
    return order

EXEC_ORDER = topological_order(TASKS)

# ── Compute earliest possible start time for each task ─────────
def compute_earliest_start(tasks, exec_order):
    finish = {}
    start  = {}
    for tid in exec_order:
        dep_finish = max([finish[d] for d in tasks[tid]["deps"]], default=0.0)
        start[tid]  = dep_finish
        finish[tid] = dep_finish + tasks[tid]["wcet"]
    return start, finish

EARLIEST_START, EARLIEST_FINISH = compute_earliest_start(TASKS, EXEC_ORDER)

# ── Critical path length (minimum time to complete one round) ──
CRITICAL_PATH_MS = EARLIEST_FINISH["V9"]

# ── Print model summary ────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  Apollo ADS Model — from Paper Figure 6")
    print("=" * 65)
    print(f"\n  {'Task':<6} {'Name':<22} {'WCET':>7}  {'Sensor':<10} {'Dependencies'}")
    print("  " + "-" * 60)
    for tid in EXEC_ORDER:
        t = TASKS[tid]
        deps = ", ".join(t["deps"]) if t["deps"] else "none"
        sensor = t["sensor"] if t["sensor"] else "—"
        print(f"  {tid:<6} {t['name']:<22} {t['wcet']:>5.1f}ms  {sensor:<10} {deps}")

    print(f"\n  Sensors:")
    for sname, s in SENSORS.items():
        print(f"    {sname:<10} {s['freq_hz']:>5} Hz   period={s['period_ms']:.1f}ms")

    print(f"\n  Hyper-period H     = {HYPER_PERIOD_MS}ms  (as in paper)")
    print(f"  Critical path      = {CRITICAL_PATH_MS:.1f}ms")
    print(f"  Execution order    : {' → '.join(EXEC_ORDER)}")

    print(f"\n  Earliest finish times (single-core, no parallelism):")
    for tid in EXEC_ORDER:
        print(f"    {tid}: starts {EARLIEST_START[tid]:.1f}ms  finishes {EARLIEST_FINISH[tid]:.1f}ms")

    # Save model to JSON for use by other steps
    model = {
        "tasks": TASKS,
        "sensors": SENSORS,
        "hyper_period_ms": HYPER_PERIOD_MS,
        "critical_path_ms": CRITICAL_PATH_MS,
        "exec_order": EXEC_ORDER,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/apollo_model.json", "w") as f:
        json.dump(model, f, indent=2)

    print("\n  ✓ Model saved to results/apollo_model.json")
    print("\n  Next step: python3 step3_schedulers.py")
    print("=" * 65)
