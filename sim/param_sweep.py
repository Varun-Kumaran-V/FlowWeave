# sim/param_sweep.py
import sys
import os

# Add project root to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

import json
import csv
import itertools
import math
from pathlib import Path
import matplotlib.pyplot as plt

# load the bucketed trace
buckets = json.load(open("sim/traces/example_buckets.json"))["buckets"]

# helper to import the flowweave runner (uses your local models/ file)
from models.flowweave_model import run_flowweave

# parameter grids
bf_vals = [1e-3, 1e-4, 1e-5]                 # BF false-positive proxies
deriv_vals = [2000, 5000, 10000, 20000]      # derivative thresholds
coalesce_vals = [500, 1000, 2000, 4000]      # coalesce durations (ms)

outdir = Path("sim/results")
outdir.mkdir(parents=True, exist_ok=True)
rows = []

for bf, deriv, coal in itertools.product(bf_vals, deriv_vals, coalesce_vals):
    params = {
        "TCAM_LIMIT": 2000,
        "FLOW_LIFETIME_MS": 50.0,
        "REPORT_INTERVAL_MS": 10,
        "DERIV_THRESHOLD": deriv,
        "COALESCE_DURATION_MS": coal,
        "BF_FALSE_NEG_RATE": bf,
        "INIT_DENSITY": 1000.0
    }
    r = run_flowweave(buckets, params)
    row = {
        "bf": bf, "deriv": deriv, "coalesce": coal,
        "tcam_peak": r["tcam_peak"], "ctrl_msgs": r["ctrl_msgs"], "drop_rate_pct": r["drop_rate_pct"]
    }
    rows.append(row)

# write CSV
csvp = outdir / "flowweave_param_grid.csv"
with open(csvp, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# simple plots: for each bf, plot tcam_peak vs deriv for each coalesce (lines)
import matplotlib.pyplot as plt
from collections import defaultdict
for metric in ["tcam_peak", "ctrl_msgs", "drop_rate_pct"]:
    plt.figure(figsize=(8,5))
    for bf in sorted(set(r["bf"] for r in rows)):
        grouped = defaultdict(list)
        for r in [x for x in rows if x["bf"]==bf]:
            grouped[r["coalesce"]].append((r["deriv"], r[metric]))
        for coal, vals in sorted(grouped.items()):
            vals.sort()
            xs = [v[0] for v in vals]; ys = [v[1] for v in vals]
            plt.plot(xs, ys, marker='o', label=f"bf={bf},coal={coal}ms")
    plt.xlabel("derivative threshold")
    plt.ylabel(metric)
    plt.title(f"FlowWeave sweep: {metric}")
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    plt.savefig(outdir / f"sweep_{metric}.png")
    plt.close()

print("Wrote", csvp, "and plots to", outdir)