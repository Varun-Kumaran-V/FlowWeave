# FlowWeave Resource Estimation

All numbers derived from simulation experiments (`sim/results/`).

## 1. TCAM Entries (from experiments)

| Scenario | Peak TCAM (mean) | Peak TCAM (max observed) | Avg TCAM (mean) |
|---|---:|---:|---:|
| bg=5 /ms (20 seeds) | 486.75 | — | 27.41 |
| bg=10 /ms (20 seeds) | 594.60 | — | 40.51 |
| bg=20 /ms (20 seeds) | 840.30 | — | 66.76 |
| ON-OFF bg=5 /ms | 482.00 | — | 33.27 |
| Targeted deriv sweep (bf=1e-4, deriv=2k–20k) | 1132–1185 | **2109** | — |

- **Max observed peak TCAM across all runs: 2109 entries**
- Worst-case mean peak TCAM: 1185.2 (targeted sweep, deriv=20000)
- Best-case mean peak TCAM: 482.0 (ON-OFF, bg=5)

## 2. Bloom Filter Memory

Parameters: n = 81 920 elements, p = 1×10⁻⁴ false-positive rate.

$$m = -\frac{n \ln p}{(\ln 2)^2} = 1\,570\,416 \text{ bits}$$

$$k = \frac{m}{n} \ln 2 \approx 13.3 \;\rightarrow\; 13 \text{ hash functions}$$

| Resource | Value |
|---|---:|
| Filter size (m) | 1 570 416 bits |
| Memory | 196 302 bytes ≈ **191.7 KiB** |
| Hash functions (k) | 13 |
| Design value used in code | m = 1 568 962, k = 13 |

## 3. Pipeline Stage Estimate (BMv2 / Tofino-style)

| Stage | Component | Operations | Resources |
|---:|---|---|---|
| 1 | Packet parsing | Extract Ethernet → IPv4 → TCP/UDP headers | Parser TCAM, header buses |
| 2 | Sketch update | Hash 5-tuple, read/write Bloom filter register array | 13 hash units, 1 register array (192 KiB SRAM) |
| 3 | Density counter update | Increment per-interval flow counter, compute density | 1 register (counter), 1 ALU |
| 4 | Derivative detection | Compare `density − mean` against `DERIV_THRESHOLD`; check capacity `projected ≥ 0.8 × TCAM_LIMIT` | 2 comparators, 1 register (prev mean) |
| 5 | Match-action forwarding | Exact-match table lookup → forward; superflow wildcard table lookup → aggregate | 1 exact-match table (≤ 2109 entries), 1 ternary/wildcard table (1 entry), `superflow_active` register |

**Total: 5 pipeline stages**

### Per-stage resource summary

| Component | Resource | Estimated Usage |
|---|---|---|
| Bloom filter | SRAM (register) | 191.7 KiB (1 568 962 bits) |
| Bloom filter | Hash units | 13 (CRC / double-hash) |
| Exact-match table | TCAM / SRAM entries | ≤ 2 109 (peak observed) |
| Exact-match table | TCAM / SRAM entries | 67 avg (bg=20, steady state) |
| Superflow table | Ternary entry | 1 wildcard rule |
| Density counter | Register + ALU | 1 counter + 1 ALU per stage |
| Derivative detector | Comparator | 2 (deriv threshold + capacity check) |
| Superflow active flag | Register | 1 bit (index 0) |
| Pipeline stages | Stages | 5 |
| Control messages | Per burst | 1 install + 1 remove (superflow) |
| Ctrl msgs (exact, bg=20) | Per trace | 3 181 mean ± 336 (95% CI) |
| Ctrl msg reduction | vs. baseline | 28.7× (bg=20) to 69.4× (bg=5) |
