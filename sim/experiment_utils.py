# sim/experiment_utils.py
import os
import json
import sys
import platform
import subprocess
import time
import random
import math

try:
    import numpy as _np
except Exception:
    _np = None

def create_rng(seed: int):
    """Return a deterministic RNG object for use in simulations."""
    return random.Random(seed)

def try_get_git_sha():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return sha.decode().strip()
    except Exception:
        return None

def write_metadata(out_dir: str, params: dict, seeds: list):
    """Write metadata.json in out_dir with environment + run parameters."""
    meta = {
        "git_sha": try_get_git_sha(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "params": params,
        "seeds": seeds,
    }
    if _np is not None:
        meta["numpy_version"] = _np.__version__
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

def ci95(vals):
    """Return 95% CI half-width for sample vals (list or numpy array)."""
    n = len(vals)
    if n < 2:
        return 0.0
    # compute sample std
    try:
        import numpy as np
        arr = np.array(vals, dtype=float)
        s = arr.std(ddof=1)
    except Exception:
        # fallback pure-python
        mean = sum(vals) / n
        s = math.sqrt(sum((x-mean)**2 for x in vals) / (n-1))
    try:
        from scipy.stats import t as student_t
        tcrit = student_t.ppf(0.975, df=n-1)
    except Exception:
        # fallback to normal z
        tcrit = 1.959963984540054
    return tcrit * s / math.sqrt(n)