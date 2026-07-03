
# switch.py
# FlowWeave Virtual Switch (Windows Compatible)

from scapy.all import sniff, IP
import json
import os
import threading

SKETCH_FILE = "sketch.json"
TABLE_FILE = "table.json"

SKETCH_SIZE = 256  # Bloom filter size

# Virtual Bloom Filter register
sketch_memory = [0] * SKETCH_SIZE

# Virtual TCAM table
flow_table = []


def initialize_files():
    """Initialize register and table files."""
    with open(SKETCH_FILE, "w") as f:
        json.dump(sketch_memory, f)

    with open(TABLE_FILE, "w") as f:
        json.dump([], f)


def load_table():
    """Load wildcard rules from controller."""
    global flow_table

    if not os.path.exists(TABLE_FILE):
        flow_table = []
        return

    try:
        with open(TABLE_FILE, "r") as f:
            flow_table = json.load(f)
    except:
        flow_table = []


def simple_hash(src, dst):
    """Simple deterministic hash function."""
    return hash(src + dst) % SKETCH_SIZE


def update_sketch(src, dst):
    """Update bloom filter and write to sketch.json."""
    index = simple_hash(src, dst)
    sketch_memory[index] = 1

    with open(SKETCH_FILE, "w") as f:
        json.dump(sketch_memory, f)


def wildcard_match(ip, prefix):
    """
    Match IP against prefix like 10.0.0.0/24
    """
    network, mask = prefix.split("/")
    mask = int(mask)

    ip_parts = ip.split(".")
    net_parts = network.split(".")

    # Compare based on mask
    compare_bytes = mask // 8

    return ip_parts[:compare_bytes] == net_parts[:compare_bytes]


def process_packet(pkt):
    """Packet processing logic (simulates P4 pipeline)."""

    if IP not in pkt:
        return

    src = pkt[IP].src
    dst = pkt[IP].dst

    # Load updated TCAM rules
    load_table()

    # Default action
    action = "Default Forward"

    # Check wildcard rules
    for rule in flow_table:

        if rule["type"] == "wildcard":

            if wildcard_match(dst, rule["match"]):
                action = "*** SUPERFLOW HIT ***"
                break

    # Update telemetry sketch
    update_sketch(src, dst)

    print(f"[Switch] {src} → {dst} | Action: {action}")


def main():
    print("=== FlowWeave Virtual Switch Started ===")
    initialize_files()

    print("Listening for packets...")

    sniff(
        prn=process_packet,
        store=0
    )


if __name__ == "__main__":
    main()