#!/usr/bin/env python3
"""Experiment 1: UDP packet-size sweep at a 10 Mbps bottleneck.

Topology: 3 UDP senders -> Router1 -> [10 Mbps p2p, 5 ms] -> Router2 -> 802.11g -> Receiver.
Each sender offers 4 Mbps (12 Mbps total). Only the packet size changes.
Sweep: 128, 256, 512, 1024, 1500 B.
"""

import csv
from ns import ns

IP_UDP_HEADER_BYTES = 28
SIM_SECONDS = 30.0
APP_START_SECONDS = 1.0
ACTIVE_TIME = SIM_SECONDS - APP_START_SECONDS
NUM_SENDERS = 3
PER_SENDER_MBPS = 4.0
PACKET_SIZE_SWEEP_BYTES = [128, 256, 512, 1024, 1500]
BOTTLENECK_MBPS = 10
OUTPUT_CSV = "project/results/results_experiment1.csv"
SINK_PORT = 9103


def _node_container_from_node(node):
    container = ns.NodeContainer()
    container.Add(node)
    return container


def _configure_wifi(ap_node, sta_node):
    channel = ns.YansWifiChannelHelper.Default()
    phy = ns.YansWifiPhyHelper()
    phy.SetChannel(channel.Create())

    wifi = ns.WifiHelper()
    wifi.SetStandard(ns.WIFI_STANDARD_80211g)
    wifi.SetRemoteStationManager(
        "ns3::ConstantRateWifiManager",
        "DataMode",
        ns.StringValue("ErpOfdmRate24Mbps"),
        "ControlMode",
        ns.StringValue("ErpOfdmRate6Mbps"),
    )

    ssid = ns.Ssid("experiment-wifi")
    mac = ns.WifiMacHelper()

    ap_nodes = _node_container_from_node(ap_node)
    sta_nodes = _node_container_from_node(sta_node)

    mac.SetType("ns3::ApWifiMac", "Ssid", ns.SsidValue(ssid))
    ap_devs = wifi.Install(phy, mac, ap_nodes)

    mac.SetType(
        "ns3::StaWifiMac",
        "Ssid",
        ns.SsidValue(ssid),
        "ActiveProbing",
        ns.BooleanValue(False),
    )
    sta_devs = wifi.Install(phy, mac, sta_nodes)

    mobility = ns.MobilityHelper()
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel")
    mobility.Install(ap_nodes)
    mobility.Install(sta_nodes)

    wifi_devices = ns.NetDeviceContainer()
    wifi_devices.Add(ap_devs.Get(0))
    wifi_devices.Add(sta_devs.Get(0))
    return wifi_devices


def _collect_metrics(flow_helper, monitor, sink_port, packet_size, active_time):
    classifier = flow_helper.GetClassifier()

    tx_packets = 0
    rx_packets = 0
    rx_bytes = 0
    delay_sum_s = 0.0

    for flow_id, stats in monitor.GetFlowStats():
        tuple_info = classifier.FindFlow(flow_id)
        if tuple_info.destinationPort != sink_port:
            continue
        tx_packets += stats.txPackets
        rx_packets += stats.rxPackets
        rx_bytes += stats.rxBytes
        delay_sum_s += stats.delaySum.GetSeconds()

    throughput_mbps = (rx_bytes * 8.0 / active_time) / 1e6 if active_time > 0 else 0.0
    goodput_mbps = (rx_packets * packet_size * 8.0 / active_time) / 1e6 if active_time > 0 else 0.0
    delay_ms = (delay_sum_s * 1000.0 / rx_packets) if rx_packets > 0 else 0.0
    loss_pct = ((tx_packets - rx_packets) * 100.0 / tx_packets) if tx_packets > 0 else 0.0

    delivered_total_bytes = rx_packets * (packet_size + IP_UDP_HEADER_BYTES)
    header_bytes = rx_packets * IP_UDP_HEADER_BYTES
    overhead_ratio_pct = (header_bytes * 100.0 / delivered_total_bytes) if delivered_total_bytes > 0 else 0.0

    return {
        "throughput_mbps": throughput_mbps,
        "goodput_mbps": goodput_mbps,
        "avg_delay_ms": delay_ms,
        "packet_loss_rate_pct": loss_pct,
        "overhead_ratio_pct": overhead_ratio_pct,
    }


