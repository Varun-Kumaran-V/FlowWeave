# Algorithmic Models Documentation

This directory contains the core mathematical simulation models representing the FlowWeave architecture, utilized strictly for experimental benchmarking and evaluation.

## FlowWeave Simulation Model (flowweave_model.py)

This model represents the behavior of the FlowWeave controller interacting with the data plane under simulated constraints.

### Core Mechanisms

- **Statistical Density Tracking:** Maintains a moving window of telemetry data to establish a dynamic baseline of background network noise, utilizing mean and standard deviation.
- **Tri-Factor Burst Detection:**
  - Derivative-based spike detection above established moving averages.
  - Predictive capacity triggers (80% TCAM saturation threshold).
  - Standard deviation outlier detection.
- **Adaptive Rule Coalescing:** Dynamically adjusts the duration of wildcard Superflow rules based on the measured width of the active traffic burst, mitigating control-plane oscillation.
