#!/usr/bin/env python3
"""
controller_flowweave.py
FlowWeave control-plane loop with Bloom-filter tracking, superflow
install/remove, and automatic coalesce expiry.

Usage:
  python sim/controller_flowweave.py
  python sim/controller_flowweave.py --coalesce-ms 2000 --m-bits 2000000 --k-hashes 15
"""

import argparse
import hashlib
import json
import os
import struct
import threading
import time

# ---------------------------------------------------------------------------
# File-based "switch" interface (same convention as controller.py)
# ---------------------------------------------------------------------------

SKETCH_FILE = "sketch.json"
TABLE_FILE = "table.json"


def _read_sketch():
    """Read density snapshot written by the switch emulator / simulator."""
    if not os.path.exists(SKETCH_FILE):
        return 0.0
    try:
        with open(SKETCH_FILE, "r") as f:
            j = json.load(f)
            return float(j.get("density", 0.0))
    except Exception:
        return 0.0


def _read_digest():
    """Read a list of sampled flow IDs from the sketch file (if present)."""
    if not os.path.exists(SKETCH_FILE):
        return []
    try:
        with open(SKETCH_FILE, "r") as f:
            j = json.load(f)
            return j.get("flow_ids", [])
    except Exception:
        return []


def _write_table(rules):
    with open(TABLE_FILE, "w") as f:
        json.dump(rules, f, indent=2)


def _read_table():
    if not os.path.exists(TABLE_FILE):
        return []
    try:
        with open(TABLE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Bloom filter (pure-Python, double-hashing scheme)
# ---------------------------------------------------------------------------

class BloomFilter:
    """Simple Bloom filter using double hashing via SHA-256."""

    def __init__(self, m_bits: int = 1_568_962, k_hashes: int = 13):
        self.m = m_bits
        self.k = k_hashes
        self._bits = bytearray(m_bits)
        self._count = 0          # number of insertions (not unique count)

    # -- hashing (no external dependency) ----------------------------------

    @staticmethod
    def _hash_pair(key: str) -> tuple:
        """Return two independent 64-bit hashes from SHA-256."""
        digest = hashlib.sha256(key.encode()).digest()
        h1 = struct.unpack_from("<Q", digest, 0)[0]
        h2 = struct.unpack_from("<Q", digest, 8)[0]
        return h1, h2

    def add(self, key):
        """Insert *key* (string) into the filter."""
        h1, h2 = self._hash_pair(str(key))
        for i in range(self.k):
            idx = (h1 + i * h2) % self.m
            self._bits[idx] = 1
        self._count += 1

    def union(self, other: "BloomFilter"):
        """Bitwise OR another BloomFilter into *self* (must have same m)."""
        assert self.m == other.m
        for i in range(self.m):
            self._bits[i] |= other._bits[i]
        self._count += other._count

    def density(self) -> float:
        """Fraction of bits set."""
        return sum(self._bits) / self.m if self.m else 0.0

    def clear(self):
        self._bits = bytearray(self.m)
        self._count = 0

    @property
    def insertions(self):
        return self._count


# ---------------------------------------------------------------------------
# Superflow install / remove
# ---------------------------------------------------------------------------

def install_superflow():
    """Write a wildcard entry into superflow_table and set register."""
    rules = _read_table()
    if any(r.get("id") == "superflow" for r in rules):
        return  # already installed

    rules.append({
        "id": "superflow",
        "table": "superflow_table",
        "type": "wildcard",
        "match": "0.0.0.0/0",
        "action": "set_superflow",
        "register": {"name": "superflow_active", "index": 0, "value": 1},
        "installed_at": time.time(),
    })
    _write_table(rules)
    print("[FLOWWEAVE] superflow installed")


def remove_superflow():
    """Delete the wildcard entry and clear the register."""
    rules = _read_table()
    rules = [r for r in rules if r.get("id") != "superflow"]
    _write_table(rules)
    print("[FLOWWEAVE] superflow removed")


# ---------------------------------------------------------------------------
# Controller main loop
# ---------------------------------------------------------------------------

DETECT_THRESHOLD_DENSITY = 0.50   # bloom density that triggers detection
REPORT_INTERVAL_S = 0.010         # 10 ms polling

# Derivative-based spike detection (flows/sec²)
DERIV_THRESHOLD = 1e4


def controller_loop(coalesce_ms: int, m_bits: int, k_hashes: int):
    """Run the FlowWeave control loop until interrupted."""

    bloom = BloomFilter(m_bits=m_bits, k_hashes=k_hashes)
    superflow_active = False
    superflow_expires = 0.0
    prev_density = 0.0
    prev_time = time.time()

    coalesce_s = coalesce_ms / 1000.0

    print(f"[FLOWWEAVE] controller started  "
          f"(coalesce={coalesce_ms}ms, m={m_bits}, k={k_hashes})")

    try:
        while True:
            now = time.time()

            # ---- 1. Ingest digest / packet notification -----------------
            flow_ids = _read_digest()
            for fid in flow_ids:
                bloom.add(fid)

            sketch_density = _read_sketch()

            # ---- 2. Detection logic -------------------------------------
            dt = max(1e-9, now - prev_time)
            derivative = (sketch_density - prev_density) / dt
            prev_density = sketch_density
            prev_time = now

            bloom_trigger = bloom.density() >= DETECT_THRESHOLD_DENSITY
            deriv_trigger = derivative >= DERIV_THRESHOLD
            detect = bloom_trigger or deriv_trigger

            # ---- 3. Install / expire superflow --------------------------
            if detect and not superflow_active:
                print(f"[FLOWWEAVE] detect signal  "
                      f"(bloom_density={bloom.density():.4f}, "
                      f"deriv={derivative:.1f})")
                install_superflow()
                superflow_active = True
                superflow_expires = now + coalesce_s
                bloom.clear()

            if superflow_active and now >= superflow_expires:
                remove_superflow()
                superflow_active = False
                bloom.clear()

            time.sleep(REPORT_INTERVAL_S)

    except KeyboardInterrupt:
        if superflow_active:
            remove_superflow()
        print("[FLOWWEAVE] controller stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="FlowWeave control-plane loop with Bloom filter tracking"
    )
    p.add_argument("--coalesce-ms", type=int, default=1500,
                   help="Superflow coalesce duration in ms (default: 1500)")
    p.add_argument("--m-bits", type=int, default=1_568_962,
                   help="Bloom filter size in bits (default: 1568962)")
    p.add_argument("--k-hashes", type=int, default=13,
                   help="Number of Bloom filter hash functions (default: 13)")
    args = p.parse_args()

    controller_loop(
        coalesce_ms=args.coalesce_ms,
        m_bits=args.m_bits,
        k_hashes=args.k_hashes,
    )