# Hardware Data Plane Documentation

This directory contains the P4_16 architectural definitions required to deploy FlowWeave onto programmable switch ASICs (Application-Specific Integrated Circuits).

## FlowWeave P4 Pipeline (flowweave_small.p4)

This file defines the strict data-plane pipeline, parsing logic, and stateful ALU (Arithmetic Logic Unit) operations.

### Core Mechanisms

- **Stateful Register Management:** Allocates switch SRAM to maintain packet counts per time-slot.
- **In-Network Computation:** Implements a bit-shift optimized Exponentially Weighted Moving Average (EWMA) directly in the ingress pipeline to establish a density baseline.
- **Hardware Trigger:** Computes the flow density derivative at line-rate. If the threshold is breached, the data plane autonomously clones the trigger packet to the CPU port to initiate control-plane superflow injection.

## Hardware Resource Specification (resource_table.md)

This document provides the mathematical justification and hardware mapping for the P4 pipeline.

### Silicon Allocation

- **SRAM (Telemetry):** Requires ~192 KiB to sustain an 81,920 element capacity with a 0.01% false-positive tolerance.
- **ALU & Comparators:** Requires 1 Arithmetic Logic Unit for density incrementation and 2 hardware comparators for derivative and capacity threshold triggers.
- **TCAM (Forwarding):** Validates that peak operational state remains under the 2,000-entry commodity hardware limit (averaging 840 entries under heavy load).
- **Pipeline Depth:** Compiles successfully into a standard 5-stage ingress architecture.
