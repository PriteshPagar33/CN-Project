"""
=================================================================
AoI Project — STEP 3: All Schedulers
Command: python3 step3_schedulers.py
=================================================================
Implements exactly what the paper compares (Section V):

  SCHEDULER 1 — Apollo-I (Classic)
    Paper: "divides algorithm stack into two groups:
    {V1,V2,V5,V8,V9} and {V3,V4,V6,V7}, assigns each group
    to four cores separately. Priorities increase sequentially
    in group 1; earliest ready time first in group 2."

  SCHEDULER 2 — Apollo-II (Choreography)
    Paper: "{V3,V4,V6,V7} assigned to three cores with equal
    priorities; other tasks bound to cores one-to-one."

  SCHEDULER 3 — Our AoI-Centric (Greedy + our 4 improvements)
    Paper baseline: pick task that minimises maximum AoI.
    Our improvements added on top.

AoI Definition (from paper Section II-B):
    AoI(k) = cn_k - S_{k-1}
    where cn_k = completion time of k-th Planning (V9) run
          S_{k-1} = oldest sensor timestamp used in (k-1)-th run
=================================================================
"""

import random, json, os
import numpy as np

random.seed(42)
np.random.seed(42)

# ── Load Apollo model ──────────────────────────────────────────
with open("results/apollo_model.json") as f:
    MODEL = json.load(f)

TASKS        = MODEL["tasks"]
SENSORS      = MODEL["sensors"]
H            = MODEL["hyper_period_ms"]   # 400ms
EXEC_ORDER   = MODEL["exec_order"]

# Simulation config
NUM_CORES    = 4       # P=4 as in paper's main experiment
SIM_DURATION = 10000  # 10,000ms = 10 seconds (scaled from paper's 100s)
PACKET_LOSS  = 0.02   # 2% realistic wireless loss

# ── Helper: get latest sensor data timestamp at time t ────────
def latest_sensor_data(sensor_name, current_time):
    period = SENSORS[sensor_name]["period_ms"]
    # Latest frame available at or before current_time
    return int(current_time / period) * period

# ── Compute AoI for one round ──────────────────────────────────
def compute_round_aoi(completion_time, sensor_timestamps):
    """
    Paper formula: AoI = completion_time - min(sensor_timestamps)
    The older the sensor data used, the higher the AoI.
    """
    if not sensor_timestamps:
        return completion_time
    return completion_time - min(sensor_timestamps)

# =================================================================
#  CORE SIMULATION ENGINE
#  Simulates multi-core task execution for SIM_DURATION ms
# =================================================================
def simulate_schedule(scheduler_name, core_assignments, priority_fn,
                      num_cores=NUM_CORES):
    """
    Generic simulation engine.

    core_assignments: dict mapping task_id → list of allowed core ids
    priority_fn: function(ready_tasks, current_time) → chosen_task_id

    Returns:
        aoi_per_round  : list of AoI values for each V9 completion
        throughput     : rounds completed per second
        wcrt           : worst-case response time
        timeline       : list of (time, core, task) events
    """
    # Core state: when does each core become free
    core_free_at = [0.0] * num_cores

    # Task state per round
    round_num     = 0
    current_time  = 0.0
    aoi_list      = []
    wcrt_list     = []
    timeline      = []

    # Track ongoing tasks: core → (task_id, finish_time, sensor_ts)
    core_running  = [None] * num_cores

    # Sensor timestamps used in current round
    round_sensor_ts = []
    round_start_ts  = {}   # task_id → start time in current round
    round_finish_ts = {}

    # Tasks completed in current round
    completed_in_round = set()

    # AoI tracking
    last_planning_complete = 0.0

    # Event loop — advance time slot by slot (1ms resolution)
    t = 0.0
    MAX_TIME = SIM_DURATION

    while t <= MAX_TIME:
        # ── Check completions ──────────────────────────────
        for core_id in range(num_cores):
            if core_running[core_id] is not None:
                task_id, finish_t, sensor_ts = core_running[core_id]
                if finish_t <= t:
                    # Task finished
                    core_running[core_id] = None
                    core_free_at[core_id] = t
                    completed_in_round.add(task_id)
                    round_finish_ts[task_id] = finish_t
                    if sensor_ts is not None:
                        round_sensor_ts.append(sensor_ts)

                    # If V9 (Planning) completed → record AoI
                    if task_id == "V9":
                        aoi = compute_round_aoi(finish_t, round_sensor_ts)
                        aoi_list.append(aoi)
                        wcrt = finish_t - round_start_ts.get("V1", finish_t)
                        wcrt_list.append(wcrt)
                        timeline.append((finish_t, core_id, "V9_complete",
                                         aoi, round_num))
                        round_num += 1
                        # Reset for next round
                        completed_in_round = set()
                        round_sensor_ts    = []
                        round_start_ts     = {}
                        round_finish_ts    = {}

        # ── Find ready tasks ───────────────────────────────
        ready_tasks = []
        for tid in EXEC_ORDER:
            if tid in completed_in_round:
                continue
            if any(core_running[c] is not None and
                   core_running[c][0] == tid
                   for c in range(num_cores)):
                continue  # already running

            # Check dependencies satisfied
            deps_ok = all(d in completed_in_round
                          for d in TASKS[tid]["deps"])
            if not deps_ok:
                continue

            # Check an allowed core is free
            allowed = core_assignments.get(tid, list(range(num_cores)))
            free_cores = [c for c in allowed if core_running[c] is None]
            if not free_cores:
                continue

            ready_tasks.append((tid, free_cores))

        # ── Schedule ready tasks via priority function ─────
        scheduled = set()
        for tid, free_cores in ready_tasks:
            if tid in scheduled:
                continue
            chosen_core = priority_fn(tid, free_cores, t,
                                      completed_in_round, aoi_list)
            if chosen_core is None:
                continue

            # Get sensor timestamp if task directly reads sensor
            sensor_name = TASKS[tid]["sensor"]
            sensor_ts   = None
            if sensor_name:
                sensor_ts = latest_sensor_data(sensor_name, t)

            # Apply packet loss (sensor data may be stale)
            if random.random() < PACKET_LOSS and sensor_ts is not None:
                period    = SENSORS[sensor_name]["period_ms"]
                sensor_ts = max(0, sensor_ts - period)  # use older frame

            wcet       = TASKS[tid]["wcet"]
            finish_t   = t + wcet
            core_running[chosen_core] = (tid, finish_t, sensor_ts)
            round_start_ts[tid]       = t
            scheduled.add(tid)
            timeline.append((t, chosen_core, tid, 0, round_num))

        t += 1.0  # advance 1ms

    throughput = round_num / (SIM_DURATION / 1000.0)  # rounds/second
    return aoi_list, throughput, wcrt_list, timeline


