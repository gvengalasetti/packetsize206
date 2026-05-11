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


def plot_experiment1_packet_size():
    rows = read_rows("results_experiment1.csv")
    x = [int(float(r["packet_size_bytes"])) for r in rows]
    goodput = as_float(rows, "goodput_mbps")
    overhead = as_float(rows, "overhead_ratio_pct")

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

    fig.suptitle("Experiment 1: Packet Size Sweep at 10 Mbps Bottleneck")
    save(fig, "exp1_packet_size_goodput_overhead.png")


def plot_experiment1_all_metrics():
    rows = read_rows("results_experiment1.csv")
    x = [int(float(r["packet_size_bytes"])) for r in rows]
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
        ax.set_xlabel("Packet size (bytes)")
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



def plot_baseline_bar():
    rows = read_rows("baseline_py.csv")
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


def plot_experiment3_link_mtu_sweep():
    rows = read_rows("results_experiment3.csv")
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
    fig.suptitle("Experiment 3: Link MTU Sweep with Fixed Payload")
    save(fig, "exp3_link_mtu_sweep.png")


def plot_experiment3_all_metrics():
    rows = read_rows("results_experiment3.csv")
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
    fig.suptitle("Experiment 3: All Available Metrics")
    save(fig, "exp3_all_metrics.png")


def plot_experiment4_tcp_vs_udp():
    rows = read_rows("results_experiment4.csv")
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
    ax.set_title("Experiment 4: TCP Competing with UDP")
    style_axes(ax)
    ax.legend(loc="best")
    save(fig, "exp4_tcp_vs_udp_competition.png")


def plot_experiment4_all_metrics():
    rows = read_rows("results_experiment4.csv")
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
    fig.suptitle("Experiment 4: All Available Metrics")
    save(fig, "exp4_all_metrics.png")


def plot_experiment5_all_metrics():
    rows = read_rows("results_experiment5.csv")
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
    fig.suptitle("Experiment 5: All Available Metrics")
    save(fig, "exp5_all_metrics.png")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    plt.style.use("seaborn-whitegrid")

    plot_baseline_bar()
    plot_experiment1_packet_size()
    plot_experiment1_all_metrics()
    plot_experiment2_offered_load()
    plot_experiment2_all_metrics()
    plot_experiment3_link_mtu_sweep()
    plot_experiment3_all_metrics()
    plot_experiment4_tcp_vs_udp()
    plot_experiment4_all_metrics()
    plot_experiment5_all_metrics()

    print(f"Saved multi-hop figures to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