def run_one(packet_size_bytes, run_id):
    ns.RngSeedManager.SetRun(run_id)

    senders = ns.NodeContainer()
    senders.Create(NUM_SENDERS)
    routers = ns.NodeContainer()
    routers.Create(2)
    receiver = ns.NodeContainer()
    receiver.Create(1)

    csma_nodes = ns.NodeContainer()
    for i in range(senders.GetN()):
        csma_nodes.Add(senders.Get(i))
    csma_nodes.Add(routers.Get(0))

    csma = ns.CsmaHelper()
    csma.SetChannelAttribute("DataRate", ns.StringValue("100Mbps"))
    csma.SetChannelAttribute("Delay", ns.TimeValue(ns.MilliSeconds(1)))
    csma_devices = csma.Install(csma_nodes)

    bottleneck = ns.PointToPointHelper()
    bottleneck.SetDeviceAttribute("DataRate", ns.StringValue(f"{BOTTLENECK_MBPS}Mbps"))
    bottleneck.SetChannelAttribute("Delay", ns.TimeValue(ns.MilliSeconds(5)))
    bottleneck_devices = bottleneck.Install(routers.Get(0), routers.Get(1))

    wifi_devices = _configure_wifi(routers.Get(1), receiver.Get(0))

    internet = ns.InternetStackHelper()
    internet.Install(senders)
    internet.Install(routers)
    internet.Install(receiver)

    csma_ip = ns.Ipv4AddressHelper()
    csma_ip.SetBase(ns.Ipv4Address("10.30.1.0"), ns.Ipv4Mask("255.255.255.0"))
    csma_ip.Assign(csma_devices)

    bottleneck_ip = ns.Ipv4AddressHelper()
    bottleneck_ip.SetBase(ns.Ipv4Address("10.30.2.0"), ns.Ipv4Mask("255.255.255.0"))
    bottleneck_ip.Assign(bottleneck_devices)

    wifi_ip = ns.Ipv4AddressHelper()
    wifi_ip.SetBase(ns.Ipv4Address("10.30.3.0"), ns.Ipv4Mask("255.255.255.0"))
    wifi_interfaces = wifi_ip.Assign(wifi_devices)

    receiver_ip = wifi_interfaces.GetAddress(1)

    ns.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    sink = ns.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), SINK_PORT).ConvertTo(),
    )
    sink_apps = sink.Install(receiver)
    sink_apps.Start(ns.Seconds(0.0))
    sink_apps.Stop(ns.Seconds(SIM_SECONDS + 0.5))

    for sender_idx in range(NUM_SENDERS):
        remote = ns.InetSocketAddress(receiver_ip, SINK_PORT)
        onoff = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
        onoff.SetAttribute("OnTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
        onoff.SetAttribute("OffTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=0]"))
        onoff.SetAttribute("PacketSize", ns.UintegerValue(packet_size_bytes))
        onoff.SetAttribute("DataRate", ns.DataRateValue(ns.DataRate(int(PER_SENDER_MBPS * 1e6))))

        sender_apps = onoff.Install(_node_container_from_node(senders.Get(sender_idx)))
        sender_apps.Start(ns.Seconds(APP_START_SECONDS + 0.02 * sender_idx))
        sender_apps.Stop(ns.Seconds(SIM_SECONDS))

    flow_helper = ns.FlowMonitorHelper()
    monitor = flow_helper.InstallAll()

    ns.Simulator.Stop(ns.Seconds(SIM_SECONDS + 1.0))
    ns.Simulator.Run()
    monitor.CheckForLostPackets()

    metrics = _collect_metrics(flow_helper, monitor, SINK_PORT, packet_size_bytes, ACTIVE_TIME)
    ns.Simulator.Destroy()
    return metrics


def main():
    ns.RngSeedManager.SetSeed(206)

    rows = []
    run_id = 1

    for packet_size_bytes in PACKET_SIZE_SWEEP_BYTES:
        metrics = run_one(packet_size_bytes, run_id)
        rows.append(
            {
                "link_type": "wireless",
                "bottleneck_mbps": BOTTLENECK_MBPS,
                "packet_size_bytes": packet_size_bytes,
                "active_senders": NUM_SENDERS,
                "offered_load_mbps": NUM_SENDERS * PER_SENDER_MBPS,
                **metrics,
            }
        )
        run_id += 1

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "link_type",
            "bottleneck_mbps",
            "packet_size_bytes",
            "active_senders",
            "offered_load_mbps",
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "packet_loss_rate_pct",
            "overhead_ratio_pct",
        ])
        for row in rows:
            writer.writerow([
                row["link_type"],
                row["bottleneck_mbps"],
                row["packet_size_bytes"],
                row["active_senders"],
                f"{row['offered_load_mbps']:.3f}",
                f"{row['throughput_mbps']:.6f}",
                f"{row['goodput_mbps']:.6f}",
                f"{row['avg_delay_ms']:.6f}",
                f"{row['packet_loss_rate_pct']:.6f}",
                f"{row['overhead_ratio_pct']:.6f}",
            ])

    print("\nExperiment 1 Summary: Packet Size Sweep (10 Mbps Bottleneck)")
    print("packet_size | throughput_mbps | goodput_mbps | delay_ms | loss_pct | overhead_pct")
    for row in rows:
        print(
            f"{row['packet_size_bytes']:>11} | "
            f"{row['throughput_mbps']:>15.3f} | "
            f"{row['goodput_mbps']:>12.3f} | "
            f"{row['avg_delay_ms']:>8.3f} | "
            f"{row['packet_loss_rate_pct']:>8.3f} | "
            f"{row['overhead_ratio_pct']:>12.3f}"
        )

    print(f"\nCSV written: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
