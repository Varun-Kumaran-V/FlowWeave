# Utilities and Diagnostics Documentation

This directory outlines the auxiliary scripts used for data validation and experimental reproducibility.

## Trace Analysis (`analyze_traces.py`)

A diagnostic script designed to validate synthetic workload integrity prior to simulation ingestion.

- **Verification:** Ensures temporal monotonicity across CSV and JSON datasets.
- **Pattern Recognition:** Autonomously detects periodic AllReduce spikes to confirm the mathematical accuracy of the synthetic traffic generator.

## Experiment Utilities (`sim/experiment_utils.py`)

Shared infrastructure for the simulation orchestration layer.

- **Reproducibility Tracking:** Extracts system platform data and Git SHA identifiers, binding them to result sets via `metadata.json`.
- **Statistical Operations:** Computes 95% Confidence Intervals for robust graphical variance representation.
