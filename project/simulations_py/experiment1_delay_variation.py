#!/usr/bin/env python3
"""
Experiment 1 — Variant: Propagation Delay Variation
=====================================================
Modification: Vary the link propagation delay while holding packet size
              and bandwidth constant (512-byte packets, 10 Mbps link, 8 Mbps load).

Justification: Propagation delay is the dominant latency component on long-haul
links.  By sweeping delay from 1 ms (LAN) to 100 ms (cross-country WAN) we
isolate its effect on end-to-end latency, throughput, and overhead — keeping
everything else identical to the Experiment 1 baseline so the comparison is
clean.
"""
import csv
from ns import ns

IP_UDP_HEADER_BYTES = 28
PACKET_SIZE   = 512          # bytes  — fixed
OFFERED_RATE  = "8Mbps"      # fixed
LINK_BW       = "10Mbps"     # fixed
DELAY_VALUES  = ["1ms", "5ms", "10ms", "20ms", "50ms", "100ms"]


def compute_metrics(stats, packet_size, active_time):
    throughput  = (stats.rxBytes * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    goodput     = (stats.rxPackets * packet_size * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    delay_ms    = (stats.delaySum.GetSeconds() * 1000.0 / stats.rxPackets) if stats.rxPackets > 0 else 0.0
    loss_pct    = ((stats.txPackets - stats.rxPackets) * 100.0 / stats.txPackets) if stats.txPackets > 0 else 0.0
    total_bytes = stats.rxPackets * (packet_size + IP_UDP_HEADER_BYTES)
    overhead_pct = (stats.rxPackets * IP_UDP_HEADER_BYTES * 100.0 / total_bytes) if total_bytes > 0 else 0.0
    return throughput, goodput, delay_ms, loss_pct, overhead_pct


def run_one(delay_str, run_id, sim_seconds=10.0, port=9010):
    ns.RngSeedManager.SetRun(run_id)

    nodes = ns.NodeContainer()
    nodes.Create(2)

    p2p = ns.PointToPointHelper()
    p2p.SetDeviceAttribute("DataRate", ns.StringValue(LINK_BW))
    p2p.SetChannelAttribute("Delay", ns.StringValue(delay_str))   # <-- varied parameter
    devices = p2p.Install(nodes)

    internet = ns.InternetStackHelper()
    internet.Install(nodes)

    ipv4 = ns.Ipv4AddressHelper()
    ipv4.SetBase(ns.Ipv4Address("10.1.10.0"), ns.Ipv4Mask("255.255.255.0"))
    ifaces = ipv4.Assign(devices)

    sink = ns.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo(),
    )
    sink_apps = sink.Install(ns.NodeContainer(nodes.Get(1)))
    sink_apps.Start(ns.Seconds(0.0))
    sink_apps.Stop(ns.Seconds(sim_seconds + 0.5))

    remote = ns.InetSocketAddress(ifaces.GetAddress(1), port)
    onoff  = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
    onoff.SetAttribute("DataRate",   ns.DataRateValue(ns.DataRate(OFFERED_RATE)))
    onoff.SetAttribute("PacketSize", ns.UintegerValue(PACKET_SIZE))
    onoff.SetAttribute("OnTime",  ns.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
    onoff.SetAttribute("OffTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=0]"))

    sender = onoff.Install(ns.NodeContainer(nodes.Get(0)))
    sender.Start(ns.Seconds(1.0))
    sender.Stop(ns.Seconds(sim_seconds))

    flow    = ns.FlowMonitorHelper()
    monitor = flow.InstallAll()

    ns.Simulator.Stop(ns.Seconds(sim_seconds + 1.0))
    ns.Simulator.Run()
    monitor.CheckForLostPackets()

    classifier = flow.GetClassifier()
    chosen = None
    for fid, st in monitor.GetFlowStats():
        t = classifier.FindFlow(fid)
        if t.destinationPort == port:
            chosen = st
            break

    ns.Simulator.Destroy()

    if chosen is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    return compute_metrics(chosen, PACKET_SIZE, sim_seconds - 1.0)


def main():
    ns.RngSeedManager.SetSeed(206)
    output_csv = "project/results/experiment1_delay_variation.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "link_delay",
            "packet_size_bytes",
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "packet_loss_rate_pct",
            "overhead_ratio_pct",
        ])

        for run_id, delay in enumerate(DELAY_VALUES, start=1):
            m = run_one(delay, run_id)
            w.writerow([delay, PACKET_SIZE,
                        f"{m[0]:.6f}", f"{m[1]:.6f}", f"{m[2]:.6f}",
                        f"{m[3]:.6f}", f"{m[4]:.6f}"])
            print(f"  delay={delay:>6s}  throughput={m[0]:.3f} Mbps  avg_delay={m[2]:.2f} ms  loss={m[3]:.2f}%")

    print(f"\nExperiment 1 (delay variation) results written to: {output_csv}")


if __name__ == "__main__":
    main()
