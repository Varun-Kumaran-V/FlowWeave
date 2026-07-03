#!/usr/bin/env python3
"""
trace_generator.py
Generate synthetic AllReduce-style DGX traces and bucketed telemetry.

Usage:
  python sim/trace_generator.py --buckets-out traces/example_buckets.json
  python sim/trace_generator.py --events-out traces/example_trace.csv --buckets-out traces/example_buckets.json
  python sim/trace_generator.py --bg-mode onoff --bg_rate_per_ms 10.0 --buckets-out traces/example_buckets.json

If only --buckets-out is given, only the bucketed JSON is written.
If both --events-out and --buckets-out are given, both files are written.
--bg-mode: 'poisson' (default) or 'onoff' (50 ms ON / 50 ms OFF alternating).
"""
import argparse, csv, json, os, random, math
from math import floor

# ---------- Poisson helpers (numpy fast-path, pure-Python fallback) ----------

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _poisson_sample_py(lam, rng):
    """Knuth algorithm for sampling Poisson(lam) using *rng* (random.Random)."""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p < L:
            return k - 1


def _generate_poisson_background(total_duration_ms, bg_rate_per_ms, num_workers,
                                  packet_bytes, rng, np_rng=None):
    """
    True Poisson background traffic: for every millisecond *t* in
    [0, total_duration_ms) draw k ~ Poisson(bg_rate_per_ms) arrivals and
    place each at t + U(0,1).

    Returns a list of (ts_ms, src, dst, bytes) tuples.
    """
    if bg_rate_per_ms <= 0:
        return []

    bg_events = []
    duration = int(math.ceil(total_duration_ms))

    if _HAS_NUMPY and np_rng is not None:
        # Vectorised fast path
        counts = np_rng.poisson(lam=bg_rate_per_ms, size=duration)
        for t, k in enumerate(counts):
            if k == 0:
                continue
            offsets = np_rng.uniform(0.0, 1.0, size=int(k))
            srcs = np_rng.integers(0, num_workers, size=int(k))
            dsts = np_rng.integers(0, num_workers - 1, size=int(k))
            for i in range(int(k)):
                src = int(srcs[i])
                dst = int(dsts[i])
                # avoid src==dst
                if dst >= src:
                    dst += 1
                bg_events.append((t + float(offsets[i]), src, dst, packet_bytes))
    else:
        # Pure-Python fallback
        for t in range(duration):
            k = _poisson_sample_py(bg_rate_per_ms, rng)
            for _ in range(k):
                src = rng.randint(0, num_workers - 1)
                dst = rng.randint(0, num_workers - 2)
                if dst >= src:
                    dst += 1
                ts = t + rng.random()
                bg_events.append((ts, src, dst, packet_bytes))

    return bg_events


def _generate_onoff_background(total_duration_ms, bg_rate_per_ms, num_workers,
                               packet_bytes, rng, np_rng=None,
                               on_duration_ms=50, off_duration_ms=50):
    """
    ON-OFF bursty background traffic.

    Time alternates between ON windows (length *on_duration_ms*) where
    arrivals are Poisson(bg_rate_per_ms) per ms, and OFF windows (length
    *off_duration_ms*) where no background events are generated.

    The ON/OFF cycle starts at t=0.  Returns a list of
    (ts_ms, src, dst, bytes) tuples.
    """
    if bg_rate_per_ms <= 0:
        return []

    period_ms = on_duration_ms + off_duration_ms
    bg_events = []
    duration = int(math.ceil(total_duration_ms))

    if _HAS_NUMPY and np_rng is not None:
        # Build a boolean ON mask for every integer millisecond
        ts_arr = np.arange(duration)
        on_mask = (ts_arr % period_ms) < on_duration_ms
        on_indices = ts_arr[on_mask]
        counts = np_rng.poisson(lam=bg_rate_per_ms, size=len(on_indices))
        for t, k in zip(on_indices.tolist(), counts.tolist()):
            if k == 0:
                continue
            offsets = np_rng.uniform(0.0, 1.0, size=int(k))
            srcs = np_rng.integers(0, num_workers, size=int(k))
            dsts = np_rng.integers(0, num_workers - 1, size=int(k))
            for i in range(int(k)):
                src = int(srcs[i])
                dst = int(dsts[i])
                if dst >= src:
                    dst += 1
                bg_events.append((t + float(offsets[i]), src, dst, packet_bytes))
    else:
        for t in range(duration):
            if (t % period_ms) >= on_duration_ms:
                continue  # OFF window — skip
            k = _poisson_sample_py(bg_rate_per_ms, rng)
            for _ in range(k):
                src = rng.randint(0, num_workers - 1)
                dst = rng.randint(0, num_workers - 2)
                if dst >= src:
                    dst += 1
                ts = t + rng.random()
                bg_events.append((ts, src, dst, packet_bytes))

    return bg_events

