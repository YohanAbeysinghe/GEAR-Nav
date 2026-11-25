"""Render the illustrative GEAR-Nav figure from the adjacent CSV."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

ROOT = Path(__file__).resolve().parent
with (ROOT / "hypothetical.csv").open(newline="") as source:
    rows = sorted(csv.DictReader(source), key=lambda row: int(row["step"]))

ink = "#222c39"
muted = "#536173"
orange = "#cb521f"
blue = "#486888"
plt.rcParams.update({
    "font.family": "STIXGeneral", "font.size": 12, "text.color": ink,
    "axes.labelcolor": ink, "xtick.color": muted, "ytick.color": muted,
    "pdf.fonttype": 42, "svg.fonttype": "none",
})
fig = plt.figure(figsize=(6.8, 4.25), facecolor="white")
fig.text(.115, .927, "Progress and clearance during refinement", fontsize=21, weight="bold")
fig.text(.115, .865, "Hypothetical data", color="#974219", fontsize=12, weight="bold")
fig.text(.308, .865, "·   Numbers mark the refinement step.", fontsize=12, color=muted)
ax = fig.add_axes([.115, .155, .84, .62])
ax.set(xlim=(20, 100), ylim=(.14, .50), xlabel="Mean goal progress (% of required distance)")
ax.set_xticks(range(20, 101, 20))
ax.set_yticks([.15, .20, .25, .30, .35, .40, .45, .50])
ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
ax.set_xlabel(ax.get_xlabel(), labelpad=8, fontsize=13)
ax.text(0, 1.045, "Mean minimum obstacle clearance (m)",
        transform=ax.transAxes, fontsize=13)
ax.grid(axis="y", color="#dfe4e8", linewidth=.65)
ax.set_axisbelow(True)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.spines["bottom"].set_color("#adb8c2")
ax.tick_params(axis="both", length=0, pad=5)

for prefix, color, marker, linestyle, vertical in (
    ("initial_only", blue, "s", (0, (4, 2.4)), -12),
    ("aggregation", orange, "o", "-", 9),
):
    xs = [float(row[prefix + "_progress_pct"]) for row in rows]
    ys = [float(row[prefix + "_clearance_m"]) for row in rows]
    ax.plot(xs, ys, color=color, lw=2.3, ls=linestyle, solid_capstyle="round")
    ax.plot(xs[1:], ys[1:], linestyle="none", marker=marker, ms=6.5,
            markeredgecolor="white", markeredgewidth=.9, color=color)
    for row, x, y in zip(rows[1:], xs[1:], ys[1:]):
        ax.annotate(row["step"], (x, y), xytext=(0, vertical), textcoords="offset points",
                    ha="center", va="center", color=color, fontsize=10)
    if prefix == "aggregation":
        ax.annotate("GEAR with aggregation", (xs[-1], ys[-1]), xytext=(-10, 16),
                    textcoords="offset points", ha="right", color=color, weight="bold")
    else:
        ax.annotate("Initial-path training only", (xs[-1], ys[-1]), xytext=(6, 4),
                    textcoords="offset points", color=color)

x0, y0 = float(rows[0]["aggregation_progress_pct"]), float(rows[0]["aggregation_clearance_m"])
ax.plot(x0, y0, "o", color="white", markeredgecolor=ink, ms=7.5, mew=1.6)
ax.annotate("0  ·  Shared prior", (x0, y0), xytext=(-8, 13),
            textcoords="offset points", fontsize=11, color=ink)
for ext in ("pdf", "png", "svg"):
    fig.savefig(ROOT / f"hypothetical_refinement.{ext}", dpi=220)
plt.close(fig)
