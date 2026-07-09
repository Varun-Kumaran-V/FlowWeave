# FlowWeave

FlowWeave: A phase-aware, telemetry-driven SDN flow management framework designed to mitigate TCAM optimization constraints and eliminate packet loss during synchronized distributed AI training workloads (e.g., AllReduce).

## Simulation Datasets & Workload Generation

The simulation environment relies on a procedural synthetic trace engine (`sim/trace_generator.py`) that models data-parallel distributed AI training traffic patterns within an NVIDIA DGX cluster fabric.

### Traffic Specifications

- **Synchronized Bursts:** Simulates standard AllReduce ring-topologies where nodes concurrently execute gradient exchanges, causing massive microflow spikes across short window intervals (2 ms).
- **Background Noise Matrix:** Provides two mathematical models to test control plane resiliency:
  - **Poisson Mode:** Independent, standard exponential arrival distributions.
  - **ON-OFF Mode:** High-stress alternating windows (50ms active / 50ms idle) to evaluate burst detection latency.

## Architecture Components

### Data Plane Emulation (switch_emulator/switch.py)

The repository includes a functional software-emulated P4 data plane pipeline that processes packets and exposes state registers via localized JSON memory maps.

- **Telemetry Sketching:** Emulates a hardware-constrained Bloom Filter register array (m=256 bits) using deterministic string hashing to monitor traffic concurrency.
- **TCAM Wildcard Matching:** Emulates line-rate hardware prefix-matching against incoming destination network subnets to track rule fulfillment.

### Control Plane (controller/controller.py & sketch_manager.py)

The centralized controller polls data-plane state without blocking routing operations, applying derivative mathematics to detect bursts.

- **Atomic Read-and-Reset:** Fetches the active Bloom filter sketch and zeros the hardware register in a single operational cycle to ensure temporal accuracy.
- **Proactive Rule Injection:** Upon crossing the density threshold, the controller injects coarse-grained wildcard rules (superflows) into the switch's TCAM, aggregating multiple microflows into single memory entries to prevent table exhaustion.

## Evaluation Suite & Baselines

The repository includes a comprehensive mathematical evaluation suite (`sim/`) designed to benchmark FlowWeave against industry-standard SDN paradigms.

### Architectural Baselines

- **Exact Match (LRU):** Traditional reactive SDN routing with timeout-based eviction.
- **TECache:** Frequency-aware traffic engineering prioritizing heavy-hitter flows.
- **AGFT (Aggregated Flow Table):** Spatial aggregation enforcing rigid 10:1 microflow grouping.

### Orchestration & Profiling

- **Mathematical Engine:** Python-based simulation environment (`models/flowweave_model.py`) evaluating rule lifecycle, control-plane messaging, and packet drop rates without requiring physical P4 hardware.
- **Statistical Rigor:** Multi-seed orchestration scripts (`run_multiseed.py`) generate randomized traces and compute 95% Confidence Intervals for robust variance analysis.
- **Parameter Sweeps:** Combinatorial grid-search orchestrators (`targeted_sweep.py`, `param_sweep.py`) identify Pareto-optimal frontiers between TCAM saturation and control-overhead reduction.