def generate_allreduce_trace(out_csv=None, out_buckets_json=None, num_workers=16, rounds=50,
                             pkts_per_worker=128, packet_bytes=1200,
                             round_period_ms=50, round_jitter_ms=1,
                             start_time_ms=0, report_interval_ms=10, seed=42,
                             bg_rate_per_ms=0.0, bg_mode="poisson",skew_factor=1.0):
    rng = random.Random(seed)
    # Also seed the module-level random for any legacy call-sites
    random.seed(seed)

    # Numpy RNG (if available) seeded deterministically from the same seed
    np_rng = np.random.default_rng(seed) if _HAS_NUMPY else None

    events = []  # (ts_ms, src, dst, bytes)
    # We model a typical ring/allreduce: each worker sends pkts to one or more peers per round
    for r in range(rounds):
        round_center = start_time_ms + r * round_period_ms + rng.uniform(-round_jitter_ms, round_jitter_ms)
        # Each worker will send pkts_per_worker tiny flows, spread micro-jitter within 2ms
        for w in range(num_workers):

            if w == 0:
                worker_pkts = int(pkts_per_worker * skew_factor)
            else:
                worker_pkts = pkts_per_worker

            for p in range(worker_pkts):

                dst = (w + 1) % num_workers
                ts = round_center + rng.uniform(0, 2.0)

                events.append((ts, w, dst, packet_bytes))

    # --- Background traffic (mode-dispatched) ---
    total_duration_ms = start_time_ms + rounds * round_period_ms + round_jitter_ms + 2.0
    if bg_mode == "onoff":
        bg_events = _generate_onoff_background(
            total_duration_ms, bg_rate_per_ms, num_workers, packet_bytes, rng, np_rng
        )
        if bg_events:
            events.extend(bg_events)
            print(f"Added {len(bg_events)} ON-OFF background events "
                  f"(rate={bg_rate_per_ms}/ms, 50ms ON/50ms OFF, "
                  f"over {total_duration_ms:.1f} ms)")
    else:
        bg_events = _generate_poisson_background(
            total_duration_ms, bg_rate_per_ms, num_workers, packet_bytes, rng, np_rng
        )
        if bg_events:
            events.extend(bg_events)
            print(f"Added {len(bg_events)} Poisson background events "
                  f"(rate={bg_rate_per_ms}/ms over {total_duration_ms:.1f} ms)")

    # Sort events by timestamp (AI bursts + background merged)
    events.sort(key=lambda x: x[0])

    # Write CSV (timestamps in ms) -- only if caller requested it
    if out_csv is not None:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline='') as f:
            wcsv = csv.writer(f)
            wcsv.writerow(["time_ms", "src", "dst", "bytes"])
            for ts, src, dst, b in events:
                wcsv.writerow([f"{ts:.3f}", src, dst, b])

    # Bucket into report intervals (arrivals per REPORT_INTERVAL_MS)
    buckets = {}
    for ts, src, dst, b in events:
        bucket = int(floor(ts / report_interval_ms)) * report_interval_ms
        buckets.setdefault(bucket, 0)
        buckets[bucket] += 1

    # write buckets JSON with keys sorted -- only if caller requested it
    sorted_keys = sorted(buckets.keys())
    bucket_list = [{"bucket_start_ms": k, "arrivals": buckets[k]} for k in sorted_keys]
    if out_buckets_json is not None:
        os.makedirs(os.path.dirname(out_buckets_json) or ".", exist_ok=True)
        with open(out_buckets_json, "w") as f:
            json.dump({"report_interval_ms": report_interval_ms, "buckets": bucket_list}, f, indent=2)

    wrote = []
    if out_csv is not None:
        wrote.append(f"{len(events)} events to {out_csv}")
    if out_buckets_json is not None:
        wrote.append(f"{len(bucket_list)} buckets to {out_buckets_json}")
    if wrote:
        print(f"Wrote {'; '.join(wrote)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Generate synthetic AllReduce-style DGX traces."
    )
    p.add_argument("--events-out", default=None,
                    help="Path to write raw events CSV (omit to skip)")
    p.add_argument("--buckets-out", default=None,
                    help="Path to write bucketed arrivals JSON (omit to skip)")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--rounds", type=int, default=50)
    p.add_argument("--pkts", type=int, default=128)
    p.add_argument("--bytes", type=int, default=1200)
    p.add_argument("--round_ms", type=float, default=50.0)
    p.add_argument("--jitter_ms", type=float, default=1.0)
    p.add_argument("--report_interval_ms", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bg_rate_per_ms", type=float, default=0.0,
                    help="Background flow arrival rate per ms "
                         "(e.g. 10.0 = ~10 000 flows/sec)")
    p.add_argument("--bg-mode", choices=["poisson", "onoff"], default="poisson",
                    help="Background traffic mode: 'poisson' (default) or "
                         "'onoff' (50 ms ON / 50 ms OFF alternating)")
    p.add_argument(
        "--skew",
        type=float,
        default=1.0,
        help="traffic multiplier for worker 0"
    )
    args = p.parse_args()
    if args.events_out is None and args.buckets_out is None:
        p.error("at least one of --events-out or --buckets-out is required")
    generate_allreduce_trace(out_csv=args.events_out, out_buckets_json=args.buckets_out,
                             num_workers=args.workers, rounds=args.rounds,
                             pkts_per_worker=args.pkts, packet_bytes=args.bytes,
                             round_period_ms=args.round_ms, round_jitter_ms=args.jitter_ms,
                             report_interval_ms=args.report_interval_ms, seed=args.seed,
                             bg_rate_per_ms=args.bg_rate_per_ms,
                             bg_mode=args.bg_mode, skew_factor=args.skew)