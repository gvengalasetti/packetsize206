# CMPE 206 NS-3 Project: Impact of Packet Size on Network Performance

This project contains reproducible NS-3 simulations for CMPE 206 (SJSU).

## Team

- Guna Vengalasetti
- Cameron Ghaemmaghami

## Project Layout

- project/simulations/baseline.cc
- project/simulations/experiment1_packet_size.cc
- project/simulations/experiment2_bandwidth.cc
- project/simulations/experiment3_congestion.cc
- project/scripts/plot_results.py
- project/results/ (CSV and PNG outputs)
- project/report/outline.md

## Requirements

- NS-3 version 3.38 or newer
- C++ build toolchain supported by your NS-3 install
- Python 3 with matplotlib for plotting

Install plotting dependency if needed:

```bash
python3 -m pip install matplotlib
```

## Reproducibility

All simulations set a fixed random seed using:

- RngSeedManager::SetSeed(206)
- Deterministic run numbers per scenario

## Build and Run Simulations

The simulation source code lives in project/simulations/. For compatibility with ns3 launch targets,
thin wrappers are also provided in scratch/.
From the repository root:

```bash
./ns3 run scratch/baseline
./ns3 run scratch/experiment1_packet_size
./ns3 run scratch/experiment2_bandwidth
./ns3 run scratch/experiment3_congestion
```

Each simulation writes CSV output into project/results/ by default:

- project/results/baseline.csv
- project/results/experiment1_packet_size.csv
- project/results/experiment2_bandwidth.csv
- project/results/experiment3_congestion.csv

## Experiment Summary

### Baseline

- Topology: 2-node point-to-point
- Link: 10 Mbps, 2 ms delay
- UDP traffic with 512-byte payload
- Duration: 10 s
- Metrics: throughput, goodput, delay, loss rate, overhead ratio

### Experiment 1: Packet Size Sweep

- Fixed link: 10 Mbps, no congestion
- Packet sizes: 64, 128, 256, 512, 1024, 1500 bytes
- Metrics: goodput, overhead ratio, delay, packet loss

### Experiment 2: Bandwidth Sweep

- Packet sizes: 512 and 1500 bytes
- Bandwidths: 1, 5, 10, 100 Mbps
- Metrics: throughput, goodput, delay, loss, overhead ratio, serialization delay
- Serialization delay model:
  - serialization_delay = packet_size / bandwidth

### Experiment 3: Congestion vs No Congestion

- Topology: multi-source dumbbell (sources -> router -> bottleneck -> router -> receiver)
- Bottleneck: 5 Mbps
- Non-bottleneck links: 100 Mbps
- Packet sizes: 256 and 1024 bytes
- Modes:
  - no_congestion: 1 sender
  - congested: 3 senders
- Metrics: packet loss rate, queue drops, goodput, throughput, delay, jitter, overhead ratio

## Generate Graphs

After all CSV files are generated, run:

```bash
python3 project/scripts/plot_results.py
```

Generated figures (saved in project/results/):

- goodput_vs_packet_size.png
- overhead_vs_packet_size.png
- delay_vs_packet_size.png
- throughput_vs_bandwidth.png
- loss_vs_packet_size_congestion.png

## Metrics Notes

- Throughput is computed from FlowMonitor rxBytes over active traffic time.
- Goodput is computed from delivered payload bytes over active traffic time.
- Overhead ratio uses a UDP+IPv4 header approximation of 28 bytes per packet:
  - overhead_ratio = header_bytes / (payload_bytes + header_bytes)
- Delay and jitter are averaged from FlowMonitor delay/jitter aggregates.
