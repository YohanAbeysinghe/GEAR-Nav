"""Draw the recorded path progression and retained replay banks on the Figure 3 Canva page."""

from __future__ import annotations

import argparse
import json

from canva_method import (
    Diagram, DistanceMap, GRAY, HERE, INK, INK_LINE, MUTED, ORANGE, PANEL_EDGE,
    SAND, TARGET, WAYPOINT_FILL, colorbar, correction_arrows, export_pptx,
    finish_fonts, load_example, path_line,
)

W, H = 560, 509.2
CENTERS = (104, 280, 456)
BANKS = ("B₁", "B₂", "B₃")


def legend(d):
    d.line([(22, 55), (45, 55)], ORANGE, 3)
    d.circle(35, 55, 2.8, WAYPOINT_FILL, INK, .8)
    d.text(51, 61, "Path", 17)
    d.arrow([(102, 55), (124, 55)], TARGET, 2.25, head=6.5)
    d.text(131, 61, "Oracle update", 17)
    d.star(259, 54, 6.2)
    d.text(271, 61, "Goal", 17)
    d.text(337, 61, "ESDF (m)", 16.5, True)
    colorbar(d, 426, 43, 97, 8, label_size=16.5)


def maps(d, data):
    field = DistanceMap(data)
    for depth, x, path, target in zip(data["depths"], CENTERS, data["paths"], data["targets"]):
        depth = int(depth)
        with d.layer(f"Round {depth + 1}, recorded path and local oracle targets", f"round-{depth + 1}"):
            d.text(x, 91, f"Round {depth + 1}", 20, True, "middle")
            project = field.plane(d, (x - 63, 98), (126, 0), (0, 136.5))
            d.star(*project(data["goal"]), 6.5)
            path_line(d, [project(p) for p in path], width=2.75).set("data-archive-depth", str(depth))
            correction_arrows(d, path, target, project, marker_radius=2.15)
            if depth < len(CENTERS) - 1:
                d.arrow([(x + 67, 166), (CENTERS[depth + 1] - 67, 166)], INK_LINE, 1.75, head=6.5)


def retained_banks(d):
    for depth, x in enumerate(CENTERS):
        with d.layer(f"Replay available at round {depth + 1}", f"retained-round-{depth + 1}"):
            left, top = x - 50, 246
            current_y = top + 20.5 * depth + 9.75
            d.arrow([(left - 10, 237), (left - 10, current_y), (left - 1, current_y)],
                    INK_LINE, 1.3, head=4.8)
            for previous in range(depth + 1):
                new = previous == depth
                y = top + 20.5 * previous
                d.rect(left, y, 102, 19.5, SAND if new else "#EDEDED", "#775943" if new else "#9A9B9B",
                       2, 1.1 if new else .85).set("data-retained-bank", str(previous + 1))
                d.text(x + 1, y + 15.7, BANKS[previous] + ("   New" if new else ""),
                       16.7, new, "middle", color=INK if new else MUTED)
    with d.layer("Fit on retained banks before advancing the paths", "replay-training"):
        d.text(280, 328, "Each bank stores paths and their target waypoint updates.", 17, anchor="middle")
        d.line([(23, 338), (537, 338)], "#AAACAC", 1)
        d.text(132, 358, "Fit GEAR on all saved banks", 16.75, True, "middle")
        d.arrow([(252, 352), (278, 352)], INK_LINE, 1.85, head=7)
        d.text(410, 358, "Take an energy-checked step", 16.75, True, "middle")


def full_dataset(d):
    with d.layer("Training on the full set of images and goals", "full-dataset"):
        d.rect(7, 374, 268, 128, SAND, PANEL_EDGE, 8, 1.1)
        d.text(20, 399, "Full-dataset training", 20.5, True)
        lines = ("Sample images and goals", "Sample depth, generate paths", "Fit GEAR to oracle targets")
        for i, label in enumerate(lines):
            y = 426 + 31 * i
            d.circle(23, y - 5, 2.1, INK_LINE, INK_LINE, 0)
            d.text(34, y, label, 16.7)
            if i < len(lines) - 1:
                d.arrow([(23, y - 1), (23, y + 21)], INK_LINE, 1.3, head=4.8)


def energy_plot(d, data):
    with d.layer("Measured mean energy over all archived training paths", "energy-plot"):
        d.rect(282, 374, 271, 128, "#F5F5F3", PANEL_EDGE, 8, 1.1)
        d.text(295, 399, "Mean path energy", 20.5, True)
        d.text(295, 418, f"{int(data['paths_per_round']):,} paths per round", 16.5, color=MUTED)
        left, right, bottom = 327, 535, 477
        energy = data["mean_energy"]
        def point(i, e):
            return left + (right - left) * i / (len(energy) - 1), bottom - e * 4.7
        for value in (0, 10):
            _, y = point(0, value)
            d.line([(left, y), (right, y)], "#A6ABAC", 1.0, "2 3" if value else None)
            d.text(left - 8, y + 5.5, str(value), 16.5, anchor="end", color=MUTED)
        d.line([(left, point(0, 11)[1]), (left, bottom)], "#A6ABAC", 1.0)
        xy = [point(i, e) for i, e in enumerate(energy)]
        d.line(xy, INK_LINE, 1.9).set("data-energy-series", "0-through-14")
        for i, pos in enumerate(xy):
            featured = i in (0, len(xy) - 1)
            d.circle(*pos, 2.7 if featured else 1.55, WAYPOINT_FILL if featured else INK_LINE, INK_LINE, .8)
        for i in (0, len(energy) - 1):
            x, _ = xy[i]
            d.line([(x, bottom), (x, bottom + 3)], "#707474", .9)
            d.text(x, 496, str(i), 16.5, anchor="middle")
        d.text((left + right) / 2, 496, "Round", 16.5, anchor="middle")


def build():
    data, proof = load_example("ottawa-replay")
    d = Diagram(W, H, "How the GEAR training set grows",
                "Three consecutive rounds for a fixed training image, goal and start. Each round "
                "labels the current path, adds a new bank, fits on all accumulated banks and advances "
                "the path with an energy check. The lower panels show full-dataset training and the measured mean "
                "path energy across all 14 aggregation rounds.",
                width_mm=86)
    d.el("metadata").text = json.dumps({**proof["figure_3"], "esdf_range_m": [-3, 3],
                                       "map_projection": "equal metric scale, robot-forward up",
                                       "retained_banks": [[1], [1, 2], [1, 2, 3]]})
    with d.layer("Aggregation of labelled paths", "aggregation"):
        d.rect(7, 7, 546, 360, GRAY, PANEL_EDGE, 8, 1.1)
        d.text(21, 33, "Growing the training set", 22, True)
        d.text(538, 32, "Same image, goal and start", 16.7, anchor="end", color=MUTED)
        legend(d)
    maps(d, data)
    retained_banks(d)
    full_dataset(d)
    energy_plot(d, data)
    return finish_fonts(d)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", action="store_true")
    args = parser.parse_args()
    svg = HERE / "08-canva-aggregation.svg"
    build().export(svg, png_width=1400)
    if args.pptx:
        export_pptx(svg, "GEAR dataset aggregation", 1400)


if __name__ == "__main__":
    main()
