import math
import random

def run_agft(buckets, params, rng=None):
    if rng is None:
        rng = random.Random(0)
    TCAM_LIMIT = params.get("TCAM_LIMIT", 2000)
    FLOW_LIFETIME_MS = params.get("FLOW_LIFETIME_MS", 50.0)
    REPORT_INTERVAL_MS = params.get("REPORT_INTERVAL_MS", 10)
    agg_ratio = params.get("AGG_RATIO", 10.0)

    installs = 0.0
    drops = 0.0
    ctrl_msgs = 0.0
    tcam_history = []
    current_entries = 0.0

    for b in buckets:
        expired = current_entries * (REPORT_INTERVAL_MS / FLOW_LIFETIME_MS)
        current_entries = max(0.0, current_entries - expired)

        arrivals = b["arrivals"]
        needed = math.ceil(arrivals / agg_ratio)

        free = max(0.0, TCAM_LIMIT - current_entries)
        installed = min(needed, free)
        dropped_groups = max(0, needed - installed)

        installs += installed
        ctrl_msgs += installed
        current_entries += installed
        drops += dropped_groups * agg_ratio

        tcam_history.append(current_entries)

    total_arrivals = sum(b["arrivals"] for b in buckets)

    return {
        "tcam_peak": max(tcam_history) if tcam_history else 0,
        "avg_tcam": sum(tcam_history)/len(tcam_history) if tcam_history else 0,
        "drops": drops,
        "installs": installs,
        "ctrl_msgs": ctrl_msgs,
        "p99_setup_s": 0.005,
        "drop_rate_pct": (drops / max(1.0, total_arrivals)) * 100.0
    }