#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <fstream>
#include <iomanip>
#include <string>

using namespace ns3;

namespace
{
constexpr uint32_t kIpUdpHeaderBytes = 28;

struct RunMetrics
{
    double throughputMbps{0.0};
    double goodputMbps{0.0};
    double avgDelayMs{0.0};
    double lossRatePct{0.0};
    double overheadRatioPct{0.0};
};

RunMetrics
ComputeMetrics(const FlowMonitor::FlowStats& stats, uint32_t packetSize, double simSeconds)
{
    RunMetrics m;

    if (simSeconds > 0.0)
    {
        m.throughputMbps = static_cast<double>(stats.rxBytes) * 8.0 / simSeconds / 1e6;
        m.goodputMbps = static_cast<double>(stats.rxPackets) * packetSize * 8.0 / simSeconds / 1e6;
    }

    if (stats.rxPackets > 0)
    {
        m.avgDelayMs = stats.delaySum.GetSeconds() * 1000.0 / static_cast<double>(stats.rxPackets);
        const double totalBytes = static_cast<double>(stats.rxPackets) * (packetSize + kIpUdpHeaderBytes);
        const double headerBytes = static_cast<double>(stats.rxPackets) * kIpUdpHeaderBytes;
        m.overheadRatioPct = (totalBytes > 0.0) ? (headerBytes / totalBytes) * 100.0 : 0.0;
    }

    if (stats.txPackets > 0)
    {
        m.lossRatePct = static_cast<double>(stats.txPackets - stats.rxPackets) * 100.0 /
                        static_cast<double>(stats.txPackets);
    }

    return m;
}
} // namespace

int
main(int argc, char* argv[])
{
    uint32_t packetSize = 512;
    double simSeconds = 10.0;
    std::string outputCsv = "project/results/baseline.csv";

    CommandLine cmd(__FILE__);
    cmd.AddValue("packetSize", "Application payload size in bytes", packetSize);
    cmd.AddValue("simSeconds", "Simulation duration in seconds", simSeconds);
    cmd.AddValue("outputCsv", "Output CSV file path", outputCsv);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(206);
    RngSeedManager::SetRun(1);

    NodeContainer nodes;
    nodes.Create(2);

    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));

    NetDeviceContainer devices = p2p.Install(nodes);

    InternetStackHelper internet;
    internet.Install(nodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign(devices);

    uint16_t port = 9000;
    PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), port));
    ApplicationContainer sinkApp = sinkHelper.Install(nodes.Get(1));
    sinkApp.Start(Seconds(0.0));
    sinkApp.Stop(Seconds(simSeconds + 0.5));

    OnOffHelper onoff("ns3::UdpSocketFactory", Address(InetSocketAddress(interfaces.GetAddress(1), port)));
    onoff.SetAttribute("DataRate", DataRateValue(DataRate("8Mbps")));
    onoff.SetAttribute("PacketSize", UintegerValue(packetSize));
    onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));

    ApplicationContainer senderApp = onoff.Install(nodes.Get(0));
    senderApp.Start(Seconds(1.0));
    senderApp.Stop(Seconds(simSeconds));

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();

    Simulator::Stop(Seconds(simSeconds + 1.0));
    Simulator::Run();

    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowHelper.GetClassifier());
    const auto statsMap = monitor->GetFlowStats();

    FlowMonitor::FlowStats flowStats;
    bool foundFlow = false;

    for (const auto& kv : statsMap)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(kv.first);
        if (t.destinationPort == port)
        {
            flowStats = kv.second;
            foundFlow = true;
            break;
        }
    }

    Simulator::Destroy();

    if (!foundFlow)
    {
        NS_LOG_UNCOND("No matching flow was found in FlowMonitor statistics.");
        return 1;
    }

    RunMetrics m = ComputeMetrics(flowStats, packetSize, simSeconds - 1.0);

    std::ofstream out(outputCsv, std::ios::trunc);
    if (!out)
    {
        NS_LOG_UNCOND("Failed to open output CSV: " << outputCsv);
        return 1;
    }

    out << "scenario,bandwidth_mbps,packet_size_bytes,throughput_mbps,goodput_mbps,avg_delay_ms,"
           "packet_loss_rate_pct,overhead_ratio_pct\n";
    out << std::fixed << std::setprecision(6);
    out << "baseline,10," << packetSize << ',' << m.throughputMbps << ',' << m.goodputMbps << ','
        << m.avgDelayMs << ',' << m.lossRatePct << ',' << m.overheadRatioPct << '\n';

    NS_LOG_UNCOND("Baseline results written to: " << outputCsv);
    return 0;
}
