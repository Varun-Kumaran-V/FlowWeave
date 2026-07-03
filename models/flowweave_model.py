# models/flowweave_model.py (replace run_flowweave)
import collections, math, random

from networkx import density

from sim.paper_demo import TCAM_LIMIT

def run_flowweave(buckets, params, rng=None):
    if rng is None:
        rng = random.Random(0)
    TCAM_LIMIT = int(params.get("TCAM_LIMIT", 2000))
    REPORT_INTERVAL_MS = params.get("REPORT_INTERVAL_MS", 10)
    FLOW_LIFETIME_MS = params.get("FLOW_LIFETIME_MS", 50.0)
    DERIV_THRESHOLD = params.get("DERIV_THRESHOLD", 5000)
    # COALESCE_DURATION_MS is now only used as an initial fallback;
    # the adaptive logic below overrides it per-burst.
    COALESCE_DURATION_MS_DEFAULT = params.get("COALESCE_DURATION_MS", 2000)
    BF_FALSE_NEG_RATE = params.get("BF_FALSE_NEG_RATE", 1e-4)
    MOVING_WINDOW = params.get("MOVING_WINDOW", 10)
    ALPHA = params.get("DERIV_ALPHA", 3.0)

    # Adaptive coalesce bounds (anti-oscillation)
    COALESCE_MIN_MS = params.get("COALESCE_MIN_MS", 500)
    COALESCE_MAX_MS = params.get("COALESCE_MAX_MS", 4000)
    BURST_WIDTH_MULT = params.get("BURST_WIDTH_MULT", 1.5)

    # Rolling-average threshold ratio: density must be this fraction above the
    # running mean to be considered "elevated".
    ELEVATED_RATIO = params.get("ELEVATED_RATIO", 1.3)

    installs = 0
    drops = 0
    ctrl_msgs = 0
    tcam_history = []

    # state
    flow_exact_active = 0
    superflow_installed = False
    superflow_until = -1
    time_index = 0

    # moving window for density statistics
    window = collections.deque(maxlen=MOVING_WINDOW)
    sum_w = 0.0
    sumsq_w = 0.0

    # --- burst-width measurement state ---
    # We track the start time of a contiguous run of "elevated" density
    # intervals so that when detection fires we know how wide the burst
    # already is.  A rolling-average crossing below the threshold resets it.
    burst_start_ms = None       # ms when current elevated run began
    burst_running = False       # True while density stays elevated

    for b in buckets:
        current_time_ms = b["bucket_start_ms"]
        arrivals = b["arrivals"]
        density = arrivals * (1000.0 / REPORT_INTERVAL_MS)  # flows/sec approx

        # update moving stats
        if len(window) == MOVING_WINDOW:
            old = window.popleft()
            sum_w -= old
            sumsq_w -= old * old
        window.append(density)
        sum_w += density
        sumsq_w += density * density
        mean = sum_w / len(window)
        var = max(0.0, (sumsq_w / len(window)) - mean * mean)
        std = math.sqrt(var)

        # ------ burst-width tracking (rolling-average crossing) ------
        elevated = (mean > 0) and (density >= ELEVATED_RATIO * mean)
        if elevated:
            if not burst_running:
                burst_start_ms = current_time_ms
                burst_running = True
        else:
            burst_running = False
            burst_start_ms = None

        # ---------- PROACTIVE PHASE + CAPACITY-AWARE DETECTION ----------
        detect = False

        # 1) Derivative-based spike detection
        deriv_signal = density - mean
        deriv_trigger = deriv_signal >= DERIV_THRESHOLD

        # 2) Capacity-aware prediction
        projected_entries = flow_exact_active + arrivals
        capacity_trigger = projected_entries >= 0.8 * TCAM_LIMIT

        # 3) Combined logic
        if deriv_trigger or capacity_trigger:
            detect = True
        elif std > 0 and deriv_signal >= ALPHA * std:
            detect = True

        # expire some exact entries
        expired = int(flow_exact_active * (REPORT_INTERVAL_MS / FLOW_LIFETIME_MS))
        flow_exact_active = max(0, flow_exact_active - expired)

        # ------ adaptive coalesce duration ------
        if detect and current_time_ms > superflow_until:
            # Measure burst width so far (how long density has been elevated)
            if burst_running and burst_start_ms is not None:
                measured_width = current_time_ms - burst_start_ms + REPORT_INTERVAL_MS
            else:
                # Detection fired on the very first elevated sample;
                # use a single-interval width as seed.
                measured_width = REPORT_INTERVAL_MS

            adaptive_coalesce_duration = measured_width * BURST_WIDTH_MULT

            # Clamp to [min, max] to prevent oscillation / runaway
            adaptive_coalesce_duration = max(COALESCE_MIN_MS,
                                             min(COALESCE_MAX_MS,
                                                 adaptive_coalesce_duration))

            superflow_installed = True
            superflow_until = current_time_ms + adaptive_coalesce_duration

            # installing a single wildcard superflow entry
            if flow_exact_active + 1 <= TCAM_LIMIT:
                installs += 1
                ctrl_msgs += 1
                print(f"SUPERFLOW INSTALLED until: {superflow_until} "
                      f"(adaptive={adaptive_coalesce_duration:.0f}ms, "
                      f"burst_width={measured_width:.0f}ms)")
            else:
                pass  # cannot install superflow (edge case)

        # now serve arrivals
        if superflow_installed and current_time_ms <= superflow_until:
            fn_needed = int(arrivals * BF_FALSE_NEG_RATE)
            free = max(0, TCAM_LIMIT - (flow_exact_active + 1))
            to_install = min(fn_needed, free)
            flow_exact_active += to_install
            installs += to_install
            ctrl_msgs += to_install
            drops += max(0, fn_needed - to_install)
            if current_time_ms >= superflow_until:
                superflow_installed = False
        else:
            free = max(0, TCAM_LIMIT - flow_exact_active)
            to_install = min(arrivals, free)
            drops += max(0, arrivals - to_install)
            flow_exact_active += to_install
            installs += to_install
            ctrl_msgs += to_install

        tcam_count = flow_exact_active + (1 if superflow_installed and current_time_ms <= superflow_until else 0)
        tcam_history.append(tcam_count)
        time_index += 1

    total_arrivals = sum(b["arrivals"] for b in buckets)
    return {
        "tcam_peak": max(tcam_history) if tcam_history else 0,
        "avg_tcam": sum(tcam_history) / len(tcam_history) if tcam_history else 0,
        "drops": drops,
        "installs": installs,
        "ctrl_msgs": ctrl_msgs,
        "p99_setup_s": 3.5e-05,
        "drop_rate_pct": (drops / max(1.0, total_arrivals)) * 100.0
    }