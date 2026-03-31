"""
=================================================================
AoI Project — RUN ALL (Single Command)
Command: python3 run_all.py
=================================================================
Runs all 5 steps in sequence automatically.
=================================================================
"""
import subprocess, sys, time

steps = [
    ("step1_setup_check.py",  "Setup verification"),
    ("step2_apollo_model.py", "Apollo DAG model"),
    ("step3_schedulers.py",   "Run all 3 schedulers"),
    ("step4_graphs.py",       "Generate 6 graphs"),
    ("step5_report_numbers.py","Report numbers"),
]

print("=" * 65)
print("  AoI Project — Running Complete Pipeline")
print("=" * 65)

for script, desc in steps:
    print(f"\n{'─'*65}")
    print(f"  ▶  {desc}  ({script})")
    print(f"{'─'*65}")
    t0 = time.time()
    result = subprocess.run([sys.executable, script],
                            capture_output=False)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n  ✗ FAILED: {script}")
        sys.exit(1)
    print(f"  ✓ Done in {elapsed:.1f}s")

print("\n" + "=" * 65)
print("  ✓ ALL STEPS COMPLETE")
print("=" * 65)
print("""
  FILES GENERATED:
  ├── results/
  │   ├── apollo_model.json         ← Apollo DAG model
  │   ├── scheduler_results.json    ← All simulation data
  │   └── report_numbers.txt        ← Numbers for report
  └── graphs/
      ├── graph1_max_aoi_bar.png    ← Max AoI comparison
      ├── graph2_aoi_per_round.png  ← AoI over time
      ├── graph3_aoi_cdf.png        ← CDF comparison
      ├── graph4_throughput.png     ← Throughput
      ├── graph5_improvement_breakdown.png
      └── graph6_headtohead.png     ← Head-to-head
""")
