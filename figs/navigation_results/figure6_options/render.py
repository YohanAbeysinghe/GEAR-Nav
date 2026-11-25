"""Render three paper-width alternatives for Figure 6 from saved measurements."""

import csv
from pathlib import Path
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from figure_style import FONT, INK

ORANGE = "#A34C22"
SLATE = "#66727E"
GRID = "#E8E5E1"
WHITE = "#FFFFFF"
DEPTHS = (0, 14, 20, 30)
MAX_PATH_M = 15


def load_measurements():
    with (HERE.parent / "endpoints.csv").open(newline="") as source:
        records = list(csv.DictReader(source))
    with (HERE / "forward_clearance.csv").open(newline="") as source:
        clearance_records = list(csv.DictReader(source))

    def xy(prefix):
        return np.array([[float(row[f"{prefix}_{axis}_m"]) for axis in ("x", "y")] for row in records])

    goals = xy("goal")
    errors = {depth: np.linalg.norm(xy(f"end_{depth}") - goals, axis=1) for depth in DEPTHS}
    clearance = np.array([[float(row[f"{path}_min_clearance_m"]) for path in ("straight", "gear")]
                          for row in clearance_records])
    if len(records) != 300 or len({row["clip_id"] for row in records}) != 8 or len(clearance) != 278:
        raise ValueError("Unexpected evaluation coverage")
    key_fields = ("clip_id", "frame_id", "sampled_goal")
    endpoint_keys = {tuple(row[field] for field in key_fields) for row in records}
    clearance_keys = {tuple(row[field] for field in key_fields) for row in clearance_records}
    if len(endpoint_keys) != len(records) or len(clearance_keys) != len(clearance) or not clearance_keys <= endpoint_keys:
        raise ValueError("Clearance samples do not match the held-out endpoint measurements")
    if (clearance < 0).sum(axis=0).tolist() != [159, 137]:
        raise ValueError("Unexpected negative-clearance counts")
    return np.linalg.norm(goals, axis=1), errors, clearance


def panels(figure, *, left=.09, left_width=.415, second=.57, right=.98, bottom=.23, top=.75):
    axes = [
        figure.add_axes([start, bottom, width, top - bottom])
        for start, width in ((left, left_width), (second, right - second))
    ]
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(length=2.3, width=.6)
        axis.set_axisbelow(True)
    return axes


def panel_title(axis, title, detail):
    axis.text(0, 1.23, title, transform=axis.transAxes, size=11, weight="bold", va="bottom")
    axis.text(0, 1.09, detail, transform=axis.transAxes, size=8.5, color=SLATE, va="bottom")


def progress_and_clearance(figure, distances, errors, clearance):
    initial, refined = errors[0], errors[14]
    left, right = panels(figure, second=.695)
    closer = (refined < initial).sum()
    panel_title(left, "(a) Goal progress", f"{closer} of {len(initial)} endpoints moved closer")
    limit = 5 * np.ceil(max(initial.max(), refined.max()) / 5)
    left.plot([0, limit], [0, limit], color=SLATE, ls=(0, (3, 3)), lw=.8, zorder=1)
    left.scatter(initial, refined, s=9, facecolor=ORANGE, edgecolor="none", alpha=.67, zorder=2)
    left.text(.025, .93, f"Median error\n{np.median(initial):.2f} → {np.median(refined):.2f} m",
              transform=left.transAxes, va="top", linespacing=1.2, size=8.5,
              bbox=dict(facecolor=WHITE, edgecolor="none", pad=.75))
    left.text(.93, .93, "No change", transform=left.transAxes, ha="right", va="bottom",
              color=SLATE, size=7.8)
    left.set(xlim=(-.65, limit), ylim=(-.65, limit), xticks=np.arange(0, limit + 1, 5),
             yticks=np.arange(0, limit + 1, 5), xlabel="Initial endpoint error (m)",
             ylabel="Endpoint error after 14 updates (m)")
    left.grid(axis="y", color=GRID, lw=.6)

    panel_title(right, "(b) Clearance at equal progress", f"{len(clearance)} pairs · map samples ≥2 m ahead")
    counts = (clearance < 0).sum(axis=0)
    rates = 100 * counts / len(clearance)
    right.barh([1, 0], rates, color=[WHITE, ORANGE], edgecolor=[SLATE, ORANGE],
               height=.32, linewidth=1.2)
    right.set(xlim=(0, 81), ylim=(-.55, 1.55), xticks=[0, 20, 40, 60, 80],
              yticks=[1, 0], yticklabels=["Straight path", "GEAR-Nav"],
              xlabel="Paths with negative\nfootprint clearance (%)")
    right.tick_params(axis="y", length=0, pad=5)
    right.spines["left"].set_visible(False)
    right.grid(axis="x", color=GRID, lw=.6)
    for row, rate in zip([1, 0], rates, strict=True):
        right.text(rate + 2, row, f"{rate:.1f}%", va="center", size=8.8, weight="bold")


