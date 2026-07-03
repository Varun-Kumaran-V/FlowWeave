# Evaluation Baselines Documentation

This directory contains the mathematical control models used to benchmark the FlowWeave architecture against existing industry standards.

## Exact Match LRU (exact_match_lru.py)

This model represents a traditional Software-Defined Networking (SDN) environment utilizing reactive rule installation.

### Operational Mechanics

- **Rule Allocation:** Enforces a strict 1:1 ratio between incoming microflows and TCAM rule installations.
- **Eviction Policy:** Simulates a time-based Least Recently Used (LRU) eviction cycle (`FLOW_LIFETIME_MS = 50.0`) where rules are only cleared after they expire.
- **Failure State Modeling:** Accurately models the "reaction gap" inherent in reactive SDN controllers. When synchronized bursts exceed the `TCAM_LIMIT` (2,000 entries), the model quantifies the exact volume of dropped packets and the resulting spike in control-plane signaling overhead.
