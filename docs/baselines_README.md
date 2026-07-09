# Evaluation Baselines Documentation

This directory contains the mathematical control models used to benchmark the FlowWeave architecture against existing industry standards.

## Exact Match LRU (exact_match_lru.py)

This model represents a traditional Software-Defined Networking (SDN) environment utilizing reactive rule installation.

### Operational Mechanics

- **Rule Allocation:** Enforces a strict 1:1 ratio between incoming microflows and TCAM rule installations.
- **Eviction Policy:** Simulates a time-based Least Recently Used (LRU) eviction cycle (`FLOW_LIFETIME_MS = 50.0`) where rules are only cleared after they expire.
- **Failure State Modeling:** Accurately models the "reaction gap" inherent in reactive SDN controllers. When synchronized bursts exceed the `TCAM_LIMIT` (2,000 entries), the model quantifies the exact volume of dropped packets and the resulting spike in control-plane signaling overhead.

## Aggregated Flow Table (agft_model.py)

This model represents a spatial aggregation baseline, utilizing subnet-level grouping to compress routing state.

### Operational Mechanics

- **Static Compression:** Enforces a rigid 10:1 aggregation ratio (`AGG_RATIO = 10.0`), assuming contiguous IP block allocations for incoming workloads.
- **Group-Level Allocation:** TCAM memory is allocated in blocks. If memory is exhausted, packet drops occur in synchronized blocks corresponding to the aggregation multiplier.
- **Performance Characteristics:** Reduces control-plane signaling overhead relative to Exact Match models, but lacks the temporal adaptability required to handle instantaneous, highly variable AI microbursts without incurring grouped packet loss.
