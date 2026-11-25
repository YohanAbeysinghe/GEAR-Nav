"""Plot model-only depth means from eval/summary.csv, raw checkpoint 30000."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

folder = Path(__file__).resolve().parent
with (folder / "checkpoint_30000.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))
steps = [int(r["depth"]) for r in rows]
progress = [100 * float(r["achieved_required_progress_ratio"]) for r in rows]
clearance = [float(r["dense_min_clearance_m"]) for r in rows]
ink = "#263141"
plt.rcParams.update({"font.family": "STIXGeneral", "font.size": 10,
                     "text.color": ink, "axes.labelcolor": ink,
                     "xtick.color": ink, "ytick.color": ink, "pdf.fonttype": 42})
fig, panels = plt.subplots(1, 2, figsize=(7, 3.0))
fig.subplots_adjust(left=.073, right=.97, bottom=.19, top=.68, wspace=.29)
fig.text(.035, .91, "What changes as GEAR refines a path?", weight="bold", fontsize=17)
fig.text(.035, .82, "Model-only rollout  ·  Checkpoint 30,000  ·  Means over 300 examples from 8 clips",
         color="#49596d", fontsize=10.5)
for ax, values, title, limits, ticks, color in [
    (panels[0], progress, "Required goal progress achieved (%)", (0, 100), [0,25,50,75,100], "#b9511b"),
    (panels[1], clearance, "Minimum footprint clearance (m)", (-.72,.02), [-.6,-.4,-.2,0], "#486888"),
]:
    ax.set_title(title, loc="left", fontsize=11, weight="bold", pad=6)
    ax.set(xlim=(-.45,12.45), ylim=limits, xticks=[0,3,6,9,12], yticks=ticks, xlabel="Refinement step")
    ax.spines[["left","right","top"]].set_visible(False)
    ax.spines["bottom"].set_color("#b5bec9")
    ax.tick_params(length=0, pad=4)
    ax.grid(axis="y", lw=.55, color="#dbe1e7")
    ax.set_axisbelow(True)
    ax.plot(steps, values, color=color, lw=2, marker="o", ms=4, mec="white", mew=.6)
    for idx, align in [(0,"left"),(-1,"right")]:
        label = f"{values[idx]:.1f}%" if ax is panels[0] else f"{values[idx]:.2f} m"
        ax.annotate(label, (steps[idx], values[idx]), xytext=(0,-12 if idx == 0 else 7), textcoords="offset points",
                    ha=align, color=color, fontsize=10)
for fmt in ["pdf","png"]:
    fig.savefig(folder / f"model_only_refinement.{fmt}", dpi=200)
