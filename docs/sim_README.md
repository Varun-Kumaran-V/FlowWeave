# Simulation & Orchestration Documentation

This directory contains the execution wrappers and orchestration scripts required to deploy, benchmark, and graph the architectural models.

## CLI-Integrated Controller (sim/controller_flowweave.py)

A dynamic execution wrapper for the FlowWeave control plane, optimized for multi-parameter simulation sweeps.

- **Dynamic Parameterization:** Accepts execution arguments (`--coalesce-ms`, `--m-bits`, `--k-hashes`) via CLI for rapid parameter grid search orchestration.
- **Software Sketch Emulation:** Implements a pure-Python, double-hashed Bloom Filter (SHA-256) capable of localized bitwise union operations, utilized when physical P4 data-plane hardware is unavailable for telemetry generation.
