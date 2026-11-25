"""Draw median and p95 per-path RMS changes logged during training.

Render the checked-in CSV with .venv/bin/python figs/aggregation_round_updates/render.py.
Pass --extract to refresh the CSV from the training run's saved round_records.
The continuation run and its source checkpoint are recorded in continuation.json.
"""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "checkpoints/astar_clearance025_prefix_a6000x4_20260924/aggregation_state_00152875.npz"
CONTINUATION = ROOT / "checkpoints/astar_fulltrain_depth14_from35000_20260930/continuation.json"
DATA = HERE / "round_updates.csv"


def extract():
    with np.load(SOURCE, allow_pickle=False) as archive:
        records = json.loads(archive["metadata_json"].item())["round_records"]
    config = json.loads(CONTINUATION.read_text())
    rounds = [record["round"] for record in records]
    assert rounds == list(range(1, len(rounds) + 1))
    assert records[config["depth_cap"] - 1]["optimizer_step"] == config["source_step"]
    with DATA.open("w", newline="") as fp:
        writer = csv.writer(fp, lineterminator="\n")
        writer.writerow(["round", "optimizer_step", "median_cm", "p95_cm", "continuation_source"])
        for record in records:
            step = record["optimizer_step"]
            writer.writerow([record["round"], step, 100 * record["path_change_median"],
                             100 * record["path_change_p95"], int(step == config["source_step"])])


def render():
    data = np.genfromtxt(DATA, delimiter=",", names=True)
    rounds = data["round"]
    selected, = data[data["continuation_source"] == 1]
    k = int(selected["round"])
    ink, orange, blue = "#222b32", "#bd4a1d", "#466781"
    plt.rcParams.update({
        "font.family": "STIXGeneral", "font.size": 8, "text.color": ink,
        "axes.labelcolor": ink, "xtick.color": ink, "ytick.color": ink,
        "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "gear-aggregation-rounds",
    })
    fig = plt.figure(figsize=(3.4, 2.13))
    main = fig.add_axes([.148, .195, .835, .68])
    detail_color = "#f5f7f8"
    main.add_patch(FancyBboxPatch((.386, .23), .605, .745, transform=main.transAxes,
                                  boxstyle="round,pad=0.005,rounding_size=0.012",
                                  facecolor=detail_color, edgecolor="#dce2e5", lw=.5, zorder=2.5))
    detail = main.inset_axes([.445, .335, .525, .51], facecolor=detail_color)
    for ax, start, limit, xticks, yticks in [
        (main, 1, 92, [1, k, 30, 45, 61], [0, 20, 40, 60, 80]),
        (detail, 10, 8, [10, 35, 61], [0, 4, 8]),
    ]:
        mask = rounds >= start
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#dce2e5", linewidth=.45)
        ax.axvline(k, color="#656a6e", linestyle=":", linewidth=.85, zorder=1)
        for key, color, style, label in [
            ("p95_cm", blue, (0, (3, 1.65)), "95th percentile"),
            ("median_cm", orange, "-", "Median"),
        ]:
            ax.plot(rounds[mask], data[key][mask], color=color, linestyle=style,
                    linewidth=1.05 if ax is detail else 1.35, label=label)
            ax.plot(k, selected[key], "o", color=color, ms=2.6 if ax is detail else 3.6,
                    mec="white", mew=.4, zorder=3)
        ax.set(xlim=(start-.65, rounds[-1]+.65), ylim=(-.022*limit, limit),
               xticks=xticks, yticks=yticks)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#9ca6ac")
        ax.spines["bottom"].set_linewidth(.5)
        ax.tick_params(length=0, pad=2, labelsize=7 if ax is detail else 8)

    main.set_xlabel("Aggregation round", labelpad=2, fontsize=9)
    main.set_ylabel("RMS path change (cm)", labelpad=2, fontsize=9)
    detail.set_title("Rounds 10–61 (cm)", fontsize=7.6, pad=3, loc="left")
    handles, labels = main.get_legend_handles_labels()
    fig.legend(handles[::-1], labels[::-1], loc="upper left", bbox_to_anchor=(.138, .997),
               ncol=2, frameon=False, borderaxespad=0, columnspacing=1.35, handlelength=1.9)
    main.annotate("Round 14", xy=(k, 48), xytext=(2, 0), textcoords="offset points",
                  color="#545b60", fontsize=7.4)
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(HERE / f"round_updates.{ext}", dpi=320,
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)
    svg = HERE / "round_updates.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", action="store_true")
    if parser.parse_args().extract:
        extract()
    render()
