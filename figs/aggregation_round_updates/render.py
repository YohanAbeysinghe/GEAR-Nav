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
from matplotlib.lines import Line2D

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
    orange, blue, ink = "#bf4e21", "#486680", "#26313b"
    plt.rcParams.update({"font.family": "STIXGeneral", "font.size": 10.5,
                         "text.color": ink, "xtick.color": ink, "ytick.color": ink,
                         "axes.labelcolor": ink, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "svg.hashsalt": "gear-aggregation-rounds"})
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.55))
    fig.subplots_adjust(left=.10, right=.975, top=.675, bottom=.20, wspace=.22)
    fig.text(.043, .905, "Path corrections shrink over aggregation rounds",
             weight="bold", fontsize=17)
    handles = [Line2D([], [], color=orange, lw=2.3, label="Median"),
               Line2D([], [], color=blue, lw=1.5, ls="--", label="95th percentile"),
               Line2D([], [], color="#65727a", lw=1.2, ls=":", label=f"Continuation checkpoint (round {k})")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.042, .876),
               ncol=3, frameon=False, borderaxespad=0, columnspacing=1.4, handlelength=1.9)
    for ax, first, ymax, yticks, xticks, title in [
        (axes[0], 1, 92, [0, 20, 40, 60, 80], [1, 14, 30, 45, 61], "All recorded rounds"),
        (axes[1], 10, 8, [0, 2, 4, 6, 8], [10, 20, 30, 40, 50, 61], "Detail from round 10"),
    ]:
        mask = rounds >= first
        ax.grid(axis="y", lw=.55, color="#dce1e4")
        ax.set_axisbelow(True)
        ax.axvline(k, ls=":", lw=1.1, color="#65727a", zorder=1)
        for key, color, style in [("p95_cm", blue, "--"), ("median_cm", orange, "-")]:
            ax.plot(rounds[mask], data[key][mask], color=color, ls=style,
                    lw=1.6 if style == "--" else 2, zorder=2)
            ax.plot(k, selected[key], "o", ms=5.2, mec="white", mew=.7, color=color, zorder=3)
        ax.set(xlim=(first-.7, rounds[-1]+.8), ylim=(-.023*ymax, ymax), xticks=xticks, yticks=yticks)
        ax.set_title(title, loc="left", weight="bold", fontsize=11.5, pad=6)
        ax.spines[["left", "top", "right"]].set_visible(False)
        ax.spines["bottom"].set_color("#b6c0c6")
        ax.tick_params(length=0, pad=3)
    axes[0].set_ylabel("RMS path change (cm)", labelpad=4)
    for key, color, offset in [("median_cm", orange, (11, 4)), ("p95_cm", blue, (11, 7))]:
        axes[1].annotate(f"{selected[key]:.2f} cm", (k, selected[key]), xytext=offset,
                         textcoords="offset points", color=color, fontsize=9, weight="bold")
    fig.text(.54, .057, "Aggregation round", ha="center", fontsize=12)
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(HERE / f"round_updates.{ext}", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", action="store_true")
    if parser.parse_args().extract:
        extract()
    render()
