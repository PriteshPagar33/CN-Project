"""
=================================================================
AoI Project — STEP 1: Setup Verification
Run this FIRST.   Command: python3 step1_setup_check.py
=================================================================
Paper : AoI-centric Task Scheduling for Autonomous Driving
Authors: Chengyuan Xu, Qian Xu, Jianping Wang, Kui Wu et al.
Venue : City University of Hong Kong (QS #62)
=================================================================
"""
import sys, os

print("=" * 60)
print("  AoI Project — Setup Check")
print("=" * 60)

v = sys.version_info
print(f"\n[1] Python {v.major}.{v.minor}  ", end="")
print("✓" if v.major == 3 and v.minor >= 8 else "✗ Need 3.8+")

for lib in ["numpy", "matplotlib", "pandas"]:
    try:
        __import__(lib); print(f"[2] {lib:<15} ✓")
    except ImportError:
        print(f"[2] {lib:<15} ✗  →  pip install {lib}")

os.makedirs("graphs",  exist_ok=True)
os.makedirs("results", exist_ok=True)
print("\n[3] Folders created: graphs/  results/")
print("\n✓ All good — run:  python3 step2_apollo_model.py")
print("=" * 60)
