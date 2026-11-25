"""Plot the fraction of paired model-only updates that strictly lower geometric energy."""

import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import COLORS, FONT, INK

CACHE = HERE / "checkpoint_30000.csv"


def extract(log):
    paths = {}
    clips = set()
    with log.open() as source:
        for line in source:
            row = json.loads(line)
            if (row["checkpoint"], row["parameter_source"], row["mode"]) != ("30000", "raw", "model_only"):
                continue
            clips.add(row["clip_id"])
            trajectory = paths.setdefault(row["example_id"], {})
            depth = row["depth"]
            if depth in trajectory:
                raise ValueError("Duplicate evaluation record")
            trajectory[depth] = row["obstacle_energy"]
    if len(paths) != 300 or len(clips) != 8 or any(set(p) != set(range(13)) for p in paths.values()):
        raise ValueError("Expected 300 complete trajectories through 12 updates on eight clips")
    energy = np.array([[p[k] for k in range(13)] for p in paths.values()])
    if not np.isfinite(energy).all():
        raise ValueError("Non-finite geometric energy")
    with CACHE.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["update", "pairs_with_lower_energy", "pairs"])
        for k, count in enumerate((np.diff(energy, axis=1) < 0).sum(axis=0), start=1):
            writer.writerow([k, count, len(paths)])


def render():
    with CACHE.open() as f:
        rows = list(csv.DictReader(f))
    steps = [int(r["update"]) for r in rows]
    percent = [100 * int(r["pairs_with_lower_energy"]) / int(r["pairs"]) for r in rows]
    plt.rcParams.update({"font.family": "serif", "font.serif": [FONT, "STIXGeneral", "Liberation Serif"],
                         "svg.fonttype": "none", "svg.hashsalt": "gear-energy", "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False, "text.color": INK})
    fig, ax = plt.subplots(figsize=(5.5, 3.15))
    fig.subplots_adjust(left=.13, bottom=.17, right=.96, top=.76)
    fig.text(.13, .92, "How often does refinement lower energy?", fontsize=14, weight="bold")
    fig.text(.13, .835, "Checkpoint 30,000  ·  300 held-out frame–goal pairs  ·  8 clips", fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#dcdfe2", linewidth=.65)
    ax.plot(steps, percent, color=COLORS[14], lw=2.1, marker="o", ms=5, mec="white", mew=.7)
    for i in (0, 5, 11):
        ax.annotate(f"{percent[i]:.1f}%", (steps[i], percent[i]), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=9, weight="bold")
    ax.set(xlim=(.45, 12.55), ylim=(65, 105), xticks=steps, yticks=[70, 80, 90, 100],
           xlabel="Refinement update", ylabel="Pairs with lower energy (%)")
    ax.spines[["left", "bottom"]].set_color("#72777b")
    ax.tick_params(length=3, labelsize=9)
    for ext, metadata in (("png", {}), ("pdf", {"CreationDate": None}), ("svg", {"Date": None})):
        fig.savefig(HERE / f"energy_decrease.{ext}", dpi=220, metadata=metadata)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-log", type=Path, help="Refresh the counts from eval/examples.jsonl")
    args = parser.parse_args()
    if args.from_log:
        extract(args.from_log)
    render()
