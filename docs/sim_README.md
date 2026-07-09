# Simulation & Orchestration Documentation

This directory contains the execution wrappers and orchestration scripts required to deploy, benchmark, and graph the architectural models.

## CLI-Integrated Controller (sim/controller_flowweave.py)

A dynamic execution wrapper for the FlowWeave control plane, optimized for multi-parameter simulation sweeps.

- **Dynamic Parameterization:** Accepts execution arguments (`--coalesce-ms`, `--m-bits`, `--k-hashes`) via CLI for rapid parameter grid search orchestration.
- **Software Sketch Emulation:** Implements a pure-Python, double-hashed Bloom Filter (SHA-256) capable of localized bitwise union operations, utilized when physical P4 data-plane hardware is unavailable for telemetry generation.

## Analytic Demonstration (sim/paper_demo.py)

A lightweight, zero-dependency mathematical simulation designed to instantly validate the control-plane reduction hypothesis.

- **Deterministic Modeling:** Utilizes strict, hardcoded traffic bursts and capacity constraints to ensure perfectly repeatable outputs for academic publication.
- **Side-by-Side Execution:** Computes Baseline Exact Match and FlowWeave metrics simultaneously across a discretized time-step loop.
- **Latency Estimation:** Employs a randomized sample generator to approximate 99th percentile flow setup latency without requiring a full OS-level network emulation.

## Analytic Demonstration (sim/paper_demo.py)

A lightweight, zero-dependency mathematical simulation designed to instantly validate the control-plane reduction hypothesis.

- **Deterministic Modeling:** Utilizes strict, hardcoded traffic bursts and capacity constraints to ensure perfectly repeatable outputs for academic publication.
- **Side-by-Side Execution:** Computes Baseline Exact Match and FlowWeave metrics simultaneously across a discretized time-step loop.
- **Latency Estimation:** Employs a randomized sample generator to approximate 99th percentile flow setup latency without requiring a full OS-level network emulation.

## Head-to-Head Evaluator (sim/run_head_to_head.py)

A deterministic benchmarking script designed to execute a synchronized 4-way architectural comparison using a single traffic trace.

- **Unified Constraints:** Enforces a rigid, shared parameter dictionary (e.g., 2,000 TCAM entries, 50ms rule lifetime) across all models to guarantee experimental control.
- **Automated Export:** Aggregates performance metrics (drops, TCAM peak, control messages) into a standardized CSV format for downstream plotting and analysis.

## Multi-Seed Orchestration (sim/run_multiseed.py)

An automated benchmarking orchestrator designed to establish statistical significance across randomized traffic distributions.

- **Dynamic Workload Generation:** Autonomously generates distinct, deterministic synthetic traffic traces per execution seed to evaluate algorithmic resilience against varying background noise.
- **Statistical Aggregation:** Computes programmatic variance metrics, including Mean, Standard Deviation, and 95% Confidence Intervals, across all simulation iterations.
- **Artifact Management:** Outputs localized directory structures containing raw execution data (`per_seed.csv`), aggregated statistics (`summary.csv`), and environmental state tracking (`metadata.json`).

## Targeted Parameter Sweep (sim/targeted_sweep.py)

A combinatorial grid-search orchestrator designed to evaluate FlowWeave's sensitivity to internal threshold tuning.

- **Matrix Evaluation:** Utilizes combinatorial cross-products to automatically test matrices of Bloom Filter error tolerances against derivative detection thresholds.
- **Multi-Dimensional Aggregation:** Nests multi-seed statistical variance tracking within parameter iteration loops to ensure tuning recommendations are mathematically robust.
- **Tuning Artifacts:** Outputs a specialized `targeted_summary.csv` designed to identify Pareto-optimal parameter configurations.

## 3D Parameter Profiler (sim/param_sweep.py)

An isolated profiling script used to map FlowWeave's internal behavioral surface across a three-dimensional parameter grid.

- **Isolated Execution:** Bypasses baseline models to exclusively stress-test FlowWeave's adaptive mathematical core.
- **Automated Visualization:** Integrates `matplotlib` to autonomously generate and export line graphs plotting architectural overhead (TCAM usage, control signaling) against algorithmic sensitivity triggers.

## Master Visualization Script (sim/plot_results.py)

The final pipeline stage responsible for translating aggregated statistical matrices into publication-ready figures.

- **Cross-Scenario Ingestion:** Autonomously navigates the `sim/results/` directory structure to aggregate data across varying environmental stress tests (Poisson, ON-OFF, Skewed).
- **Pareto Mapping:** Generates scatter-plot visualizations to identify the Pareto frontier, mapping the optimal operational tradeoffs between TCAM saturation and control-plane signaling reduction.
