
controller_instrumented.py - derivative-based controller emulation
sketch_updater.py - simple telemetry producer that writes sketch.json (density)
table.json - installed rules (written by controller)
metrics.json - controller metrics (written by controller)
Run sketch_updater.py in one terminal and controller_instrumented.py in another to emulate behavior.

## Southbound Communication (rule_manager.py)
This module isolates the P4Runtime protocol logic required to modify data-plane state.

### Core Mechanisms
- **State Enforcement:** Translates logical control-plane decisions (Superflow aggregation) into hardware-specific P4 Table Entry objects.
- **TCAM Lifecycle Management:** Provides the discrete `install_rule` and `delete_rule` functions to manage wildcard entries, ensuring the switch memory is accurately updated when burst boundaries are crossed.
- **Hardware Abstraction:** Mocks physical gRPC channels to allow local software simulation and performance benchmarking without requiring bare-metal deployment.

## Instrumented Evaluation Controller (controller_instrumented.py)
This module provides a metric-tracking wrapper around the core control-plane logic, utilized exclusively for live simulation benchmarking.

### Core Mechanisms
- **Time-Aware Derivative Tracking:** Calculates flow density derivatives using precise system clock deltas for high-fidelity evaluation.
- **Timer-Based Lifecycle:** Implements a strict, static coalesce duration timer (2.2 seconds) for wildcard entry removal, providing a baseline comparison against the adaptive model.
- **Telemetry Export:** Autonomously tracks and exports control-plane signaling volume and TCAM occupancy snapshots to a localized `metrics.json` file for post-run analysis.