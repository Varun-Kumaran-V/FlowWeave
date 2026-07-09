
paper_demo.py - simplified FlowWeave vs Baseline simulation harness (deterministic, fast)

To run:
    python3 paper_demo.py

What it does:
- simulates a short timeline with a hyper-burst in the middle
- baseline installs exact-match entries until TCAM_LIMIT is reached
- FlowWeave installs a single superflow when derivative of flow density exceeds DERIV_THRESHOLD
- reports TCAM peaks, drop counts, installs, controller messages, and p99 setup latencies for both approaches

Tweak parameters inside paper_demo.py header for different scenarios.
