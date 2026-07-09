#!/usr/bin/env python3
"""
targeted_sweep.py
Sweep over (BF_FALSE_NEG_RATE, DERIV_THRESHOLD) pairs with multiple seeds.

Outputs into --out-dir:
  per_seed.csv           – one row per (bf, deriv, seed)
  targeted_summary.csv   – one row per (bf, deriv) with mean + 95 % CI
  metadata.json          – run provenance

Usage:
  python sim/targeted_sweep.py --seeds 10 --bg 5.0 --out-dir sim/results/sweep
  python sim/targeted_sweep.py --bf-list 1e-3,1e-4 --deriv-list 2000,5000,12000
"""

import sys, os, csv, json, itertools

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_targeted_sweep(
    bf_list=None,
    deriv_list=None,
    num_seeds=10,
    bg_rate_per_ms=5.0,
    out_dir="sim/results/targeted_sweep",
):
    if bf_list is None:
        bf_list = [1e-3, 1e-4, 3e-5, 1e-5]
    if deriv_list is None:
        deriv_list = [2000, 5000, 8000, 12000, 20000]

    os.makedirs(out_dir, exist_ok=True)

    # Base simulation parameters (bf and deriv overridden per combo)
    base_params = {
        "TCAM_LIMIT": 10000,
        "FLOW_LIFETIME_MS": 50,
        "REPORT_INTERVAL_MS": 10,
        "HEAVY_FRAC": 0.02,
        "AGG_RATIO": 10,
        "BURST_WIDTH_MULT": 1.5,
    }

    # Temp files for trace generation
    trace_csv = os.path.join(out_dir, "_tmp_trace.csv")
    buckets_json = os.path.join(out_dir, "_tmp_buckets.json")

    seeds = list(range(1, num_seeds + 1))
    per_seed_rows = []
    summary_rows = []

    combos = list(itertools.product(bf_list, deriv_list))

    print(f"{'='*64}")
    print(f"  Targeted sweep: {len(combos)} combos x {num_seeds} seeds, bg={bg_rate_per_ms}/ms")
    print(f"  out_dir: {out_dir}")
    print(f"{'='*64}")

    for bf, deriv in combos:
        sim_params = {
            **base_params,
            "BF_FALSE_NEG_RATE": bf,
            "DERIV_THRESHOLD": deriv,
        }

        seed_reductions = []
        seed_drop_reductions = []
        seed_tcam_peaks = []
        seed_drop_rates = []

        for seed in seeds:
            rng = create_rng(seed)

            # 1. Generate trace
            generate_allreduce_trace(
                out_csv=trace_csv,
                out_buckets_json=buckets_json,
                seed=seed,
                bg_rate_per_ms=bg_rate_per_ms,
            )

            # 2. Load buckets
            with open(buckets_json) as f:
                buckets = json.load(f)["buckets"]

            # 3. Run baseline + FlowWeave with same rng per seed
            bl = run_exact(buckets, sim_params, rng=create_rng(seed))
            fw = run_flowweave(buckets, sim_params, rng=create_rng(seed))

            # 4. Paired reductions
            ctrl_reduction = bl["ctrl_msgs"] / max(1.0, fw["ctrl_msgs"])
            drop_reduction = (bl["drops"] / max(1.0, fw["drops"])
                              if fw["drops"] > 0 else float("inf"))

            per_seed_rows.append({
                "bf": bf,
                "deriv": deriv,
                "seed": seed,
                "bl_ctrl": bl["ctrl_msgs"],
                "fw_ctrl": fw["ctrl_msgs"],
                "reduction": ctrl_reduction,
                "bl_tcam_peak": bl["tcam_peak"],
                "fw_tcam_peak": fw["tcam_peak"],
                "bl_drops": bl["drops"],
                "fw_drops": fw["drops"],
            })

            seed_reductions.append(ctrl_reduction)
            seed_drop_reductions.append(fw["drop_rate_pct"])
            seed_tcam_peaks.append(fw["tcam_peak"])
            seed_drop_rates.append(fw["drop_rate_pct"])

        # Aggregate for this (bf, deriv) combo
        summary_rows.append({
            "bf": bf,
            "deriv": deriv,
            "tcam_peak_mean": _mean(seed_tcam_peaks),
            "tcam_peak_ci95": ci95(seed_tcam_peaks),
            "ctrl_reduction_mean": _mean(seed_reductions),
            "ctrl_reduction_ci95": ci95(seed_reductions),
            "drop_rate_mean": _mean(seed_drop_rates),
            "drop_rate_ci95": ci95(seed_drop_rates),
        })

        print(f"  bf={bf:.1e}  deriv={deriv:6d}  |  "
              f"tcam_peak={_mean(seed_tcam_peaks):.0f}  "
              f"ctrl_red={_mean(seed_reductions):.1f}x  "
              f"drop_rate={_mean(seed_drop_rates):.3f}%")

    # ------------------------------------------------------------------
    # Write per_seed.csv
    # ------------------------------------------------------------------
    per_seed_path = os.path.join(out_dir, "per_seed.csv")
    ps_fields = [
        "bf", "deriv", "seed",
        "bl_ctrl", "fw_ctrl", "reduction",
        "bl_tcam_peak", "fw_tcam_peak",
        "bl_drops", "fw_drops",
    ]
    with open(per_seed_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ps_fields)
        writer.writeheader()
        writer.writerows(per_seed_rows)

    # ------------------------------------------------------------------
    # Write targeted_summary.csv
    # ------------------------------------------------------------------
    summary_path = os.path.join(out_dir, "targeted_summary.csv")
    sum_fields = [
        "bf", "deriv",
        "tcam_peak_mean", "tcam_peak_ci95",
        "ctrl_reduction_mean", "ctrl_reduction_ci95",
        "drop_rate_mean", "drop_rate_ci95",
    ]
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sum_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    # ------------------------------------------------------------------
    # Write metadata.json
    # ------------------------------------------------------------------
    write_metadata(
        out_dir,
        params={
            **base_params,
            "bf_list": bf_list,
            "deriv_list": deriv_list,
            "bg_rate_per_ms": bg_rate_per_ms,
        },
        seeds=seeds,
    )

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------
    print(f"\n{'='*64}")
    print(f"  RESULTS  ({len(combos)} combos x {num_seeds} seeds)")
    print(f"{'='*64}")
    print(f"  {per_seed_path}")
    print(f"  {summary_path}")
    print(f"  {os.path.join(out_dir, 'metadata.json')}")
    print(f"{'='*64}\n")

    # Clean up temp files
    for tmp in (trace_csv, buckets_json):
        if os.path.exists(tmp):
            os.remove(tmp)

    return summary_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_float_list(s):
    return [float(x.strip()) for x in s.split(",")]


def _parse_int_list(s):
    return [int(x.strip()) for x in s.split(",")]


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Targeted BF/DERIV_THRESHOLD parameter sweep")
    p.add_argument("--bf-list", type=_parse_float_list,
                   default=None,
                   help="Comma-separated BF_FALSE_NEG_RATE values "
                        "(default: 1e-3,1e-4,3e-5,1e-5)")
    p.add_argument("--deriv-list", type=_parse_int_list,
                   default=None,
                   help="Comma-separated DERIV_THRESHOLD values "
                        "(default: 2000,5000,8000,12000,20000)")
    p.add_argument("--seeds", type=int, default=10,
                   help="Number of seeds per combo (default: 10)")
    p.add_argument("--bg", type=float, default=5.0,
                   help="Poisson background rate per ms (default: 5.0)")
    p.add_argument("--out-dir", default="sim/results/targeted_sweep",
                   help="Output directory (default: sim/results/targeted_sweep)")
    args = p.parse_args()

    run_targeted_sweep(
        bf_list=args.bf_list,
        deriv_list=args.deriv_list,
        num_seeds=args.seeds,
        bg_rate_per_ms=args.bg,
        out_dir=args.out_dir,
    )