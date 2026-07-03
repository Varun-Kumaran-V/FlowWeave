
# controller.py
# FlowWeave Control Plane

import json
import time
import os

SKETCH_FILE = "sketch.json"
TABLE_FILE = "table.json"

THRESHOLD = 0.5
SKETCH_SIZE = 256


def read_sketch():
    if not os.path.exists(SKETCH_FILE):
        return [0] * SKETCH_SIZE

    try:
        with open(SKETCH_FILE, "r") as f:
            return json.load(f)
    except:
        return [0] * SKETCH_SIZE


def write_sketch_empty():
    with open(SKETCH_FILE, "w") as f:
        json.dump([0] * SKETCH_SIZE, f)


def calculate_density(sketch):

    if len(sketch) == 0:
        return 0

    return sum(sketch) / len(sketch)


def install_superflow():

    print(">>> BURST DETECTED → Installing Superflow")

    rule = [
        {
            "type": "wildcard",
            "match": "10.0.0.0/24",
            "action": "aggregate"
        }
    ]

    with open(TABLE_FILE, "w") as f:
        json.dump(rule, f)


def remove_superflow():

    print("<<< Traffic Normal → Removing Superflow")

    with open(TABLE_FILE, "w") as f:
        json.dump([], f)


def main():

    print("=== FlowWeave Controller Started ===")

    active = False

    while True:

        sketch = read_sketch()

        density = calculate_density(sketch)

        print(f"[Controller] Density = {density:.2f}")

        if density > THRESHOLD and not active:

            install_superflow()
            active = True

        elif density <= THRESHOLD and active:

            remove_superflow()
            active = False

        # CRITICAL: Reset sketch every cycle
        write_sketch_empty()

        time.sleep(1)


if __name__ == "__main__":
    main()