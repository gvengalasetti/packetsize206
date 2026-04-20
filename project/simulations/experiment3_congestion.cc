#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

namespace
{
constexpr uint32_t kIpUdpHeaderBytes = 28;
static uint64_t gQueueDrops = 0;

void
CountQueueDrop(Ptr<const Packet>)
{
    ++gQueueDrops;
}

struct Metrics
{
    double throughputMbps{0.0};
    double goodputMbps{0.0};
    double delayMs{0.0};
    double jitterMs{0.0};
    double lossPct{0.0};
    double overheadPct{0.0};
    uint64_t queueDrops{0};
};

Metrics
RunCongestionScenario(bool congested, uint32_t packetSize, double simSeconds, uint32_t runNumber)
{
    RngSeedManager::SetRun(runNumber);
    gQueueDrops = 0;

    const uint32_t numSources = congested ? 3 : 1;
    const double perSourceRateMbps = 4.0;

    NodeContainer sources;
    sources.Create(numSources);

    NodeContainer routers;
    routers.Create(2);

    NodeContainer receiver;
    receiver.Create(1);

    PointToPointHelper edgeLink;
    edgeLink.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    edgeLink.SetChannelAttribute("Delay", StringValue("1ms"));

    PointToPointHelper bottleneck;
    bottleneck.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    bottleneck.SetChannelAttribute("Delay", StringValue("10ms"));

    NetDeviceContainer bottleneckDevices = bottleneck.Install(routers.Get(0), routers.Get(1));

    std::vector<NetDeviceContainer> sourceDevices;
    sourceDevices.reserve(numSources);
    for (uint32_t i = 0; i < numSources; ++i)
    {
        sourceDevices.push_back(edgeLink.Install(sources.Get(i), routers.Get(0)));
    }
    NetDeviceContainer receiverDevices = edgeLink.Install(routers.Get(1), receiver.Get(0));

    Ptr<PointToPointNetDevice> bottleneckDevice = DynamicCast<PointToPointNetDevice>(bottleneckDevices.Get(0));
    if (bottleneckDevice && bottleneckDevice->GetQueue())
    {
        bottleneckDevice->GetQueue()->TraceConnectWithoutContext("Drop", MakeCallback(&CountQueueDrop));
    }

    InternetStackHelper internet;
    internet.Install(sources);
    internet.Install(routers);
    internet.Install(receiver);

    std::vector<Ipv4InterfaceContainer> sourceIfaces;
    sourceIfaces.reserve(numSources);
    for (uint32_t i = 0; i < numSources; ++i)
    {
        Ipv4AddressHelper ip;
        std::ostringstream subnet;
        subnet << "10.1." << (i + 1) << ".0";
        ip.SetBase(subnet.str().c_str(), "255.255.255.0");
        sourceIfaces.push_back(ip.Assign(sourceDevices[i]));
    }

    Ipv4AddressHelper bottleneckIp;
    bottleneckIp.SetBase("10.1.50.0", "255.255.255.0");
    bottleneckIp.Assign(bottleneckDevices);

    Ipv4AddressHelper recvIp;
    recvIp.SetBase("10.1.60.0", "255.255.255.0");
    Ipv4InterfaceContainer recvIfaces = recvIp.Assign(receiverDevices);

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    constexpr uint16_t sinkPort = 9002;
    PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), sinkPort));
    auto sinkApps = sinkHelper.Install(receiver.Get(0));
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(simSeconds + 0.5));

    const uint64_t perSourceRateBps = static_cast<uint64_t>(perSourceRateMbps * 1e6);
    for (uint32_t i = 0; i < numSources; ++i)
    {
        OnOffHelper onoff("ns3::UdpSocketFactory",
                          Address(InetSocketAddress(recvIfaces.GetAddress(1), sinkPort)));
        onoff.SetAttribute("DataRate", DataRateValue(DataRate(perSourceRateBps)));
        onoff.SetAttribute("PacketSize", UintegerValue(packetSize));
        onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
        onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));

        auto apps = onoff.Install(sources.Get(i));
        apps.Start(Seconds(1.0 + 0.05 * i));
        apps.Stop(Seconds(simSeconds));
    }

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();

    Simulator::Stop(Seconds(simSeconds + 1.0));
    Simulator::Run();

    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowHelper.GetClassifier());

    uint64_t totalRxBytes = 0;
    uint64_t totalRxPackets = 0;
    uint64_t totalTxPackets = 0;
    double totalDelaySeconds = 0.0;
    double totalJitterSeconds = 0.0;

    for (const auto& kv : monitor->GetFlowStats())
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(kv.first);
        if (t.destinationPort != sinkPort)
        {
            continue;
        }

        const auto& s = kv.second;
        totalRxBytes += s.rxBytes;
        totalRxPackets += s.rxPackets;
        totalTxPackets += s.txPackets;
        totalDelaySeconds += s.delaySum.GetSeconds();
        totalJitterSeconds += s.jitterSum.GetSeconds();
    }

    Simulator::Destroy();

    Metrics m;
    const double activeTime = simSeconds - 1.0;
    if (activeTime > 0.0)
    {
        m.throughputMbps = static_cast<double>(totalRxBytes) * 8.0 / activeTime / 1e6;
        m.goodputMbps = static_cast<double>(totalRxPackets) * packetSize * 8.0 / activeTime / 1e6;
    }

    if (totalRxPackets > 0)
    {
        m.delayMs = totalDelaySeconds * 1000.0 / static_cast<double>(totalRxPackets);
        const double jitterDivisor = (totalRxPackets > 1) ? static_cast<double>(totalRxPackets - 1) : 1.0;
        m.jitterMs = totalJitterSeconds * 1000.0 / jitterDivisor;

        const double totalBytes = static_cast<double>(totalRxPackets) * (packetSize + kIpUdpHeaderBytes);
        const double headerBytes = static_cast<double>(totalRxPackets) * kIpUdpHeaderBytes;
        m.overheadPct = (totalBytes > 0.0) ? (headerBytes * 100.0 / totalBytes) : 0.0;
    }

    if (totalTxPackets > 0)
    {
        m.lossPct = static_cast<double>(totalTxPackets - totalRxPackets) * 100.0 /
                    static_cast<double>(totalTxPackets);
    }
    m.queueDrops = gQueueDrops;

    return m;
}
} // namespace

