#!/usr/bin/env python3
"""Generate all required CMPE 206 packet-size study figures from CSV outputs."""

import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(rows, key):
    return [float(r[key]) for r in rows]


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def plot_experiment1():
    rows = read_csv_rows(os.path.join(RESULTS_DIR, "experiment1_packet_size.csv"))
    packet_sizes = [int(float(r["packet_size_bytes"])) for r in rows]
    goodput = to_float(rows, "goodput_mbps")
    overhead = to_float(rows, "overhead_ratio_pct")
    delay = to_float(rows, "avg_delay_ms")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(packet_sizes, goodput, marker="o", linewidth=2)
    ax.set_title("Goodput vs Packet Size")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Goodput (Mbps)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "goodput_vs_packet_size.png"), dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(packet_sizes, overhead, marker="s", linewidth=2, color="tab:orange")
    ax.set_title("Overhead Ratio vs Packet Size")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Overhead Ratio (%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "overhead_vs_packet_size.png"), dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(packet_sizes, delay, marker="^", linewidth=2, color="tab:green")
    ax.set_title("End-to-End Delay vs Packet Size")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Average Delay (ms)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "delay_vs_packet_size.png"), dpi=300)
    plt.close(fig)


def plot_experiment2():
    rows = read_csv_rows(os.path.join(RESULTS_DIR, "experiment2_bandwidth.csv"))

    grouped = defaultdict(list)
    for r in rows:
        psize = int(float(r["packet_size_bytes"]))
        grouped[psize].append(r)

    fig, ax = plt.subplots(figsize=(8, 5))
    for psize, vals in sorted(grouped.items()):
        vals_sorted = sorted(vals, key=lambda x: float(x["bandwidth_mbps"]))
        x = [float(v["bandwidth_mbps"]) for v in vals_sorted]
        y = [float(v["throughput_mbps"]) for v in vals_sorted]
        ax.plot(x, y, marker="o", linewidth=2, label=f"Packet Size {psize} B")

    ax.set_title("Throughput vs Bandwidth")
    ax.set_xlabel("Bandwidth (Mbps)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "throughput_vs_bandwidth.png"), dpi=300)
    plt.close(fig)


def plot_experiment3():
    rows = read_csv_rows(os.path.join(RESULTS_DIR, "experiment3_congestion.csv"))

    grouped = defaultdict(dict)
    for r in rows:
        psize = int(float(r["packet_size_bytes"]))
        mode = r["mode"]
        grouped[psize][mode] = float(r["packet_loss_rate_pct"])

    packet_sizes = sorted(grouped.keys())
    no_cong = [grouped[p].get("no_congestion", 0.0) for p in packet_sizes]
    cong = [grouped[p].get("congested", 0.0) for p in packet_sizes]

    x = range(len(packet_sizes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([i - width / 2 for i in x], no_cong, width=width, label="No Congestion")
    ax.bar([i + width / 2 for i in x], cong, width=width, label="Congested")

    ax.set_title("Packet Loss Rate vs Packet Size (Congested vs No Congestion)")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Packet Loss Rate (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(p) for p in packet_sizes])
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "loss_vs_packet_size_congestion.png"), dpi=300)
    plt.close(fig)


def main():
    ensure_results_dir()
    plot_experiment1()
    plot_experiment2()
    plot_experiment3()
    print(f"Saved all graphs to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
