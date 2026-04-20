#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>

using namespace ns3;

namespace
{
constexpr uint32_t kIpUdpHeaderBytes = 28;

struct Metrics
{
    double throughputMbps{0.0};
    double goodputMbps{0.0};
    double delayMs{0.0};
    double lossPct{0.0};
    double overheadPct{0.0};
};

Metrics
RunBandwidthScenario(uint32_t packetSize,
                     uint32_t bandwidthMbps,
                     double offeredLoadFactor,
                     double simSeconds,
                     uint32_t runNumber)
{
    RngSeedManager::SetRun(runNumber);

    NodeContainer nodes;
    nodes.Create(2);

    PointToPointHelper p2p;
    std::ostringstream bw;
    bw << bandwidthMbps << "Mbps";
    p2p.SetDeviceAttribute("DataRate", StringValue(bw.str()));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));

    NetDeviceContainer devices = p2p.Install(nodes);

    InternetStackHelper internet;
    internet.Install(nodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.1.2.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign(devices);

    constexpr uint16_t port = 9001;
    PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), port));
    auto sinkApps = sinkHelper.Install(nodes.Get(1));
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(simSeconds + 0.5));

    const double offeredMbps = static_cast<double>(bandwidthMbps) * offeredLoadFactor;
    const uint64_t offeredBps = static_cast<uint64_t>(offeredMbps * 1e6);

    OnOffHelper onoff("ns3::UdpSocketFactory", Address(InetSocketAddress(interfaces.GetAddress(1), port)));
    onoff.SetAttribute("DataRate", DataRateValue(DataRate(offeredBps)));
    onoff.SetAttribute("PacketSize", UintegerValue(packetSize));
    onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));

    auto senderApps = onoff.Install(nodes.Get(0));
    senderApps.Start(Seconds(1.0));
    senderApps.Stop(Seconds(simSeconds));

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();

    Simulator::Stop(Seconds(simSeconds + 1.0));
    Simulator::Run();

    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowHelper.GetClassifier());

    Metrics m;
    for (const auto& kv : monitor->GetFlowStats())
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(kv.first);
        if (t.destinationPort != port)
        {
            continue;
        }

        const auto& s = kv.second;
        const double activeTime = simSeconds - 1.0;
        m.throughputMbps = static_cast<double>(s.rxBytes) * 8.0 / activeTime / 1e6;
        m.goodputMbps = static_cast<double>(s.rxPackets) * packetSize * 8.0 / activeTime / 1e6;
        m.delayMs = (s.rxPackets > 0) ? (s.delaySum.GetSeconds() * 1000.0 / static_cast<double>(s.rxPackets))
                                      : 0.0;
        m.lossPct = (s.txPackets > 0)
                        ? (static_cast<double>(s.txPackets - s.rxPackets) * 100.0 /
                           static_cast<double>(s.txPackets))
                        : 0.0;

        const double totalBytes = static_cast<double>(s.rxPackets) * (packetSize + kIpUdpHeaderBytes);
        const double headerBytes = static_cast<double>(s.rxPackets) * kIpUdpHeaderBytes;
        m.overheadPct = (totalBytes > 0.0) ? (headerBytes * 100.0 / totalBytes) : 0.0;
        break;
    }

    Simulator::Destroy();
    return m;
}
} // namespace

int
main(int argc, char* argv[])
{
    double simSeconds = 10.0;
    std::string outputCsv = "project/results/experiment2_bandwidth.csv";

    CommandLine cmd(__FILE__);
    cmd.AddValue("simSeconds", "Simulation duration in seconds", simSeconds);
    cmd.AddValue("outputCsv", "Output CSV file path", outputCsv);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(206);

    const std::vector<uint32_t> packetSizes = {512, 1500};
    const std::vector<uint32_t> bandwidthsMbps = {1, 5, 10, 100};
    constexpr double offeredLoadFactor = 0.8;

    std::ofstream out(outputCsv, std::ios::trunc);
    if (!out)
    {
        NS_LOG_UNCOND("Failed to open output CSV: " << outputCsv);
        return 1;
    }

    out << "packet_size_bytes,bandwidth_mbps,serialization_delay_ms,throughput_mbps,goodput_mbps,"
           "avg_delay_ms,packet_loss_rate_pct,overhead_ratio_pct\n";
    out << std::fixed << std::setprecision(6);

    uint32_t runNumber = 1;
    for (uint32_t packetSize : packetSizes)
    {
        for (uint32_t bw : bandwidthsMbps)
        {
            const double serializationMs =
                static_cast<double>(packetSize) * 8.0 / (static_cast<double>(bw) * 1e6) * 1000.0;

            Metrics m = RunBandwidthScenario(packetSize, bw, offeredLoadFactor, simSeconds, runNumber++);
            out << packetSize << ',' << bw << ',' << serializationMs << ',' << m.throughputMbps << ','
                << m.goodputMbps << ',' << m.delayMs << ',' << m.lossPct << ',' << m.overheadPct << '\n';
        }
    }

    NS_LOG_UNCOND("Experiment 2 results written to: " << outputCsv);
    return 0;
}
