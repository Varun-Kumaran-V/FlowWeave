import random

def run_exact(buckets, params, rng=None):
    if rng is None:
        rng = random.Random(0)
    TCAM_LIMIT = params.get("TCAM_LIMIT", 2000)
    FLOW_LIFETIME_MS = params.get("FLOW_LIFETIME_MS", 50.0)
    REPORT_INTERVAL_MS = params.get("REPORT_INTERVAL_MS", 10)

    active = 0.0
    installs = 0.0
    drops = 0.0
    ctrl_msgs = 0.0
    tcam_history = []
    setup_samples = 0

    for b in buckets:
        dt = REPORT_INTERVAL_MS
        expired = active * (dt / FLOW_LIFETIME_MS)
        active = max(0.0, active - expired)

        arrivals = b["arrivals"]
        free = max(0.0, TCAM_LIMIT - active)
        to_install = min(arrivals, free)
        dropped = max(0.0, arrivals - to_install)

        active += to_install
        installs += to_install
        drops += dropped
        ctrl_msgs += to_install
        setup_samples += int(max(1, to_install))
        tcam_history.append(active)

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