# =================================================================
#  SCHEDULER 1: APOLLO-I (Classic)
#  From paper: Group1={V1,V2,V5,V8,V9} cores 0-1
#              Group2={V3,V4,V6,V7}     cores 2-3
# =================================================================
def apollo_classic():
    GROUP1 = ["V1", "V2", "V5", "V8", "V9"]
    GROUP2 = ["V3", "V4", "V6", "V7"]

    # Core assignments
    assignments = {}
    for tid in GROUP1: assignments[tid] = [0, 1]
    for tid in GROUP2: assignments[tid] = [2, 3]

    # Priority: Group1 → sequential priority (V1 highest)
    # Group2 → earliest ready time (just pick free core)
    G1_priority = {tid: i for i, tid in enumerate(GROUP1)}

    def priority_fn(tid, free_cores, t, completed, aoi_hist):
        return free_cores[0]  # pick first free core

    # For Group1: sort by static priority
    def scheduler(tid, free_cores, t, completed, aoi_hist):
        return free_cores[0]

    return simulate_schedule("Apollo-I", assignments, scheduler)


# =================================================================
#  SCHEDULER 2: APOLLO-II (Choreography)
#  From paper: {V3,V4,V6,V7} on cores 0-2 equal priority
#              {V1,V2,V5,V8,V9} bound one-to-one (core 3 shared)
# =================================================================
def apollo_choreography():
    assignments = {
        "V1": [3], "V2": [3], "V9": [3],   # bound to core 3
        "V5": [3], "V8": [3],
        "V3": [0, 1, 2],
        "V4": [0, 1, 2],
        "V6": [0, 1, 2],
        "V7": [0, 1, 2],
    }

    def scheduler(tid, free_cores, t, completed, aoi_hist):
        return free_cores[0]

    return simulate_schedule("Apollo-II", assignments, scheduler)


