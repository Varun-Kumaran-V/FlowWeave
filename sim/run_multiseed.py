#!/usr/bin/env python3
"""
run_multiseed.py
Run head-to-head evaluation across multiple seeds with Poisson background
traffic.  Writes three artefacts into --out-dir:

  per_seed.csv   – one row per seed with baseline & FlowWeave metrics + paired
                   reduction ratios
  summary.csv    – aggregate mean / std / 95 % CI for each metric
  metadata.json  – git sha, python version, params, seeds, timestamp

Usage:
  python sim/run_multiseed.py --seeds 5 --bg 5.0 --out-dir sim/results/my_run
"""

import sys, os, csv, math, json

# Ensure the project root is importable regardless of cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sim.trace_generator import generate_allreduce_trace
from sim.experiment_utils import ci95, create_rng, write_metadata
from models.flowweave_model import run_flowweave
from baselines.exact_match_lru import run_exact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals, mu=None):
    if len(vals) < 2:
        return 0.0
    if mu is None:
        mu = _mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_multiseed(num_seeds=20, bg_rate_per_ms=5.0,
                  out_dir="sim/results/multiseed",
                  bg_mode="poisson"
                  ,skew=1.0):
    """Generate traces and evaluate FlowWeave for *num_seeds* seeds."""

    # Shared simulation parameters (same as run_head_to_head / paper_demo)
    sim_params = {
        "TCAM_LIMIT": 2000,
        "FLOW_LIFETIME_MS": 50,
        "REPORT_INTERVAL_MS": 10,
        "HEAVY_FRAC": 0.02,
        "AGG_RATIO": 10,
        "DERIV_THRESHOLD": 10000,
        "COALESCE_DURATION_MS": 2000,
        "BF_FALSE_NEG_RATE": 1e-4,
    }

    os.makedirs(out_dir, exist_ok=True)

    # Temp files for trace generation (cleaned up at the end)
    trace_csv = os.path.join(out_dir, "_tmp_trace.csv")
    buckets_json = os.path.join(out_dir, "_tmp_buckets.json")

    # Metric names we are tracking
    metric_keys = [
        "tcam_peak", "avg_tcam", "drops", "installs",
        "ctrl_msgs", "p99_setup_s", "drop_rate_pct",
    ]

    # Collect per-seed results
    all_fw = {k: [] for k in metric_keys}
    all_bl = {k: [] for k in metric_keys}
    per_seed_rows = []

    seeds = list(range(1, num_seeds + 1))

    print(f"{'='*64}")
    print(f"  Multi-seed evaluation: {num_seeds} seeds, bg_rate={bg_rate_per_ms}/ms")
    print(f"  out_dir: {out_dir}")
    print(f"{'='*64}")

    for seed in seeds:
        rng = create_rng(seed)

        # 1. Regenerate trace with Poisson background traffic
        generate_allreduce_trace(
        out_csv=trace_csv,
        out_buckets_json=buckets_json,
        seed=seed,
        bg_rate_per_ms=bg_rate_per_ms,
        bg_mode=bg_mode,
        skew_factor=skew,
        )

        # 2. Load buckets
        with open(buckets_json) as f:
            buckets = json.load(f)["buckets"]

        # 3. Run baseline + FlowWeave (pass rng for determinism)
        bl = run_exact(buckets, sim_params, rng=create_rng(seed))
        fw = run_flowweave(buckets, sim_params, rng=create_rng(seed))

        # 4. Stash metrics
        for k in metric_keys:
            all_fw[k].append(fw[k])
            all_bl[k].append(bl[k])

        # Paired reduction ratios
        ctrl_reduction = bl["ctrl_msgs"] / max(1.0, fw["ctrl_msgs"])
        drop_reduction = bl["drops"] / max(1.0, fw["drops"]) if fw["drops"] > 0 else float("inf")

        row = {"seed": seed}
        for k in metric_keys:
            row[f"bl_{k}"] = bl[k]
            row[f"fw_{k}"] = fw[k]
        row["ctrl_msg_reduction"] = ctrl_reduction
        row["drop_reduction"] = drop_reduction
        per_seed_rows.append(row)

        print(f"  seed {seed:3d}  |  FW drops={fw['drops']:.0f}  "
              f"tcam_peak={fw['tcam_peak']:.0f}  "
              f"ctrl_msgs={fw['ctrl_msgs']:.0f}  "
              f"reduction={ctrl_reduction:.1f}x")

    # ------------------------------------------------------------------
    # Write per_seed.csv  (NO summary rows appended)
    # ------------------------------------------------------------------
    per_seed_path = os.path.join(out_dir, "per_seed.csv")
    per_seed_header = (
        ["seed"]
        + [f"bl_{k}" for k in metric_keys]
        + [f"fw_{k}" for k in metric_keys]
        + ["ctrl_msg_reduction", "drop_reduction"]
    )
    with open(per_seed_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=per_seed_header)
        writer.writeheader()
        writer.writerows(per_seed_rows)

    # ------------------------------------------------------------------
    # Aggregate statistics  (using experiment_utils.ci95)
    # ------------------------------------------------------------------
    summary_rows = []
    for k in metric_keys:
        mu = _mean(all_fw[k])
        sd = _std(all_fw[k], mu)
        ci = ci95(all_fw[k])
        summary_rows.append({
            "metric": f"fw_{k}", "mean": mu, "std": sd, "ci95_half": ci,
        })

    # Paired ctrl-message reduction
    reductions = [r["ctrl_msg_reduction"] for r in per_seed_rows]
    summary_rows.append({
        "metric": "ctrl_msg_reduction",
        "mean": _mean(reductions),
        "std": _std(reductions),
        "ci95_half": ci95(reductions),
    })

    # Paired drop reduction (exclude inf seeds for stats)
    drop_reds = [r["drop_reduction"] for r in per_seed_rows
                 if r["drop_reduction"] != float("inf")]
    if drop_reds:
        summary_rows.append({
            "metric": "drop_reduction",
            "mean": _mean(drop_reds),
            "std": _std(drop_reds),
            "ci95_half": ci95(drop_reds),
        })

    # ------------------------------------------------------------------
    # Write summary.csv
    # ------------------------------------------------------------------
    summary_path = os.path.join(out_dir, "summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "mean", "std", "ci95_half"])
        writer.writeheader()
        writer.writerows(summary_rows)

    # ------------------------------------------------------------------
    # Write metadata.json  (via experiment_utils)
    # ------------------------------------------------------------------
    write_metadata(out_dir, params={**sim_params, "bg_rate_per_ms": bg_rate_per_ms},
                   seeds=seeds)

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------
    print(f"\n{'='*64}")
    print(f"  RESULTS  ({num_seeds} seeds, bg_rate={bg_rate_per_ms}/ms)")
    print(f"{'='*64}")
    print(f"  {per_seed_path}")
    print(f"  {summary_path}")
    print(f"  {os.path.join(out_dir, 'metadata.json')}")
    print(f"{'='*64}\n")

    # Clean up temp trace files
    for tmp in (trace_csv, buckets_json):
        if os.path.exists(tmp):
            os.remove(tmp)

    return summary_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Multi-seed FlowWeave evaluation")
    p.add_argument("--seeds", type=int, default=20,
                   help="Number of seeds to run (default: 20)")
    p.add_argument("--bg", type=float, default=5.0,
                   help="Poisson background rate per ms (default: 5.0)")
    p.add_argument("--out-dir", default="sim/results/multiseed",
                   help="Output directory (default: sim/results/multiseed)")
    p.add_argument(
    "--bg-mode",
    default="poisson",
    choices=["poisson", "onoff"]
    )
    p.add_argument(
    "--skew",
        type=float,
        default=1.0,
        help="traffic multiplier for worker 0"
    )
    args = p.parse_args()
    run_multiseed(
        num_seeds=args.seeds,
        bg_rate_per_ms=args.bg,
        out_dir=args.out_dir,
        bg_mode=args.bg_mode,
        skew=args.skew
    )