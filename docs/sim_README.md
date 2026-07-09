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
