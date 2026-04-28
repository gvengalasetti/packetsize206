#!/usr/bin/env python3
"""Experiment 6: Link MTU sweep with fixed 1000-byte payload on multi-hop topology.

Topology:
Sender1 --+
Sender2 --+-- Router1 --[bottleneck p2p]-- Router2 --[802.11g WiFi]-- Receiver
Sender3 --+

Rationale: This experiment fixes the application payload at 1000 bytes (1028 bytes
on the wire including IP+UDP headers) and sweeps the WiFi link MTU from 512 B
up to 1500 B. This models the real-world scenario where an operator tunes the
wireless link MTU (e.g., to accommodate VXLAN overhead, PPPoE headers, or
different hardware limits). The crossover occurs at MTU = 1028 B: below it every
packet is dropped by the WiFi layer; at or above it packets are delivered
without loss. This demonstrates that MTU provisioning is a binary on/off knob
for a given traffic class.
"""
import csv
from ns import ns

IP_UDP_HEADER_BYTES = 28
SIM_SECONDS = 30.0
APP_START_SECONDS = 1.0
ACTIVE_TIME = SIM_SECONDS - APP_START_SECONDS

PAYLOAD_SIZE = 1000
FRAME_SIZE = PAYLOAD_SIZE + IP_UDP_HEADER_BYTES
LINK_MTU_VALUES = [512, 800, 1024, FRAME_SIZE, 1200, 1500]

BOTTLENECK_MBPS = 10
NUM_SENDERS = 3
PER_SENDER_MBPS = 8.0 / NUM_SENDERS
SINK_PORT = 9206
ROUTER_QUEUE_MAX_SIZE = "100p"


def _node_container_from_node(node):
    container = ns.NodeContainer()
    container.Add(node)
    return container


def _configure_wifi(ap_node, sta_node, wifi_mtu):
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

    for i in range(wifi_devices.GetN()):
        wifi_devices.Get(i).SetMtu(wifi_mtu)

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
        tx_packets += int(stats.txPackets)
        rx_packets += int(stats.rxPackets)
        rx_bytes += int(stats.rxBytes)
        delay_sum_s += stats.delaySum.GetSeconds()

    throughput_mbps = (rx_bytes * 8.0 / active_time) / 1e6 if active_time > 0 else 0.0
    goodput_mbps = (rx_packets * packet_size * 8.0 / active_time) / 1e6 if active_time > 0 else 0.0
    delay_ms = (delay_sum_s * 1000.0 / rx_packets) if rx_packets > 0 else 0.0
    loss_pct = ((tx_packets - rx_packets) * 100.0 / tx_packets) if tx_packets > 0 else 0.0

    total_bytes = rx_packets * (packet_size + IP_UDP_HEADER_BYTES)
    overhead_pct = (rx_packets * IP_UDP_HEADER_BYTES * 100.0 / total_bytes) if total_bytes > 0 else 0.0
    flowmonitor_drop_events = sum(int(d) for d in stats.packetsDropped)

    return (
        throughput_mbps,
        goodput_mbps,
        delay_ms,
        loss_pct,
        overhead_pct,
        flowmonitor_drop_events,
        tx_packets,
        rx_packets,
    )


def run_one(wifi_mtu, run_id):
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
    csma.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", ns.StringValue(ROUTER_QUEUE_MAX_SIZE))
    csma_devices = csma.Install(csma_nodes)

    p2p = ns.PointToPointHelper()
    p2p.SetDeviceAttribute("DataRate", ns.StringValue(f"{BOTTLENECK_MBPS}Mbps"))
    p2p.SetChannelAttribute("Delay", ns.TimeValue(ns.MilliSeconds(5)))
    p2p.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", ns.StringValue(ROUTER_QUEUE_MAX_SIZE))
    bottleneck_devices = p2p.Install(routers.Get(0), routers.Get(1))

    wifi_devices = _configure_wifi(routers.Get(1), receiver.Get(0), wifi_mtu)

    internet = ns.InternetStackHelper()
    internet.Install(senders)
    internet.Install(routers)
    internet.Install(receiver)

    csma_ip = ns.Ipv4AddressHelper()
    csma_ip.SetBase(ns.Ipv4Address("10.60.1.0"), ns.Ipv4Mask("255.255.255.0"))
    csma_ip.Assign(csma_devices)

    bottleneck_ip = ns.Ipv4AddressHelper()
    bottleneck_ip.SetBase(ns.Ipv4Address("10.60.2.0"), ns.Ipv4Mask("255.255.255.0"))
    bottleneck_ip.Assign(bottleneck_devices)

    wifi_ip = ns.Ipv4AddressHelper()
    wifi_ip.SetBase(ns.Ipv4Address("10.60.3.0"), ns.Ipv4Mask("255.255.255.0"))
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

    remote = ns.InetSocketAddress(receiver_ip, SINK_PORT)
    onoff = ns.OnOffHelper("ns3::UdpSocketFactory", remote.ConvertTo())
    onoff.SetAttribute("DataRate", ns.DataRateValue(ns.DataRate(int(PER_SENDER_MBPS * 1e6))))
    onoff.SetAttribute("PacketSize", ns.UintegerValue(PAYLOAD_SIZE))
    onoff.SetAttribute("OnTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
    onoff.SetAttribute("OffTime", ns.StringValue("ns3::ConstantRandomVariable[Constant=0]"))

    for sender_idx in range(NUM_SENDERS):
        apps = onoff.Install(_node_container_from_node(senders.Get(sender_idx)))
        apps.Start(ns.Seconds(APP_START_SECONDS + 0.02 * sender_idx))
        apps.Stop(ns.Seconds(SIM_SECONDS))

    flow = ns.FlowMonitorHelper()
    monitor = flow.InstallAll()

    ns.Simulator.Stop(ns.Seconds(SIM_SECONDS + 1.0))
    ns.Simulator.Run()
    monitor.CheckForLostPackets()

    metrics = _collect_metrics(flow, monitor, SINK_PORT, PAYLOAD_SIZE, ACTIVE_TIME)

    ns.Simulator.Destroy()
    return metrics


def main():
    ns.RngSeedManager.SetSeed(206)
    output_csv = "project/results/experiment4_mtu_link_mtu.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "link_mtu_bytes",
            "frame_bytes",
            "payload_bytes",
            "mtu_sufficient",
            "throughput_mbps",
            "goodput_mbps",
            "avg_delay_ms",
            "packet_loss_rate_pct",
            "overhead_ratio_pct",
            "flowmonitor_drop_events",
            "oversized_packet_drops",
        ])

        for run_id, mtu in enumerate(LINK_MTU_VALUES, start=1):
            sufficient = int(mtu >= FRAME_SIZE)
            m = run_one(mtu, run_id)
            oversized_packet_drops = 0
            if not sufficient:
                oversized_packet_drops = max(0, m[6] - m[7])
            w.writerow([mtu, FRAME_SIZE, PAYLOAD_SIZE, sufficient,
                        f"{m[0]:.6f}", f"{m[1]:.6f}", f"{m[2]:.6f}",
                        f"{m[3]:.6f}", f"{m[4]:.6f}", int(m[5]), oversized_packet_drops])
            status = "OK  " if sufficient else "DROP"
            print(f"  link_mtu={mtu:>4d}B  frame={FRAME_SIZE}B  [{status}]  "
                  f"throughput={m[0]:.3f} Mbps  loss={m[3]:.2f}%")

    print(f"\nExperiment 6 (WiFi MTU variation) results written to: {output_csv}")


if __name__ == "__main__":
    main()