def horizon(figure, distances, errors, clearance):
    within = distances <= MAX_PATH_M
    left, right = panels(figure, left=.20, left_width=.36, second=.62)
    comparisons = [
        (left, "(a) Goals within 15 m", f"{within.sum()} pairs · lower is better",
         "Remaining endpoint error (m)", [errors[depth][within] for depth in (0, 14)]),
        (right, "(b) Goals beyond 15 m", f"{(~within).sum()} pairs · higher is better",
         "Goal distance gained (m)", [(distances - errors[depth])[~within] for depth in (0, 14)]),
    ]
    for axis, title, detail, xlabel, values in comparisons:
        panel_title(axis, title, detail)
        axis.set(xlim=(-.2, 16), ylim=(-.48, 1.68), xticks=[0, 4, 8, 12, 16],
                 yticks=[1, 0], xlabel=xlabel)
        axis.set_yticklabels(["Initial path", "After 14 updates"] if axis is left else [])
        axis.tick_params(axis="y", length=0, pad=6)
        axis.spines["left"].set_visible(False)
        axis.grid(axis="x", color=GRID, lw=.6)
        for y, color, measurements in zip([1, 0], [SLATE, ORANGE], values, strict=True):
            low, median, high = np.percentile(measurements, [25, 50, 75])
            axis.hlines(y, low, high, color=color, alpha=.6, lw=2)
            axis.scatter(median, y, s=28, facecolor=WHITE if y == 1 else color,
                         edgecolor=color, linewidth=1, zorder=3)
            axis.annotate(f"{median:.2f} m", (median, y), xytext=(0, 8),
                          textcoords="offset points", ha="center", color=color, weight="bold", size=8.5)
    figure.text(.20, .047, "Dots show the median. Lines span the middle 50% of pairs.", color=SLATE, size=8)


def refinement_budget(figure, distances, errors, clearance):
    left, right = panels(figure, second=.605)
    panel_title(left, "(a) Endpoint error by update count", f"Same {len(distances)} held-out frame–goal pairs")
    low, median, high = np.percentile(np.stack([errors[step] for step in DEPTHS]), [25, 50, 75], axis=1)
    for step, lo, center, hi in zip(DEPTHS, low, median, high, strict=True):
        color = ORANGE if step == 14 else SLATE
        left.vlines(step, lo, hi, lw=1.8, alpha=.65, color=color)
        left.scatter(step, center, s=27, facecolor=color if step == 14 else WHITE,
                     edgecolor=color, zorder=3, linewidth=1)
        if step in (0, 14):
            left.annotate(f"{center:.2f} m", (step, center), xytext=(5, 1),
                          textcoords="offset points", color=color, weight="bold", size=8)
    left.set(xlim=(-2.5, 33), ylim=(0, 17), xticks=DEPTHS, yticks=[0, 4, 8, 12, 16],
             xlabel="Learned updates", ylabel="Endpoint error (m)")
    left.grid(axis="y", color=GRID, lw=.6)
    figure.text(.09, .047, "Dots show the median. Lines span the middle 50% of pairs.", color=SLATE, size=8)

    gain_cm = 100 * (errors[14] - errors[30])
    paired_median = float(np.median(gain_cm))
    panel_title(right, "(b) From 14 to 30 updates", f"{(gain_cm < 0).sum()} farther · {(gain_cm > 0).sum()} closer")
    limit = 50 * int(np.ceil(np.max(np.abs(gain_cm)) / 50))
    edges = np.arange(-limit, limit + 10, 10)
    right.hist(gain_cm, bins=edges, color="#D8D3CD", ec=WHITE, linewidth=.6)
    right.axvline(0, color=INK, linewidth=.7)
    right.axvline(paired_median, color=ORANGE, ls=(0, (2, 2)), linewidth=1.3)
    right.annotate(f"{paired_median:+.0f} cm median", xy=(paired_median, 71), xytext=(19, 70),
                   arrowprops=dict(arrowstyle="-", color=ORANGE, lw=.7),
                   va="center", color=ORANGE, weight="bold", size=8.5)
    right.set(xlim=(-limit, limit), ylim=(0, 80), xticks=np.arange(-limit, limit + 1, 50),
              yticks=[0, 20, 40, 60, 80], xlabel="Paired reduction in endpoint error (cm)",
              ylabel="Frame–goal pairs")
    right.grid(axis="y", color=GRID, lw=.6)


def main():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": [FONT, "STIXGeneral", "Liberation Serif"],
        "font.size": 9, "axes.labelcolor": INK, "text.color": INK, "axes.edgecolor": SLATE,
        "axes.linewidth": .6, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "gear-figure6-options",
    })
    data = load_measurements()
    drafts = [
        ("progress_and_clearance", "1. Goal progress and clearance", progress_and_clearance),
        ("planning_horizon", "2. Local planning horizon", horizon),
        ("refinement_budget", "3. Refinement budget", refinement_budget),
    ]
    overview = plt.figure(figsize=(8.4, 10.2), facecolor=WHITE)
    for (name, title, render), subfigure in zip(drafts, overview.subfigures(3, 1), strict=True):
        figure = plt.figure(figsize=(7.08, 2.72), facecolor=WHITE)
        render(figure, *data)
        for filetype, metadata in (("pdf", {"CreationDate": None}), ("svg", {"Date": None}), ("png", {})):
            figure.savefig(HERE / f"{name}.{filetype}", dpi=240, metadata=metadata)
        svg = HERE / f"{name}.svg"
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
        plt.close(figure)
        render(subfigure, *data)
        subfigure.text(.04, .986, title, size=14, va="top", weight="bold", color=INK)
    overview.savefig(HERE / "compare.png", dpi=175)
    plt.close(overview)


if __name__ == "__main__":
    main()
