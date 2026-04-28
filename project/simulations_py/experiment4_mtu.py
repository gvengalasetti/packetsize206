#!/usr/bin/env python3
"""
Experiment 4 — MTU Boundary Effects
=====================================
Scenario: A single UDP sender transmits over a point-to-point link whose MTU
is deliberately set to 576 bytes (the historic minimum for IPv4 routers, per
RFC 791).  The application payload size is swept from 64 B up to 1500 B.

Key insight: The total on-wire frame = payload + 28 B (IP+UDP headers).
             The PointToPointNetDevice drops any frame larger than its MTU.
             Therefore packets with payload > 548 B  (548 + 28 = 576)
             will be dropped entirely, producing a hard loss cliff at the
             MTU boundary.

This demonstrates why applications must respect path MTU: exceeding it
causes 100% loss for those packets, collapsing throughput.
"""
import csv
from ns import ns

IP_UDP_HEADER_BYTES = 28

# Link MTU in bytes — this is the key constraint being studied.
# Payload must satisfy: payload + IP_UDP_HEADER_BYTES <= LINK_MTU
LINK_MTU    = 576
MTU_PAYLOAD = LINK_MTU - IP_UDP_HEADER_BYTES   # = 548 — maximum safe payload

# Sweep includes sizes below, at, and above the MTU boundary.
PAYLOAD_SIZES = [64, 256, 512, MTU_PAYLOAD, 600, 1024, 1500]

LINK_BW      = "10Mbps"
OFFERED_RATE = "8Mbps"


def compute_metrics(stats, packet_size, active_time):
    throughput   = (stats.rxBytes * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    goodput      = (stats.rxPackets * packet_size * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    delay_ms     = (stats.delaySum.GetSeconds() * 1000.0 / stats.rxPackets) if stats.rxPackets > 0 else 0.0
    loss_pct     = ((stats.txPackets - stats.rxPackets) * 100.0 / stats.txPackets) if stats.txPackets > 0 else 0.0
    total_bytes  = stats.rxPackets * (packet_size + IP_UDP_HEADER_BYTES)
    overhead_pct = (stats.rxPackets * IP_UDP_HEADER_BYTES * 100.0 / total_bytes) if total_bytes > 0 else 0.0
    flowmonitor_drop_events = sum(int(d) for d in stats.packetsDropped)
    return (
        throughput,
        goodput,
        delay_ms,
        loss_pct,
        overhead_pct,
        flowmonitor_drop_events,
        int(stats.txPackets),
        int(stats.rxPackets),
    )


def run_one(payload_size, run_id, sim_seconds=10.0, port=9020):
    ns.RngSeedManager.SetRun(run_id)

    nodes = ns.NodeContainer()
    nodes.Create(2)

    p2p = ns.PointToPointHelper()
    p2p.SetDeviceAttribute("DataRate", ns.StringValue(LINK_BW))
    p2p.SetDeviceAttribute("Mtu",      ns.UintegerValue(LINK_MTU))  # <-- MTU constraint
    p2p.SetChannelAttribute("Delay",   ns.StringValue("2ms"))
    devices = p2p.Install(nodes)

    internet = ns.InternetStackHelper()
    internet.Install(nodes)

    ipv4 = ns.Ipv4AddressHelper()
    ipv4.SetBase(ns.Ipv4Address("10.1.20.0"), ns.Ipv4Mask("255.255.255.0"))
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
    onoff.SetAttribute("PacketSize", ns.UintegerValue(payload_size))
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
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)
    return compute_metrics(chosen, payload_size, sim_seconds - 1.0)


def main():
    ns.RngSeedManager.SetSeed(206)
    output_csv = "project/results/experiment4_mtu.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "payload_bytes",
            "frame_bytes",        # payload + IP/UDP headers
            "link_mtu_bytes",
            "exceeds_mtu",        # boolean flag for clarity
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "packet_loss_rate_pct",
            "overhead_ratio_pct",
            "flowmonitor_drop_events",
            "oversized_packet_drops",
        ])

        for run_id, p in enumerate(PAYLOAD_SIZES, start=1):
            frame = p + IP_UDP_HEADER_BYTES
            exceeds = frame > LINK_MTU
            m = run_one(p, run_id)
            # FlowMonitor provides end-to-end drop events; this captures dropped oversized packets
            # when they manifest as tx-rx gaps for cases above the MTU threshold.
            oversized_packet_drops = 0
            if exceeds:
                oversized_packet_drops = max(0, int(m[6]) - int(m[7]))
            w.writerow([p, frame, LINK_MTU, int(exceeds),
                        f"{m[0]:.6f}", f"{m[1]:.6f}", f"{m[2]:.6f}",
                        f"{m[3]:.6f}", f"{m[4]:.6f}", int(m[5]), oversized_packet_drops])
            status = "EXCEEDS MTU" if exceeds else "within MTU"
            print(f"  payload={p:>4d}B  frame={frame:>4d}B  [{status:^11s}]  "
                  f"throughput={m[0]:.3f} Mbps  loss={m[3]:.2f}%")

    print(f"\nExperiment 4 (MTU boundary) results written to: {output_csv}")


if __name__ == "__main__":
    main()