int
main(int argc, char* argv[])
{
    double simSeconds = 10.0;
    std::string outputCsv = "project/results/experiment3_congestion.csv";

    CommandLine cmd(__FILE__);
    cmd.AddValue("simSeconds", "Simulation duration in seconds", simSeconds);
    cmd.AddValue("outputCsv", "Output CSV file path", outputCsv);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(206);

    const std::vector<uint32_t> packetSizes = {256, 1024};

    std::ofstream out(outputCsv, std::ios::trunc);
    if (!out)
    {
        NS_LOG_UNCOND("Failed to open output CSV: " << outputCsv);
        return 1;
    }

    out << "mode,packet_size_bytes,num_senders,throughput_mbps,goodput_mbps,avg_delay_ms,jitter_ms,"
           "packet_loss_rate_pct,queue_drops,overhead_ratio_pct\n";
    out << std::fixed << std::setprecision(6);

    uint32_t runNumber = 1;
    for (uint32_t packetSize : packetSizes)
    {
        for (bool congested : {false, true})
        {
            Metrics m = RunCongestionScenario(congested, packetSize, simSeconds, runNumber++);
            out << (congested ? "congested" : "no_congestion") << ',' << packetSize << ','
                << (congested ? 3 : 1) << ',' << m.throughputMbps << ',' << m.goodputMbps << ','
                << m.delayMs << ',' << m.jitterMs << ',' << m.lossPct << ',' << m.queueDrops << ','
                << m.overheadPct << '\n';
        }
    }

    NS_LOG_UNCOND("Experiment 3 results written to: " << outputCsv);
    return 0;
}
