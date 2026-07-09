import sys
import json
import csv
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from baselines.exact_match_lru import run_exact
from baselines.tecache_model import run_tecache
from baselines.agft_model import run_agft
from models.flowweave_model import run_flowweave

def load_buckets(path):
    data = json.load(open(path))
    return data["buckets"]

def main(buckets_path, out_csv):
    buckets = load_buckets(buckets_path)

    params = {
        "TCAM_LIMIT": 2000,
        "FLOW_LIFETIME_MS": 50,
        "REPORT_INTERVAL_MS": 10,
        "HEAVY_FRAC": 0.02,
        "AGG_RATIO": 10,
        "DERIV_THRESHOLD": 10000,
        "COALESCE_DURATION_MS": 2000,
        "BF_FALSE_NEG_RATE": 1e-4
    }

    results = {
        "exact": run_exact(buckets, params),
        "tecache": run_tecache(buckets, params),
        "agft": run_agft(buckets, params),
        "flowweave": run_flowweave(buckets, params)
    }

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["method","tcam_peak","avg_tcam","drops","installs","ctrl_msgs","p99_setup_s","drop_rate_pct"])
        for k,v in results.items():
            writer.writerow([k,v["tcam_peak"],v["avg_tcam"],v["drops"],v["installs"],v["ctrl_msgs"],v["p99_setup_s"],v["drop_rate_pct"]])

    for k,v in results.items():
        print("===",k,"===")
        for m,val in v.items():
            print(m,":",val)

if __name__ == "__main__":
    buckets = sys.argv[1]
    out = sys.argv[2]
    main(buckets,out)