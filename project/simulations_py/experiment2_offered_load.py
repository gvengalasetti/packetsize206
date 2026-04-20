#!/usr/bin/env python3
"""
Experiment 2 — Variant: Offered Load Variation
===============================================
Modification: Vary the offered load (as a fraction of link capacity) while
              holding bandwidth and packet size constant (10 Mbps, 512 bytes).

Justification: The original Experiment 2 always sends at 80 % of capacity.
This variant sweeps load from 20 % up to 120 % of link capacity to reveal the
saturation knee — the point where loss and queueing delay rise sharply.
Understanding the saturation point is critical for provisioning links so they
operate in the efficient region below congestion onset.
"""
import csv
from ns import ns

IP_UDP_HEADER_BYTES  = 28
PACKET_SIZE          = 512      # bytes  — fixed
LINK_BW_MBPS         = 10       # Mbps   — fixed
# Offered load as a fraction of LINK_BW (1.2 = 120 % means intentional overload)
LOAD_FACTORS         = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]


def compute_metrics(stats, packet_size, active_time):
    throughput   = (stats.rxBytes * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    goodput      = (stats.rxPackets * packet_size * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    delay_ms     = (stats.delaySum.GetSeconds() * 1000.0 / stats.rxPackets) if stats.rxPackets > 0 else 0.0
    loss_pct     = ((stats.txPackets - stats.rxPackets) * 100.0 / stats.txPackets) if stats.txPackets > 0 else 0.0
    total_bytes  = stats.rxPackets * (packet_size + IP_UDP_HEADER_BYTES)
    overhead_pct = (stats.rxPackets * IP_UDP_HEADER_BYTES * 100.0 / total_bytes) if total_bytes > 0 else 0.0
    return throughput, goodput, delay_ms, loss_pct, overhead_pct


def run_one(load_factor, run_id, sim_seconds=10.0, port=9011):
    ns.RngSeedManager.SetRun(run_id)

    nodes = ns.NodeContainer()
    nodes.Create(2)

    p2p = ns.PointToPointHelper()
    p2p.SetDeviceAttribute("DataRate", ns.StringValue(f"{LINK_BW_MBPS}Mbps"))
    p2p.SetChannelAttribute("Delay", ns.StringValue("2ms"))
    devices = p2p.Install(nodes)

    internet = ns.InternetStackHelper()
    internet.Install(nodes)

    ipv4 = ns.Ipv4AddressHelper()
    ipv4.SetBase(ns.Ipv4Address("10.1.11.0"), ns.Ipv4Mask("255.255.255.0"))
    ifaces = ipv4.Assign(devices)

    sink = ns.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo(),
    )
    sink_apps = sink.Install(ns.NodeContainer(nodes.Get(1)))
    sink_apps.Start(ns.Seconds(0.0))
    sink_apps.Stop(ns.Seconds(sim_seconds + 0.5))

    offered_bps = int(LINK_BW_MBPS * load_factor * 1e6)   # <-- varied parameter
    remote = ns.InetSocketAddress(ifaces.GetAddress(1), port)
    onoff  = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
    onoff.SetAttribute("DataRate",   ns.DataRateValue(ns.DataRate(offered_bps)))
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
    output_csv = "project/results/experiment2_offered_load.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "load_factor",
            "offered_mbps",
            "packet_size_bytes",
            "bandwidth_mbps",
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "packet_loss_rate_pct",
            "overhead_ratio_pct",
        ])

        for run_id, lf in enumerate(LOAD_FACTORS, start=1):
            offered = LINK_BW_MBPS * lf
            m = run_one(lf, run_id)
            w.writerow([f"{lf:.1f}", f"{offered:.1f}", PACKET_SIZE, LINK_BW_MBPS,
                        f"{m[0]:.6f}", f"{m[1]:.6f}", f"{m[2]:.6f}",
                        f"{m[3]:.6f}", f"{m[4]:.6f}"])
            print(f"  load={lf*100:.0f}%  throughput={m[0]:.3f} Mbps  delay={m[2]:.2f} ms  loss={m[3]:.2f}%")

    print(f"\nExperiment 2 (offered load variation) results written to: {output_csv}")


if __name__ == "__main__":
    main()
