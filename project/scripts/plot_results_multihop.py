#!/usr/bin/env python3
"""Plot polished figures for the multi-hop PyNS3 experiment outputs."""

import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
IMAGES_DIR = os.path.join(RESULTS_DIR, "images")


def read_rows(filename):
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_float(rows, key):
    return [float(r[key]) for r in rows]


def style_axes(ax):
    ax.grid(True, alpha=0.25, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_alpha(0.3)


def save(fig, filename):
    out = os.path.join(IMAGES_DIR, filename)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def plot_experiment1_delay():
    rows = read_rows("results_experiment1.csv")
    x = [int(float(r["delay_ms"])) for r in rows]
    delay = as_float(rows, "avg_delay_ms")
    throughput = as_float(rows, "throughput_mbps")

    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.plot(x, delay, marker="o", linewidth=2.2, color="#1f77b4", label="Avg delay")
    ax1.set_xlabel("Bottleneck propagation delay (ms)")
    ax1.set_ylabel("End-to-end delay (ms)", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    style_axes(ax1)

    ax2 = ax1.twinx()
    ax2.plot(x, throughput, marker="s", linewidth=2.0, color="#ff7f0e", label="Throughput")
    ax2.set_ylabel("Throughput (Mbps)", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    fig.suptitle("Experiment 1: Delay Sweep (Single Sender, 50% Load)")
    save(fig, "exp1_delay_vs_e2e_delay_throughput.png")


def plot_experiment1_all_metrics():
    rows = read_rows("results_experiment1.csv")
    x = [int(float(r["delay_ms"])) for r in rows]
    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)", "#1f77b4"),
        ("goodput_mbps", "Goodput (Mbps)", "#2ca02c"),
        ("avg_delay_ms", "Delay (ms)", "#9467bd"),
        ("packet_loss_rate_pct", "Loss (%)", "#d62728"),
        ("overhead_ratio_pct", "Overhead (%)", "#ff7f0e"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(12, 9))
    flat_axes = axes.flatten()

    for idx, (key, ylabel, color) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(x, as_float(rows, key), marker="o", linewidth=2.1, color=color)
        ax.set_xlabel("Bottleneck delay (ms)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[-1].axis("off")
    fig.suptitle("Experiment 1: All Available Metrics")
    save(fig, "exp1_all_metrics.png")


def plot_experiment2_offered_load():
    """Plot packet size effect on throughput/delay across congestion modes."""
    rows = read_rows("results_experiment2.csv")
    
    # Separate data by congestion mode
    uncongested = [r for r in rows if r.get("congestion_mode") == "without_congestion"]
    congested = [r for r in rows if r.get("congestion_mode") == "with_congestion"]
    
    # Extract x values (packet size) and y values
    x_uncong = [int(r["packet_size_bytes"]) for r in uncongested]
    x_cong = [int(r["packet_size_bytes"]) for r in congested]
    
    goodput_uncong = [float(r["goodput_mbps"]) for r in uncongested]
    goodput_cong = [float(r["goodput_mbps"]) for r in congested]
    
    loss_uncong = [float(r["packet_loss_rate_pct"]) for r in uncongested]
    loss_cong = [float(r["packet_loss_rate_pct"]) for r in congested]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
    
    # Plot 1: Goodput
    ax1.plot(x_uncong, goodput_uncong, marker="o", linewidth=2.2, color="#1f77b4", label="No congestion (20% load)")
    ax1.plot(x_cong, goodput_cong, marker="s", linewidth=2.2, color="#d62728", label="With congestion (120% load)")
    ax1.set_xlabel("Packet size (bytes)")
    ax1.set_ylabel("Goodput (Mbps)")
    ax1.set_title("Goodput vs Packet Size")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    style_axes(ax1)
    
    # Plot 2: Loss rate
    ax2.plot(x_uncong, loss_uncong, marker="o", linewidth=2.2, color="#1f77b4", label="No congestion (20% load)")
    ax2.plot(x_cong, loss_cong, marker="s", linewidth=2.2, color="#d62728", label="With congestion (120% load)")
    ax2.set_xlabel("Packet size (bytes)")
    ax2.set_ylabel("Packet loss rate (%)")
    ax2.set_title("Loss Rate vs Packet Size")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    style_axes(ax2)
    
    fig.suptitle("Experiment 2: Packet Size Effect Under Different Congestion Levels")
    save(fig, "exp2_offered_load_knee.png")


def plot_experiment2_all_metrics():
    rows = read_rows("results_experiment2.csv")
    uncongested = [r for r in rows if r.get("congestion_mode") == "without_congestion"]
    congested = [r for r in rows if r.get("congestion_mode") == "with_congestion"]

    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)"),
        ("goodput_mbps", "Goodput (Mbps)"),
        ("avg_delay_ms", "Delay (ms)"),
        ("packet_loss_rate_pct", "Loss (%)"),
        ("overhead_ratio_pct", "Overhead (%)"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(12, 9))
    flat_axes = axes.flatten()

    for idx, (key, ylabel) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(
            [int(r["packet_size_bytes"]) for r in uncongested],
            [float(r[key]) for r in uncongested],
            marker="o",
            linewidth=2.1,
            color="#1f77b4",
            label="No congestion (20%)",
        )
        ax.plot(
            [int(r["packet_size_bytes"]) for r in congested],
            [float(r[key]) for r in congested],
            marker="s",
            linewidth=2.1,
            color="#d62728",
            label="With congestion (120%)",
        )
        ax.set_xlabel("Packet size (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[0].legend(loc="best")
    flat_axes[-1].axis("off")
    fig.suptitle("Experiment 2: All Available Metrics")
    save(fig, "exp2_all_metrics.png")



def plot_experiment3_bottleneck_sweep():
    rows = read_rows("results_experiment3.csv")
    sweep = [r for r in rows if r["scenario"] == "bottleneck_sweep"]
    x = [float(r["bottleneck_mbps"]) for r in sweep]
    throughput = as_float(sweep, "throughput_mbps")
    goodput = as_float(sweep, "goodput_mbps")
    loss = as_float(sweep, "packet_loss_rate_pct")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(x, throughput, marker="o", linewidth=2.2, label="Throughput")
    ax.plot(x, goodput, marker="s", linewidth=2.2, label="Goodput")
    ax.plot(x, loss, marker="^", linewidth=2.0, label="Loss rate (%)")
    ax.axvline(12, linestyle="--", color="gray", alpha=0.7, linewidth=1.3, label="Offered load = 12 Mbps")
    ax.set_xlabel("Bottleneck bandwidth (Mbps)")
    ax.set_ylabel("Metric value")
    ax.set_title("Experiment 3A: Bottleneck Provisioning Crossover")
    style_axes(ax)
    ax.legend(loc="best")
    save(fig, "exp3a_bottleneck_crossover.png")


def plot_experiment3_packet_sweep():
    rows = read_rows("results_experiment3.csv")
    sweep = [r for r in rows if r["scenario"] == "packet_size_sweep"]
    x = [int(float(r["packet_size_bytes"])) for r in sweep]
    goodput = as_float(sweep, "goodput_mbps")
    overhead = as_float(sweep, "overhead_ratio_pct")

    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.plot(x, goodput, marker="o", linewidth=2.2, color="#2ca02c")
    ax1.set_xlabel("Packet size (bytes)")
    ax1.set_ylabel("Goodput (Mbps)", color="#2ca02c")
    ax1.tick_params(axis="y", labelcolor="#2ca02c")
    style_axes(ax1)

    ax2 = ax1.twinx()
    ax2.plot(x, overhead, marker="s", linewidth=2.0, color="#ff7f0e")
    ax2.set_ylabel("Overhead ratio (%)", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    fig.suptitle("Experiment 3B: Packet Size Impact at 10 Mbps Bottleneck")
    save(fig, "exp3b_packet_size_goodput_overhead.png")


def plot_experiment3_all_metrics():
    rows = read_rows("results_experiment3.csv")
    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)", "#1f77b4"),
        ("goodput_mbps", "Goodput (Mbps)", "#2ca02c"),
        ("avg_delay_ms", "Delay (ms)", "#9467bd"),
        ("packet_loss_rate_pct", "Loss (%)", "#d62728"),
        ("overhead_ratio_pct", "Overhead (%)", "#ff7f0e"),
    ]

    for scenario, xlabel, out_name, title in [
        (
            "bottleneck_sweep",
            "Bottleneck bandwidth (Mbps)",
            "exp3a_all_metrics.png",
            "Experiment 3A: All Available Metrics",
        ),
        (
            "packet_size_sweep",
            "Packet size (bytes)",
            "exp3b_all_metrics.png",
            "Experiment 3B: All Available Metrics",
        ),
    ]:
        sweep = [r for r in rows if r["scenario"] == scenario]
        x_key = "bottleneck_mbps" if scenario == "bottleneck_sweep" else "packet_size_bytes"
        x = [float(r[x_key]) for r in sweep]

        fig, axes = plt.subplots(3, 2, figsize=(12, 9))
        flat_axes = axes.flatten()

        for idx, (key, ylabel, color) in enumerate(metric_specs):
            ax = flat_axes[idx]
            ax.plot(x, as_float(sweep, key), marker="o", linewidth=2.1, color=color)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            style_axes(ax)

        flat_axes[-1].axis("off")
        fig.suptitle(title)
        save(fig, out_name)


def plot_experiment4_wired_vs_wireless():
    rows = read_rows("results_experiment4.csv")
    grouped = defaultdict(dict)
    for r in rows:
        psize = int(float(r["packet_size_bytes"]))
        grouped[psize][r["link_type"]] = r

    packet_sizes = sorted(grouped.keys())
    wireless_goodput = [float(grouped[p]["wireless"]["goodput_mbps"]) for p in packet_sizes]
    wired_goodput = [float(grouped[p]["wired"]["goodput_mbps"]) for p in packet_sizes]
    wireless_delay = [float(grouped[p]["wireless"]["avg_delay_ms"]) for p in packet_sizes]
    wired_delay = [float(grouped[p]["wired"]["avg_delay_ms"]) for p in packet_sizes]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(packet_sizes, wireless_goodput, marker="o", linewidth=2.2, label="Wireless goodput")
    ax.plot(packet_sizes, wired_goodput, marker="s", linewidth=2.2, label="Wired goodput")
    ax.plot(packet_sizes, wireless_delay, marker="^", linewidth=1.8, linestyle="--", label="Wireless delay")
    ax.plot(packet_sizes, wired_delay, marker="d", linewidth=1.8, linestyle="--", label="Wired delay")
    ax.set_xlabel("Packet size (bytes)")
    ax.set_ylabel("Metric value")
    ax.set_title("Experiment 4: Wired vs Wireless Last-Hop Comparison")
    style_axes(ax)
    ax.legend(loc="best")
    save(fig, "exp4_wired_vs_wireless_comparison.png")


def plot_experiment4_all_metrics():
    rows = read_rows("results_experiment4.csv")
    grouped = defaultdict(dict)
    for r in rows:
        psize = int(float(r["packet_size_bytes"]))
        grouped[psize][r["link_type"]] = r

    packet_sizes = sorted(grouped.keys())
    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)"),
        ("goodput_mbps", "Goodput (Mbps)"),
        ("avg_delay_ms", "Delay (ms)"),
        ("packet_loss_rate_pct", "Loss (%)"),
        ("overhead_ratio_pct", "Overhead (%)"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(12, 9))
    flat_axes = axes.flatten()

    for idx, (key, ylabel) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(
            packet_sizes,
            [float(grouped[p]["wireless"][key]) for p in packet_sizes],
            marker="o",
            linewidth=2.1,
            color="#1f77b4",
            label="Wireless",
        )
        ax.plot(
            packet_sizes,
            [float(grouped[p]["wired"][key]) for p in packet_sizes],
            marker="s",
            linewidth=2.1,
            color="#d62728",
            label="Wired",
        )
        ax.set_xlabel("Packet size (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[0].legend(loc="best")
    flat_axes[-1].axis("off")
    fig.suptitle("Experiment 4: All Available Metrics")
    save(fig, "exp4_all_metrics.png")


def plot_baseline_bar():
    rows = read_rows("baseline.csv")
    baseline = rows[0]
    metric_names = ["Throughput", "Goodput", "Delay", "Loss", "Overhead"]
    metric_values = [
        float(baseline["throughput_mbps"]),
        float(baseline["goodput_mbps"]),
        float(baseline["avg_delay_ms"]),
        float(baseline["packet_loss_rate_pct"]),
        float(baseline["overhead_ratio_pct"]),
    ]
    metric_units = ["Mbps", "Mbps", "ms", "%", "%"]

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    bars = ax.bar(metric_names, metric_values, color=["#1f77b4", "#2ca02c", "#9467bd", "#d62728", "#ff7f0e"])
    for b, unit in zip(bars, metric_units):
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            b.get_height(),
            f"{b.get_height():.2f} {unit}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_title("Baseline Metrics Snapshot")
    ax.set_xlabel("Metric")
    ax.set_ylabel("Value (native units per metric)")
    style_axes(ax)
    save(fig, "baseline_metrics_snapshot.png")


def plot_experiment5_mtu_payload_sweep():
    rows = read_rows("experiment4_mtu.csv")
    x = [int(float(r["payload_bytes"])) for r in rows]
    goodput = as_float(rows, "goodput_mbps")
    overhead = as_float(rows, "overhead_ratio_pct")
    loss = as_float(rows, "packet_loss_rate_pct")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(x, goodput, marker="o", linewidth=2.2, label="Goodput (Mbps)")
    ax.plot(x, overhead, marker="s", linewidth=2.0, label="Overhead ratio (%)")
    ax.plot(x, loss, marker="^", linewidth=2.0, label="Loss rate (%)")
    ax.axvline(548, linestyle="--", color="gray", alpha=0.75, linewidth=1.3, label="Payload at MTU limit")
    ax.set_xlabel("Payload size (bytes)")
    ax.set_ylabel("Metric value")
    ax.set_title("Experiment 5: Fixed Link MTU, Payload Sweep")
    style_axes(ax)
    ax.legend(loc="best")
    save(fig, "exp5_mtu_payload_sweep.png")


def plot_experiment5_all_metrics():
    rows = read_rows("experiment4_mtu.csv")
    x = [int(float(r["payload_bytes"])) for r in rows]
    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)", "#1f77b4"),
        ("goodput_mbps", "Goodput (Mbps)", "#2ca02c"),
        ("avg_delay_ms", "Delay (ms)", "#9467bd"),
        ("packet_loss_rate_pct", "Loss (%)", "#d62728"),
        ("overhead_ratio_pct", "Overhead (%)", "#ff7f0e"),
        ("flowmonitor_drop_events", "FlowMonitor drops", "#8c564b"),
        ("oversized_packet_drops", "Oversized packet drops", "#17becf"),
    ]

    fig, axes = plt.subplots(4, 2, figsize=(12, 11))
    flat_axes = axes.flatten()

    for idx, (key, ylabel, color) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(x, as_float(rows, key), marker="o", linewidth=2.1, color=color)
        ax.set_xlabel("Payload size (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[-1].axis("off")
    fig.suptitle("Experiment 5: All Available Metrics")
    save(fig, "exp5_all_metrics.png")


def plot_experiment6_link_mtu_sweep():
    rows = read_rows("experiment4_mtu_link_mtu.csv")
    x = [int(float(r["link_mtu_bytes"])) for r in rows]
    throughput = as_float(rows, "throughput_mbps")
    goodput = as_float(rows, "goodput_mbps")
    delay = as_float(rows, "avg_delay_ms")

    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.plot(x, throughput, marker="o", linewidth=2.2, color="#1f77b4", label="Throughput")
    ax1.plot(x, goodput, marker="s", linewidth=2.2, color="#2ca02c", label="Goodput")
    ax1.set_xlabel("Link MTU (bytes)")
    ax1.set_ylabel("Rate (Mbps)")
    style_axes(ax1)

    ax2 = ax1.twinx()
    ax2.plot(x, delay, marker="^", linewidth=2.0, color="#9467bd", label="Delay")
    ax2.set_ylabel("Delay (ms)", color="#9467bd")
    ax2.tick_params(axis="y", labelcolor="#9467bd")

    frame_size = int(float(rows[0]["frame_bytes"]))
    ax1.axvline(frame_size, linestyle="--", color="gray", alpha=0.75, linewidth=1.3)
    fig.suptitle("Experiment 6: Link MTU Sweep with Fixed Payload")
    save(fig, "exp6_link_mtu_sweep.png")


def plot_experiment6_all_metrics():
    rows = read_rows("experiment4_mtu_link_mtu.csv")
    x = [int(float(r["link_mtu_bytes"])) for r in rows]
    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)", "#1f77b4"),
        ("goodput_mbps", "Goodput (Mbps)", "#2ca02c"),
        ("avg_delay_ms", "Delay (ms)", "#9467bd"),
        ("packet_loss_rate_pct", "Loss (%)", "#d62728"),
        ("overhead_ratio_pct", "Overhead (%)", "#ff7f0e"),
        ("flowmonitor_drop_events", "FlowMonitor drops", "#8c564b"),
        ("oversized_packet_drops", "Oversized packet drops", "#17becf"),
    ]

    fig, axes = plt.subplots(4, 2, figsize=(12, 11))
    flat_axes = axes.flatten()

    for idx, (key, ylabel, color) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(x, as_float(rows, key), marker="o", linewidth=2.1, color=color)
        ax.set_xlabel("Link MTU (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    frame_size = int(float(rows[0]["frame_bytes"]))
    for idx in range(len(metric_specs)):
        flat_axes[idx].axvline(frame_size, linestyle="--", color="gray", alpha=0.7, linewidth=1.1)

    flat_axes[-1].axis("off")
    fig.suptitle("Experiment 6: All Available Metrics")
    save(fig, "exp6_all_metrics.png")


def plot_experiment7_tcp_vs_udp():
    rows = read_rows("results_experiment7.csv")
    x = [int(float(r["packet_size_bytes"])) for r in rows]
    udp_goodput = as_float(rows, "udp_goodput_mbps")
    tcp_goodput = as_float(rows, "tcp_goodput_mbps")
    udp_loss = as_float(rows, "udp_packet_loss_rate_pct")
    tcp_loss = as_float(rows, "tcp_packet_loss_rate_pct")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(x, udp_goodput, marker="o", linewidth=2.2, label="UDP goodput")
    ax.plot(x, tcp_goodput, marker="s", linewidth=2.2, label="TCP goodput")
    ax.plot(x, udp_loss, marker="^", linewidth=1.8, linestyle="--", label="UDP loss (%)")
    ax.plot(x, tcp_loss, marker="d", linewidth=1.8, linestyle="--", label="TCP loss (%)")
    ax.set_xlabel("Packet size (bytes)")
    ax.set_ylabel("Metric value")
    ax.set_title("Experiment 7: TCP Competing with UDP")
    style_axes(ax)
    ax.legend(loc="best")
    save(fig, "exp7_tcp_vs_udp_competition.png")


def plot_experiment7_all_metrics():
    rows = read_rows("results_experiment7.csv")
    x = [int(float(r["packet_size_bytes"])) for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    flat_axes = axes.flatten()

    metric_pairs = [
        ("udp_goodput_mbps", "tcp_goodput_mbps", "Goodput (Mbps)"),
        ("udp_packet_loss_rate_pct", "tcp_packet_loss_rate_pct", "Loss (%)"),
        ("udp_overhead_ratio_pct", "tcp_overhead_ratio_pct", "Overhead (%)"),
        (
            "udp_fragmentation_effect_flowmonitor_drops",
            "tcp_fragmentation_effect_flowmonitor_drops",
            "FlowMonitor drops",
        ),
    ]

    for idx, (udp_key, tcp_key, ylabel) in enumerate(metric_pairs):
        ax = flat_axes[idx]
        ax.plot(x, as_float(rows, udp_key), marker="o", linewidth=2.1, color="#1f77b4", label="UDP")
        ax.plot(x, as_float(rows, tcp_key), marker="s", linewidth=2.1, color="#d62728", label="TCP")
        ax.set_xlabel("Packet size (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[0].legend(loc="best")
    fig.suptitle("Experiment 7: All Available Metrics")
    save(fig, "exp7_all_metrics.png")


def plot_experiment8_all_metrics():
    rows = read_rows("results_experiment8.csv")
    low_bw = [r for r in rows if r["regime"] == "low_bw"]
    high_bw = [r for r in rows if r["regime"] == "high_bw"]

    metric_specs = [
        ("throughput_mbps", "Throughput (Mbps)"),
        ("goodput_mbps", "Goodput (Mbps)"),
        ("avg_delay_ms", "Delay (ms)"),
        ("packet_loss_rate_pct", "Loss (%)"),
        ("overhead_ratio_pct", "Overhead (%)"),
        ("serial_delay_ms", "Serialization delay (ms)"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(12, 9))
    flat_axes = axes.flatten()

    for idx, (key, ylabel) in enumerate(metric_specs):
        ax = flat_axes[idx]
        ax.plot(
            [int(float(r["packet_size_bytes"])) for r in low_bw],
            [float(r[key]) for r in low_bw],
            marker="o",
            linewidth=2.1,
            color="#1f77b4",
            label="Low BW (1 Mbps)",
        )
        ax.plot(
            [int(float(r["packet_size_bytes"])) for r in high_bw],
            [float(r[key]) for r in high_bw],
            marker="s",
            linewidth=2.1,
            color="#d62728",
            label="High BW (100 Mbps)",
        )
        ax.set_xlabel("Packet size (bytes)")
        ax.set_ylabel(ylabel)
        style_axes(ax)

    flat_axes[0].legend(loc="best")
    fig.suptitle("Experiment 8: All Available Metrics")
    save(fig, "exp8_all_metrics.png")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    plot_baseline_bar()
    plot_experiment1_delay()
    plot_experiment1_all_metrics()
    plot_experiment2_offered_load()
    plot_experiment2_all_metrics()
    plot_experiment3_bottleneck_sweep()
    plot_experiment3_packet_sweep()
    plot_experiment3_all_metrics()
    plot_experiment4_wired_vs_wireless()
    plot_experiment4_all_metrics()
    plot_experiment5_mtu_payload_sweep()
    plot_experiment5_all_metrics()
    plot_experiment6_link_mtu_sweep()
    plot_experiment6_all_metrics()
    plot_experiment7_tcp_vs_udp()
    plot_experiment7_all_metrics()
    plot_experiment8_all_metrics()

    print(f"Saved multi-hop figures to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
