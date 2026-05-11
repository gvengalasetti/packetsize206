# CMPE 206 Project Report Outline

## Project Title

Impact of Packet Size on Network Performance

## Authors

- Guna Vengalasetti
- Cameron Ghaemmaghami

## 1. Introduction

- Explain why packet size matters for practical network design and protocol tuning.
- Connect packet size to MTU, fragmentation risk, and transport/application efficiency.
- Define key metrics used in this report: throughput, goodput, delay, loss, and overhead ratio.
- State project objective and research questions for baseline, bandwidth variation, and congestion cases.

## 2. Related Work

- Paper 1: Effect of packet size on loss rate and delay in wireless links.
- Summary points:
  - Packet length influences both loss and delay even when MAC mechanisms compensate for errors.
  - BER characteristics are tied to observed latency and reliability trends.
  - Relevance to this project: motivates packet-size sensitivity analysis for delay/loss metrics.
- Paper 2: Quantifying the impact of network congestion on application performance and network metrics.
- Summary points:
  - Stall/flit ratio correlates strongly with congestion and execution time in HPC/MPI workloads.
  - Congestion-sensitive metrics can predict application-level performance degradation.
  - Relevance to this project: supports multi-flow bottleneck experiment and congestion justification.
- Paper 3: Increasing Packet Sizes to Mitigate Performance Issues in High-Speed Packet Networks.
- Summary points:
  - A fourfold MTU increase can reduce packet rate by about two-thirds.
  - Relationship between MTU and average packet count is inverse logarithmic.
  - Relevance to this project: supports analyzing overhead reduction for larger payloads.
- Paper 4: Impact of Variable MTU Size of Voice Packet To Reduce Packet Loss In Bandwidth Constraint Military Network.
- Summary points:
  - Lower MTU reduces efficiency due to increased overhead burden.
  - Larger frames can see higher corruption probability under BER constraints.
  - Relevance to this project: frames expected trade-off between efficiency and error vulnerability.

## 3. Simulation Design

- Describe baseline two-node point-to-point topology.
- Describe bandwidth-variation topology and controlled variables.
- Describe congestion topology (multi-source dumbbell with bottleneck link).
- List NS-3 modules and tooling used: PointToPoint, InternetStack, Applications, FlowMonitor.
- Mention fixed RNG seed and run numbering for reproducibility.

## 4. Experimental Setup

- Include parameter table for each experiment:
  - Link rates, delays, packet sizes, offered load, simulation duration.
  - Number of senders/flows and bottleneck configuration.
  - Metrics collected and computation formulas.
- Clarify assumptions:
  - UDP + IPv4 header overhead model for overhead ratio.
  - FlowMonitor aggregation method for multi-flow scenarios.

## 5. Results

- Figure: Goodput vs Packet Size.
- Figure: Overhead Ratio vs Packet Size.
- Figure: End-to-End Delay vs Packet Size.
- Figure: Throughput vs Bandwidth (separate lines for 512 B and 1500 B packets).
- Figure: Packet Loss Rate vs Packet Size under congestion and no congestion.
- Placeholder bullets for observed trends and anomalies.

## 6. Discussion

- Interpret results using OSI-layer perspective:
  - L2 framing and queuing behavior.
  - L3 MTU and fragmentation implications.
  - L4 (UDP) overhead effect on goodput.
- Explain serialization delay relationship:
  - serialization delay = packet_size / bandwidth.
- Discuss congestion behavior:
  - queue buildup, drops, jitter, and head-of-line effects.
- Compare findings to related work and highlight consistencies/differences.
- Discuss threats to validity and simulation limitations.

## 7. Conclusion

- Summarize primary findings for each experiment.
- State practical recommendations for packet-size selection under different link conditions.
- List future extensions (TCP comparison, wireless BER/error model, AQM queue disciplines).
