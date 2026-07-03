
# controller_instrumented.py - instrumented FlowWeave controller loop for evaluation
import json, time, os
SKETCH_FILE = "sketch.json"   # external producer (e.g., switch agent or simulator) updates this with {"density": <flows/sec>}
TABLE_FILE = "table.json"     # controller writes installed rules here (for emulation)
METRICS_FILE = "metrics.json"
REPORT_INTERVAL = 0.01  # seconds (10 ms)
THRESHOLD = 1e4         # derivative threshold (flows/sec^2)
COALESCE_DURATION = 2.2 # seconds
BF_FALSE_NEG_RATE = 0.0001

def read_sketch():
    if not os.path.exists(SKETCH_FILE):
        return 0.0
    try:
        with open(SKETCH_FILE, "r") as f:
            j = json.load(f)
            return float(j.get("density", 0.0))
    except Exception:
        return 0.0

def write_table(rules):
    with open(TABLE_FILE, "w") as f:
        json.dump(rules, f, indent=2)

def read_table():
    if not os.path.exists(TABLE_FILE):
        return []
    with open(TABLE_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def write_metrics(m):
    with open(METRICS_FILE, "w") as f:
        json.dump(m, f, indent=2)

def install_superflow(rules):
    # Add a superflow wildcard rule entry
    rules.append({"id":"superflow","type":"superflow","installed_at":time.time()})
    return rules

def remove_superflow(rules):
    return [r for r in rules if r.get("id") != "superflow"]

def main():
    prev_density = read_sketch()
    prev_time = time.time()
    rules = read_table()
    active = any(r.get("id")=="superflow" for r in rules)
    superflow_expires = 0.0

    # metrics
    metrics = {
        "total_drops": 0,
        "control_messages_sent": 0,
        "tcam_history": [],
        "flow_setup_times": []
    }

    write_table(rules)
    write_metrics(metrics)

    try:
        while True:
            now = time.time()
            density = read_sketch()
            dt = max(1e-9, now - prev_time)
            derivative = (density - prev_density) / dt
            prev_density = density
            prev_time = now

            # decide to install superflow
            if derivative >= THRESHOLD and not active:
                # install one superflow
                rules = read_table()
                rules = install_superflow(rules)
                write_table(rules)
                metrics["control_messages_sent"] += 1
                active = True
                superflow_expires = now + COALESCE_DURATION
            # check expiry
            if active and now >= superflow_expires:
                rules = read_table()
                rules = remove_superflow(rules)
                write_table(rules)
                active = False

            # sample TCAM occupancy as number of rules (simple approximation)
            rules = read_table()
            tcam_occupancy = len(rules)
            metrics["tcam_history"].append({"ts": now, "occupancy": tcam_occupancy})

            # write metrics atomically
            write_metrics(metrics)
            time.sleep(REPORT_INTERVAL)
    except KeyboardInterrupt:
        write_metrics(metrics)
        print("Controller stopped, metrics written to", METRICS_FILE)

if __name__=="__main__":
    main()
