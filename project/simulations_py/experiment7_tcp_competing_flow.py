#!/usr/bin/env python3
"""Experiment 7: TCP competing flow with packet-size sweep.

Topology:
Sender1 --+
Sender2 --+-- Router1 --[bottleneck p2p]-- Router2 --[802.11g WiFi]-- Receiver
Sender3 --+
Sender4 --+

Traffic model:
- Sender1..Sender3: UDP OnOff flows competing at the bottleneck.
- Sender4: TCP BulkSend flow sharing the same path.
- Packet sizes swept: [128, 256, 512, 1024, 1500] bytes.

Queueing/fairness note:
- Packet-based DropTail queues can bias service toward larger packets in terms of
  bytes dequeued per packet event; this can affect fairness for heterogeneous packet sizes.
"""

import csv
from ns import ns

UDP_IP_HEADER_BYTES = 28
TCP_IP_HEADER_BYTES = 40
SIM_SECONDS = 30.0
APP_START_SECONDS = 1.0
ACTIVE_TIME = SIM_SECONDS - APP_START_SECONDS
PACKET_SIZE_SWEEP_BYTES = [128, 256, 512, 1024, 1500]
UDP_SENDERS = 3
UDP_PER_SENDER_MBPS = 4.0
BOTTLENECK_MBPS = 10
ROUTER_QUEUE_MAX_SIZE = "100p"
OUTPUT_CSV = "project/results/results_experiment7.csv"
UDP_SINK_PORT = 9207
TCP_SINK_PORT = 9208


def _node_container_from_node(node):
    container = ns.NodeContainer()
    container.Add(node)
    return container


def _configure_wifi(ap_node, sta_node):
    # 802.11g uses DCF medium access, so contention/backoff affects last-hop latency.
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


def _collect_group_metrics(flow_helper, monitor, dst_port, protocol, packet_size, header_bytes):
    classifier = flow_helper.GetClassifier()

    tx_packets = 0
    rx_packets = 0
    rx_bytes = 0
    drop_events = 0

    for flow_id, stats in monitor.GetFlowStats():
        tuple_info = classifier.FindFlow(flow_id)
        if tuple_info.destinationPort != dst_port or int(tuple_info.protocol) != int(protocol):
            continue
        tx_packets += int(stats.txPackets)
        rx_packets += int(stats.rxPackets)
        rx_bytes += int(stats.rxBytes)
        drop_events += sum(int(d) for d in stats.packetsDropped)

    goodput_mbps = (rx_packets * packet_size * 8.0 / ACTIVE_TIME) / 1e6 if ACTIVE_TIME > 0 else 0.0
    loss_pct = ((tx_packets - rx_packets) * 100.0 / tx_packets) if tx_packets > 0 else 0.0
    delivered_total_bytes = rx_packets * (packet_size + header_bytes)
    overhead_ratio_pct = (rx_packets * header_bytes * 100.0 / delivered_total_bytes) if delivered_total_bytes > 0 else 0.0

    return {
        "goodput_mbps": goodput_mbps,
        "overhead_ratio_pct": overhead_ratio_pct,
        "fragmentation_effect_flowmonitor_drops": drop_events,
        "packet_loss_rate_pct": loss_pct,
        "rx_bytes": rx_bytes,
    }


