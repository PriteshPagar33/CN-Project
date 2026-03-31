"""
=================================================================
AoI Project — STEP 5: Generate Report Numbers
Command: python3 step5_report_numbers.py
=================================================================
Prints ALL numbers you need for your report in one place.
Copy-paste directly into your report document.
=================================================================
"""

import json, os
import numpy as np

with open("results/scheduler_results.json") as f:
    R = json.load(f)

aoi1 = R["apollo_classic"]["aoi"]
aoi2 = R["apollo_choreography"]["aoi"]
aoi3 = R["aoi_centric_improved"]["aoi"]
tp1  = R["apollo_classic"]["throughput"]
tp2  = R["apollo_choreography"]["throughput"]
tp3  = R["aoi_centric_improved"]["throughput"]
w1   = R["apollo_classic"]["wcrt"]
w2   = R["apollo_choreography"]["wcrt"]
w3   = R["aoi_centric_improved"]["wcrt"]

print("=" * 65)
print("  REPORT NUMBERS — Copy these into your report")
print("=" * 65)

print("""
TABLE I: Apollo ADS Task Parameters (from paper Figure 6)
┌─────┬──────────────────────┬──────────┬──────────────┐
│Task │ Name                 │ WCET(ms) │ Dependencies │
├─────┼──────────────────────┼──────────┼──────────────┤
│ V1  │ Localization         │   18.2   │ (GNSS 12.5Hz)│
│ V2  │ Segmentation         │   49.8   │ (LiDAR 10Hz) │
│ V3  │ Image Processing     │   26.3   │ (Cam1 15Hz)  │
│ V4  │ Image Processing*    │   24.9   │ (Cam2 15Hz)  │
│ V5  │ Recognition          │    8.4   │ V2           │
│ V6  │ Traffic Light        │   48.4   │ V3           │
│ V7  │ Traffic Light*       │   39.2   │ V4           │
│ V8  │ Prediction           │   18.6   │ V1, V5       │
│ V9  │ Planning (output)    │   86.4   │ V6, V7, V8   │
└─────┴──────────────────────┴──────────┴──────────────┘
Hyper-period H = 400ms | P = 4 cores
""")

print("TABLE II: Simulation Results")
print(f"  {'Metric':<32} {'Apollo-I':>10} {'Apollo-II':>11} {'OURS':>10}")
print("  " + "-" * 65)
print(f"  {'Max AoI (ms)':<32} {max(aoi1):>10.1f} {max(aoi2):>11.1f} {max(aoi3):>10.1f}")
print(f"  {'Mean AoI (ms)':<32} {np.mean(aoi1):>10.1f} {np.mean(aoi2):>11.1f} {np.mean(aoi3):>10.1f}")
print(f"  {'Min AoI (ms)':<32} {min(aoi1):>10.1f} {min(aoi2):>11.1f} {min(aoi3):>10.1f}")
print(f"  {'Std Dev AoI (ms)':<32} {np.std(aoi1):>10.1f} {np.std(aoi2):>11.1f} {np.std(aoi3):>10.1f}")
print(f"  {'95th Percentile AoI (ms)':<32} {np.percentile(aoi1,95):>10.1f} {np.percentile(aoi2,95):>11.1f} {np.percentile(aoi3,95):>10.1f}")
print(f"  {'Throughput (rounds/sec)':<32} {tp1:>10.2f} {tp2:>11.2f} {tp3:>10.2f}")
if w1: print(f"  {'Avg WCRT (ms)':<32} {np.mean(w1):>10.1f} {np.mean(w2):>11.1f} {np.mean(w3):>10.1f}")
print(f"  {'Total rounds':<32} {len(aoi1):>10} {len(aoi2):>11} {len(aoi3):>10}")

g_max = ((max(aoi1)-max(aoi3))/max(aoi1))*100
g_avg = ((np.mean(aoi1)-np.mean(aoi3))/np.mean(aoi1))*100
g_tp  = ((tp3-tp1)/tp1)*100

print(f"""
TABLE III: Our Improvements vs Apollo-I
  Max AoI reduction  : {g_max:+.1f}%
  Avg AoI reduction  : {g_avg:+.1f}%
  Throughput gain    : {g_tp:+.1f}%
""")

print("""
TABLE IV: Our 4 Improvements Description
┌──────┬───────────────────────────────┬──────────────────────────────┐
│  #   │ Improvement                   │ What It Does                 │
├──────┼───────────────────────────────┼──────────────────────────────┤
│  1   │ Safety-Priority Weighting     │ LiDAR/Camera get 10x higher  │
│      │                               │ scheduling priority vs CANBUS│
├──────┼───────────────────────────────┼──────────────────────────────┤
│  2   │ Burst Mode (AoI Spike)        │ 3 bonus slots when AoI jumps │
│      │                               │ 1.5x above rolling average   │
├──────┼───────────────────────────────┼──────────────────────────────┤
│  3   │ Loss Compensation             │ Boost priority for streams   │
│      │                               │ with elevated packet loss    │
├──────┼───────────────────────────────┼──────────────────────────────┤
│  4   │ Adaptive Core Allocation      │ Under high AoI, allow all    │
│      │                               │ tasks to use any free core   │
└──────┴───────────────────────────────┴──────────────────────────────┘
""")

# Save as text file for report
os.makedirs("results", exist_ok=True)
with open("results/report_numbers.txt", "w") as f:
    f.write(f"Max AoI Apollo-I  = {max(aoi1):.1f}ms\n")
    f.write(f"Max AoI Apollo-II = {max(aoi2):.1f}ms\n")
    f.write(f"Max AoI OURS      = {max(aoi3):.1f}ms\n")
    f.write(f"Avg AoI Apollo-I  = {np.mean(aoi1):.1f}ms\n")
    f.write(f"Avg AoI Apollo-II = {np.mean(aoi2):.1f}ms\n")
    f.write(f"Avg AoI OURS      = {np.mean(aoi3):.1f}ms\n")
    f.write(f"Throughput Apollo-I  = {tp1:.2f} rps\n")
    f.write(f"Throughput Apollo-II = {tp2:.2f} rps\n")
    f.write(f"Throughput OURS      = {tp3:.2f} rps\n")
    f.write(f"Max AoI gain vs Apollo-I = {g_max:.1f}%\n")
    f.write(f"Avg AoI gain vs Apollo-I = {g_avg:.1f}%\n")

print("  ✓ Numbers saved to results/report_numbers.txt")
print("  ✓ PROJECT COMPLETE — All files ready!")
print("=" * 65)
