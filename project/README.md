# CMPE 206 NS-3 Project: Impact of Packet Size on Network Performance

NS-3 simulations studying how packet size, offered load, link MTU, transport
protocol, and link bandwidth shape network performance.

## Team

- Guna Vengalasetti
- Cameron Ghaemmaghami

## Layout

```
project/
  simulations_py/    # Python ns-3 simulation scripts
  scripts/           # Plotting (matplotlib)
  results/           # CSV outputs and PNG figures
  report/            # IEEE-format report sources
  main.tex           # Compiled report
```

## Requirements

- ns-3 with Python bindings
- Python 3 with matplotlib

## Running

From the repo root, each simulation is a standalone Python script:

```bash
python3 project/simulations_py/experiment1_packet_size.py
python3 project/simulations_py/experiment2_offered_load.py
python3 project/simulations_py/experiment3_link_mtu.py
python3 project/simulations_py/experiment4_tcp_competing_flow.py
python3 project/simulations_py/experiment5_packet_size_bw_regimes.py
```

Each writes a CSV to `project/results/results_experimentN.csv`.

Generate graphs after CSVs exist:

```bash
python3 project/scripts/plot_results_multihop.py
```

Figures are written to `project/results/images/`.

## The Five Experiments

All use a shared topology: 3 UDP senders -> Router1 -> [p2p bottleneck] ->
Router2 -> 802.11g WiFi -> Receiver. Each experiment varies one parameter.

1. **Packet Size Sweep** — fixed 10 Mbps bottleneck, sweep packet size
   (128–1500 B). Isolates packetization effects.
2. **Offered Load Variation** — fixed 512 B packets, sweep total offered load
   (20%–120% of bottleneck). Shows congestion onset.
3. **Link MTU Sweep** — fixed 1000 B payload (1028 B frame), sweep link MTU
   (512–1500 B). Shows the on/off MTU drop boundary.
4. **TCP vs UDP Competing Flow** — UDP senders share the bottleneck with a
   TCP BulkSend flow, swept by packet size. Shows fairness behavior.
5. **Bandwidth Regime Comparison** — sweep packet size at a 1 Mbps and a
   100 Mbps bottleneck. Shows how link capacity changes the packet-size effect.

All metrics: throughput, goodput, average delay, packet loss, overhead ratio
(plus drops for MTU/TCP experiments). RNG seed fixed at 206.
