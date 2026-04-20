#!/usr/bin/env python3
import csv
from ns import ns

IP_UDP_HEADER_BYTES = 28
PACKET_SIZES = [256, 1024]


def aggregate_metrics(monitor, classifier, sink_port, packet_size, active_time):
    rx_bytes = 0
    rx_packets = 0
    tx_packets = 0
    delay_s = 0.0
    jitter_s = 0.0
    flow_drop_sum = 0

    for fid, st in monitor.GetFlowStats():
        t = classifier.FindFlow(fid)
        if t.destinationPort != sink_port:
            continue
        rx_bytes += st.rxBytes
        rx_packets += st.rxPackets
        tx_packets += st.txPackets
        delay_s += st.delaySum.GetSeconds()
        jitter_s += st.jitterSum.GetSeconds()
        for d in st.packetsDropped:
            flow_drop_sum += d

    throughput = (rx_bytes * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    goodput = (rx_packets * packet_size * 8.0) / active_time / 1e6 if active_time > 0 else 0.0
    delay_ms = (delay_s * 1000.0 / rx_packets) if rx_packets > 0 else 0.0
    jitter_ms = (jitter_s * 1000.0 / (rx_packets - 1)) if rx_packets > 1 else 0.0
    loss_pct = ((tx_packets - rx_packets) * 100.0 / tx_packets) if tx_packets > 0 else 0.0

    total_bytes = rx_packets * (packet_size + IP_UDP_HEADER_BYTES)
    overhead_pct = (rx_packets * IP_UDP_HEADER_BYTES * 100.0 / total_bytes) if total_bytes > 0 else 0.0

    return throughput, goodput, delay_ms, jitter_ms, loss_pct, flow_drop_sum, overhead_pct


def run_one(congested, packet_size, run_id, sim_seconds=10.0):
    ns.RngSeedManager.SetRun(run_id)

    num_sources = 3 if congested else 1
    sink_port = 9002
    per_source_rate_mbps = 4.0

    sources = ns.NodeContainer()
    sources.Create(num_sources)

    routers = ns.NodeContainer()
    routers.Create(2)

    receiver = ns.NodeContainer()
    receiver.Create(1)

    edge = ns.PointToPointHelper()
    edge.SetDeviceAttribute("DataRate", ns.StringValue("100Mbps"))
    edge.SetChannelAttribute("Delay", ns.StringValue("1ms"))

    bottleneck = ns.PointToPointHelper()
    bottleneck.SetDeviceAttribute("DataRate", ns.StringValue("5Mbps"))
    bottleneck.SetChannelAttribute("Delay", ns.StringValue("10ms"))

    src_dev = []
    for i in range(num_sources):
        src_dev.append(edge.Install(sources.Get(i), routers.Get(0)))

    bottleneck_dev = bottleneck.Install(routers.Get(0), routers.Get(1))
    recv_dev = edge.Install(routers.Get(1), receiver.Get(0))

    internet = ns.InternetStackHelper()
    internet.Install(sources)
    internet.Install(routers)
    internet.Install(receiver)

    for i in range(num_sources):
        ip = ns.Ipv4AddressHelper()
        subnet = f"10.1.{i + 1}.0"
        ip.SetBase(ns.Ipv4Address(subnet), ns.Ipv4Mask("255.255.255.0"))
        ip.Assign(src_dev[i])

    ip_b = ns.Ipv4AddressHelper()
    ip_b.SetBase(ns.Ipv4Address("10.1.50.0"), ns.Ipv4Mask("255.255.255.0"))
    ip_b.Assign(bottleneck_dev)

    ip_r = ns.Ipv4AddressHelper()
    ip_r.SetBase(ns.Ipv4Address("10.1.60.0"), ns.Ipv4Mask("255.255.255.0"))
    recv_if = ip_r.Assign(recv_dev)

    ns.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    sink = ns.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), sink_port).ConvertTo(),
    )
    sink_apps = sink.Install(receiver)
    sink_apps.Start(ns.Seconds(0.0))
    sink_apps.Stop(ns.Seconds(sim_seconds + 0.5))

    per_source_bps = int(per_source_rate_mbps * 1e6)
    for i in range(num_sources):
        remote = ns.InetSocketAddress(recv_if.GetAddress(1), sink_port)
        onoff = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
        onoff.SetAttribute("DataRate", ns.DataRateValue(ns.DataRate(per_source_bps)))
        onoff.SetAttribute("PacketSize", ns.UintegerValue(packet_size))
        onoff.SetAttribute("OnTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
        onoff.SetAttribute("OffTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=0]"))
        app = onoff.Install(ns.NodeContainer(sources.Get(i)))
        app.Start(ns.Seconds(1.0 + 0.05 * i))
        app.Stop(ns.Seconds(sim_seconds))

    flow = ns.FlowMonitorHelper()
    monitor = flow.InstallAll()

    ns.Simulator.Stop(ns.Seconds(sim_seconds + 1.0))
    ns.Simulator.Run()
    monitor.CheckForLostPackets()

    classifier = flow.GetClassifier()
    metrics = aggregate_metrics(monitor, classifier, sink_port, packet_size, sim_seconds - 1.0)

    ns.Simulator.Destroy()
    return metrics


def main():
    ns.RngSeedManager.SetSeed(206)
    output_csv = "project/results/experiment3_congestion.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "mode",
            "packet_size_bytes",
            "num_senders",
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "jitter_ms",
            "packet_loss_rate_pct",
            "queue_drops",
            "overhead_ratio_pct",
        ])

        run_id = 1
        for p in PACKET_SIZES:
            for congested in [False, True]:
                m = run_one(congested, p, run_id)
                run_id += 1
                w.writerow([
                    "congested" if congested else "no_congestion",
                    p,
                    3 if congested else 1,
                    f"{m[0]:.6f}",
                    f"{m[1]:.6f}",
                    f"{m[2]:.6f}",
                    f"{m[3]:.6f}",
                    f"{m[4]:.6f}",
                    int(m[5]),
                    f"{m[6]:.6f}",
                ])

    print(f"Experiment 3 results written to: {output_csv}")


if __name__ == "__main__":
    main()