def run_one(packet_size_bytes, run_id):
    ns.RngSeedManager.SetRun(run_id)

    senders = ns.NodeContainer()
    senders.Create(4)  # 3 UDP senders + 1 TCP sender
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
    csma.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", ns.StringValue(ROUTER_QUEUE_MAX_SIZE))
    # Router1 access-side DropTail buffer depth controls when congestion drops begin.
    csma_devices = csma.Install(csma_nodes)

    bottleneck = ns.PointToPointHelper()
    bottleneck.SetDeviceAttribute("DataRate", ns.StringValue(f"{BOTTLENECK_MBPS}Mbps"))
    bottleneck.SetChannelAttribute("Delay", ns.TimeValue(ns.MilliSeconds(5)))
    bottleneck.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", ns.StringValue(ROUTER_QUEUE_MAX_SIZE))
    # Router1/Router2 bottleneck DropTail buffer: smaller buffers drop earlier with lower delay,
    # larger buffers defer drops but permit larger queueing delay before loss onset.
    bottleneck_devices = bottleneck.Install(routers.Get(0), routers.Get(1))

    wifi_devices = _configure_wifi(routers.Get(1), receiver.Get(0))

    internet = ns.InternetStackHelper()
    internet.Install(senders)
    internet.Install(routers)
    internet.Install(receiver)

    csma_ip = ns.Ipv4AddressHelper()
    csma_ip.SetBase(ns.Ipv4Address("10.70.1.0"), ns.Ipv4Mask("255.255.255.0"))
    csma_ip.Assign(csma_devices)

    bottleneck_ip = ns.Ipv4AddressHelper()
    bottleneck_ip.SetBase(ns.Ipv4Address("10.70.2.0"), ns.Ipv4Mask("255.255.255.0"))
    bottleneck_ip.Assign(bottleneck_devices)

    wifi_ip = ns.Ipv4AddressHelper()
    wifi_ip.SetBase(ns.Ipv4Address("10.70.3.0"), ns.Ipv4Mask("255.255.255.0"))
    wifi_interfaces = wifi_ip.Assign(wifi_devices)
    receiver_ip = wifi_interfaces.GetAddress(1)

    ns.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    udp_sink = ns.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), UDP_SINK_PORT).ConvertTo(),
    )
    udp_sink_apps = udp_sink.Install(receiver)
    udp_sink_apps.Start(ns.Seconds(0.0))
    udp_sink_apps.Stop(ns.Seconds(SIM_SECONDS + 0.5))

    tcp_sink = ns.PacketSinkHelper(
        "ns3::TcpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), TCP_SINK_PORT).ConvertTo(),
    )
    tcp_sink_apps = tcp_sink.Install(receiver)
    tcp_sink_apps.Start(ns.Seconds(0.0))
    tcp_sink_apps.Stop(ns.Seconds(SIM_SECONDS + 0.5))

    for sender_idx in range(UDP_SENDERS):
        remote = ns.InetSocketAddress(receiver_ip, UDP_SINK_PORT)
        onoff = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
        onoff.SetAttribute("OnTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
        onoff.SetAttribute("OffTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=0]"))
        onoff.SetAttribute("PacketSize", ns.UintegerValue(packet_size_bytes))
        onoff.SetAttribute("DataRate", ns.DataRateValue(ns.DataRate(int(UDP_PER_SENDER_MBPS * 1e6))))

        udp_apps = onoff.Install(_node_container_from_node(senders.Get(sender_idx)))
        udp_apps.Start(ns.Seconds(APP_START_SECONDS + 0.02 * sender_idx))
        udp_apps.Stop(ns.Seconds(SIM_SECONDS))

    tcp_remote = ns.InetSocketAddress(receiver_ip, TCP_SINK_PORT)
    bulk = ns.BulkSendHelper("ns3::TcpSocketFactory", tcp_remote.ConvertTo())
    bulk.SetAttribute("SendSize", ns.UintegerValue(packet_size_bytes))
    bulk.SetAttribute("MaxBytes", ns.UintegerValue(0))
    tcp_apps = bulk.Install(_node_container_from_node(senders.Get(3)))
    tcp_apps.Start(ns.Seconds(APP_START_SECONDS + 0.1))
    tcp_apps.Stop(ns.Seconds(SIM_SECONDS))

    flow_helper = ns.FlowMonitorHelper()
    monitor = flow_helper.InstallAll()

    ns.Simulator.Stop(ns.Seconds(SIM_SECONDS + 1.0))
    ns.Simulator.Run()
    monitor.CheckForLostPackets()

    udp_metrics = _collect_group_metrics(flow_helper, monitor, UDP_SINK_PORT, 17, packet_size_bytes, UDP_IP_HEADER_BYTES)
    tcp_metrics = _collect_group_metrics(flow_helper, monitor, TCP_SINK_PORT, 6, packet_size_bytes, TCP_IP_HEADER_BYTES)

    ns.Simulator.Destroy()
    return udp_metrics, tcp_metrics


def main():
    ns.RngSeedManager.SetSeed(206)

    rows = []
    for run_id, packet_size in enumerate(PACKET_SIZE_SWEEP_BYTES, start=1):
        udp_metrics, tcp_metrics = run_one(packet_size, run_id)
        rows.append(
            {
                "experiment": "experiment7_tcp_competing_flow",
                "packet_size_bytes": packet_size,
                "udp_goodput_mbps": udp_metrics["goodput_mbps"],
                "udp_overhead_ratio_pct": udp_metrics["overhead_ratio_pct"],
                "udp_fragmentation_effect_flowmonitor_drops": udp_metrics[
                    "fragmentation_effect_flowmonitor_drops"
                ],
                "udp_packet_loss_rate_pct": udp_metrics["packet_loss_rate_pct"],
                "tcp_goodput_mbps": tcp_metrics["goodput_mbps"],
                "tcp_overhead_ratio_pct": tcp_metrics["overhead_ratio_pct"],
                "tcp_fragmentation_effect_flowmonitor_drops": tcp_metrics[
                    "fragmentation_effect_flowmonitor_drops"
                ],
                "tcp_packet_loss_rate_pct": tcp_metrics["packet_loss_rate_pct"],
            }
        )

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "experiment",
                "packet_size_bytes",
                "udp_goodput_mbps",
                "udp_overhead_ratio_pct",
                "udp_fragmentation_effect_flowmonitor_drops",
                "udp_packet_loss_rate_pct",
                "tcp_goodput_mbps",
                "tcp_overhead_ratio_pct",
                "tcp_fragmentation_effect_flowmonitor_drops",
                "tcp_packet_loss_rate_pct",
            ]
        )

        for row in rows:
            w.writerow(
                [
                    row["experiment"],
                    row["packet_size_bytes"],
                    f"{row['udp_goodput_mbps']:.6f}",
                    f"{row['udp_overhead_ratio_pct']:.6f}",
                    int(row["udp_fragmentation_effect_flowmonitor_drops"]),
                    f"{row['udp_packet_loss_rate_pct']:.6f}",
                    f"{row['tcp_goodput_mbps']:.6f}",
                    f"{row['tcp_overhead_ratio_pct']:.6f}",
                    int(row["tcp_fragmentation_effect_flowmonitor_drops"]),
                    f"{row['tcp_packet_loss_rate_pct']:.6f}",
                ]
            )

    print("\nExperiment 7 Summary (TCP competing with UDP)")
    print("pkt | udp_goodput | udp_loss | tcp_goodput | tcp_loss")
    for row in rows:
        print(
            f"{row['packet_size_bytes']:>4} | "
            f"{row['udp_goodput_mbps']:>11.3f} | "
            f"{row['udp_packet_loss_rate_pct']:>8.3f} | "
            f"{row['tcp_goodput_mbps']:>11.3f} | "
            f"{row['tcp_packet_loss_rate_pct']:>8.3f}"
        )

    print(f"\nCSV written: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
