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
    fig, ax = plt.subplots(figsize=(3.4, 2.13))
    fig.subplots_adjust(left=.13, right=.975, bottom=.195, top=.84)
    ax.set_yscale("function", functions=(np.sqrt, np.square))
    ax.set(xlim=(0, rounds[-1] + 1), ylim=(0, 100),
           xticks=[1, k, 30, 45, rounds[-1]], yticks=[0, 1, 4, 10, 25, 50, 100])
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#dce2e5", linewidth=.45)
    ax.vlines(k, 0, 69, color="#6b757b", linestyle=":", linewidth=.8)
    for key, color, style, label in [
        ("median_cm", orange, "-", "Median"),
        ("p95_cm", blue, (0, (3, 1.65)), "95th percentile"),
    ]:
        ax.plot(rounds, data[key], color=color, linestyle=style, linewidth=1.35, label=label)
        ax.plot(k, selected[key], "o", color=color, ms=3.8,
                mec="white", mew=.5, zorder=3)
    ax.annotate("Continuation checkpoint", (k, 69), xytext=(3, 0),
                textcoords="offset points", va="center", color=ink, fontsize=8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#9ca6ac")
    ax.spines["bottom"].set_linewidth(.5)
    ax.tick_params(length=0, pad=2)
    ax.set_xlabel("Aggregation round", labelpad=3, fontsize=9)
    ax.set_ylabel("RMS path change (cm)", labelpad=3, fontsize=9)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.04), ncol=2, frameon=False,
              borderaxespad=0, columnspacing=1.2, handlelength=2)
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
