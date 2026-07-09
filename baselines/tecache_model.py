import random

def run_tecache(buckets, params, rng=None):
    if rng is None:
        rng = random.Random(0)
    TCAM_LIMIT = params.get("TCAM_LIMIT", 2000)
    FLOW_LIFETIME_MS = params.get("FLOW_LIFETIME_MS", 50.0)
    REPORT_INTERVAL_MS = params.get("REPORT_INTERVAL_MS", 10)
    heavy_frac = params.get("HEAVY_FRAC", 0.05)

    cache_size = 0.0
    installs = 0.0
    drops = 0.0
    ctrl_msgs = 0.0
    tcam_history = []

    for b in buckets:
        expired = cache_size * (REPORT_INTERVAL_MS / FLOW_LIFETIME_MS)
        cache_size = max(0.0, cache_size - expired)

        arrivals = b["arrivals"]
        heavy = arrivals * heavy_frac
        light = arrivals - heavy

        free = max(0.0, TCAM_LIMIT - cache_size)

        install_heavy = min(heavy, free)
        cache_size += install_heavy
        installs += install_heavy
        ctrl_msgs += install_heavy

        free = max(0.0, TCAM_LIMIT - cache_size)

        install_light = min(light, free)
        cache_size += install_light
        installs += install_light
        ctrl_msgs += install_light

        drops += max(0.0, light - install_light)
        tcam_history.append(cache_size)

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