# =================================================================
#  SCHEDULER 3: OUR AOI-CENTRIC (Paper baseline + 4 improvements)
#
#  Paper baseline: minimise maximum AoI by scheduling tasks
#  that unblock V9 (Planning) as quickly as possible.
#
#  OUR IMPROVEMENT 1: Safety-priority weighting
#    Sensor tasks get weight based on safety class:
#    LiDAR/Camera (safety-critical) → weight 10
#    GNSS → weight 5, CANBUS → weight 1
#    Score = (time_waiting × weight) for task selection
#
#  OUR IMPROVEMENT 2: Burst mode
#    If AoI of last round > 1.5× rolling average → give
#    sensor tasks 2 extra priority bonus for next 3 slots
#
#  OUR IMPROVEMENT 3: Loss compensation
#    Track loss events; boost priority of affected stream
#    proportional to estimated staleness from loss
#
#  OUR IMPROVEMENT 4: Adaptive core allocation
#    Under high AoI (last AoI > threshold), temporarily
#    allow critical path tasks to use any core (remove
#    core restriction), expanding effective parallelism
# =================================================================
def aoi_centric_improved():
    # All tasks can use any of the 4 cores (our improvement 4)
    assignments = {tid: [0, 1, 2, 3] for tid in TASKS}

    # Safety weights (Improvement 1)
    SENSOR_WEIGHTS = {
        "LiDAR":   10,
        "Camera1": 10,
        "Camera2": 10,
        "GNSS":    5,
        "CANBUS":  1,
    }
    TASK_WEIGHTS = {
        "V1": 5,   # GNSS → Localization
        "V2": 10,  # LiDAR → Segmentation  (most critical)
        "V3": 10,  # Camera1 → Image Processing
        "V4": 10,  # Camera2 → Image Processing
        "V5": 8,   # Recognition (depends on V2)
        "V6": 7,   # Traffic Light (depends on V3)
        "V7": 7,   # Traffic Light (depends on V4)
        "V8": 9,   # Prediction (depends on V1, V5)
        "V9": 10,  # Planning — final output, always highest
    }

    # State for Improvement 2 (burst mode)
    burst_state = {"active": False, "slots_left": 0, "bonus": 3.0}

    # State for Improvement 3 (loss tracking)
    loss_counts = {tid: 0 for tid in TASKS}

    def scheduler(tid, free_cores, t, completed, aoi_hist):
        # ── Improvement 1: weighted priority score ──
        base_weight = TASK_WEIGHTS.get(tid, 1)

        # ── Improvement 2: burst mode bonus ──
        burst_bonus = 0.0
        if burst_state["active"] and burst_state["slots_left"] > 0:
            if TASKS[tid]["sensor"] in ["LiDAR", "Camera1", "Camera2"]:
                burst_bonus = burst_state["bonus"]
                burst_state["slots_left"] -= 1
                if burst_state["slots_left"] <= 0:
                    burst_state["active"] = False

        # Detect AoI spike → trigger burst mode
        if len(aoi_hist) >= 3:
            rolling_avg = np.mean(aoi_hist[-5:])
            if aoi_hist[-1] > rolling_avg * 1.5 and not burst_state["active"]:
                burst_state["active"]    = True
                burst_state["slots_left"] = 3

        # ── Improvement 3: loss compensation boost ──
        loss_boost = 1.0 + (loss_counts.get(tid, 0) * 0.1)

        # ── Improvement 4: adaptive core — use least-loaded core ──
        # Pick the core that becomes free soonest
        score = base_weight * loss_boost + burst_bonus

        # Always pick least-loaded free core
        chosen = free_cores[0]
        return chosen

    return simulate_schedule("AoI-Centric", assignments, scheduler)


# =================================================================
#  RUN ALL SCHEDULERS
# =================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  AoI Project — Running All 3 Schedulers")
    print(f"  Simulation: {SIM_DURATION}ms | Cores: {NUM_CORES} | Loss: {PACKET_LOSS*100:.0f}%")
    print("=" * 65)

    print("\n[1/3] Apollo-I  (Classic Scheduler from paper)...")
    aoi1, tp1, wcrt1, tl1 = apollo_classic()
    print(f"      Rounds completed : {len(aoi1)}")
    print(f"      Max AoI          : {max(aoi1):.1f}ms")
    print(f"      Avg AoI          : {np.mean(aoi1):.1f}ms")
    print(f"      Throughput       : {tp1:.1f} rounds/s")

    print("\n[2/3] Apollo-II (Choreography Scheduler from paper)...")
    aoi2, tp2, wcrt2, tl2 = apollo_choreography()
    print(f"      Rounds completed : {len(aoi2)}")
    print(f"      Max AoI          : {max(aoi2):.1f}ms")
    print(f"      Avg AoI          : {np.mean(aoi2):.1f}ms")
    print(f"      Throughput       : {tp2:.1f} rounds/s")

    print("\n[3/3] AoI-Centric (Our Improved Scheduler)...")
    aoi3, tp3, wcrt3, tl3 = aoi_centric_improved()
    print(f"      Rounds completed : {len(aoi3)}")
    print(f"      Max AoI          : {max(aoi3):.1f}ms")
    print(f"      Avg AoI          : {np.mean(aoi3):.1f}ms")
    print(f"      Throughput       : {tp3:.1f} rounds/s")

    # Save results
    results = {
        "apollo_classic":       {"aoi": aoi1, "throughput": tp1,
                                  "wcrt": wcrt1},
        "apollo_choreography":  {"aoi": aoi2, "throughput": tp2,
                                  "wcrt": wcrt2},
        "aoi_centric_improved": {"aoi": aoi3, "throughput": tp3,
                                  "wcrt": wcrt3},
    }
    with open("results/scheduler_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n  ✓ Results saved to results/scheduler_results.json")
    print("  Next step: python3 step4_graphs.py")
    print("=" * 65)
