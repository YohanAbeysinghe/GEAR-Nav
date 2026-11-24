"""Draw the editable training pipeline on the native Figure 2 Canva canvas."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json

import numpy as np

from canva_method import (
    BACKWARD, Diagram, DistanceMap, EXAMPLES, GRAY, HERE, INDICES, INK, INK_LINE,
    MUTED, ORANGE, PANEL_EDGE, SAND, SCALE, TARGET, WAYPOINT_FILL, colorbar,
    correction_arrows, export_pptx, finish_fonts, load_example, path_line,
)

W, H = 1048, 260
LIFT = 19


def inputs(d, data):
    with d.layer("Camera, goal and candidate path", "inputs"):
        d.text(12, 33, "Navigation inputs", 21, True)
        d.image(EXAMPLES / "rainy-sidewalk.jpg", 12, 55, 120, 67.5)
        d.rect(12, 55, 120, 67.5, "none", "#777B7B", 0, .9)
        d.text(62, 148, "RGB image", 15.5, anchor="middle")

        def project(p):
            return 169 - 6.6 * p[1], 124 - 6.6 * p[0]

        xy = [project(p) for p in data["path"]]
        d.line(xy, ORANGE, 2.5).set("data-path-step", "2")
        for i in INDICES:
            d.circle(*xy[i], 2.2, WAYPOINT_FILL, INK, .7)
        d.circle(*xy[0], 2.7, "white", INK, .85)
        d.star(*project(data["goal"]), 5.6)
        d.text(166, 148, "Current path", 15.5, anchor="middle")
        d.star(19, 174, 5.6)
        d.text(32, 180, "Goal", 17, True)
        d.text(12, 200, "Text, image region, waypoint", 15)


def action_head(d):
    x, y = 237, 72
    d.rect(x, y, 137, 66, "#F7F7F7", PANEL_EDGE, 5, 1.1)
    left = [(x + 12, y + 23), (x + 12, y + 43)]
    mid = [(x + 22, y + 14), (x + 22, y + 33), (x + 22, y + 52)]
    right = [(x + 32, y + 23), (x + 32, y + 43)]
    for starts, ends in ((left, mid), (mid, right)):
        for start in starts:
            for end in ends:
                d.line([start, end], "#45484A", .7)
    for p in (*left, *mid, *right):
        d.circle(*p, 2.55, "white", "#3C3F40", .85)
    d.text(x + 42, y + 29, "GEAR VLA", 17.5, True)
    d.text(x + 42, y + 49, "Action head", 15.5)


def training(d, data):
    with d.layer("Model prediction and training loss", "training"):
        d.rect(218, 8, 443, 201, GRAY, PANEL_EDGE, 11, 1.1)
        d.text(233, 34, "GEAR predicts waypoint updates", 21, True)
        action_head(d)
        d.arrow([(191, 105), (236, 105)], INK_LINE, 1.75, head=7).set("data-flow", "inputs-to-head")
        d.text(445, 78, "Updates", 15.5, anchor="middle")
        d.arrow([(375, 91), (515, 91)], INK_LINE, 1.75, head=7).set("data-flow", "prediction-to-path")
        d.text(584, 70, "Updated path", 16.5, True, "middle")
        # The recorded path after one bounded model step, rotated to point right.
        xy = [(529 + 13.2 * p[0], 99 - 13.2 * p[1]) for p in data["next_path"]]
        path_line(d, xy, width=2.65).set("data-path-step", "3")
        for i in INDICES:
            d.circle(*xy[i], 2.4, WAYPOINT_FILL, INK, .75)
        d.circle(*xy[0], 2.9, "white", INK, .85)

        d.circle(457, 91, 2.25, INK_LINE, INK_LINE, 0)
        d.arrow([(457, 91), (457, 154), (498, 154)], INK_LINE, 1.7, head=6.8).set(
            "data-flow", "predictions-to-loss")
        d.rect(500, 137, 147, 34, "#F7F7F7", PANEL_EDGE, 4, 1.05)
        d.text(573.5, 160, "Correction loss", 17, True, "middle")
        d.arrow([(574, 172), (574, 192), (305, 192), (305, 139)], BACKWARD, 1.95,
                "4.8 3.3", head=7.5).set("data-gradient", "correction-loss-to-action-head")
        d.text(405, 183, "Loss gradient", 15.5, anchor="middle", color=BACKWARD)


def oracle(d, data):
    with d.layer("Energy supervision in the scene's distance field", "energy-oracle"):
        d.rect(672, 8, 368, 201, SAND, PANEL_EDGE, 11, 1.1)
        d.text(687, 33, "Energy oracle", 21, True)
        d.text(1024, 32, "Training only", 15.5, anchor="end", color="#62471F")
        d.text(687, 54, "Map, goal, robot radius and current path", 15.5, color=MUTED)
        field = DistanceMap(data)
        project = field.plane(d, (895, 62), (132, 33), (-141, 71))

        def raised(p):
            return project(p) - np.array([0., LIFT])

        d.star(*project(data["goal"]), 5.5)
        for i in INDICES:
            p = data["path"][i]
            d.line([raised(p), project(p)], INK, 1.15, "1.7 2.2").set("data-projected-waypoint", str(i))
            d.circle(*project(p), 2.05, "white", INK, .8)
        path_line(d, [raised(p) for p in data["path"]], width=2.75).set("data-oblique-path-step", "2")
        correction_arrows(d, data["path"], data["target"], raised)

        d.text(724, 145, "Targets", 15.5, anchor="middle", color=TARGET)
        d.arrow([(827, 154), (648, 154)], TARGET, 2.1, head=7.5).set("data-flow", "oracle-targets-to-loss")
        d.text(688, 190, "ESDF (m)", 16, True)
        colorbar(d, 797, 173, 211, 8)


def deployment(d):
    with d.layer("Repeated model updates on the robot", "deployment"):
        d.rect(8, 219, 1032, 33, "#F2F2F2", "#A0A1A0", 5, 1)
        d.text(21, 242, "On the robot", 18, True)
        d.line([(146, 226), (146, 245)], "#989B9B", 1)
        d.text(166, 242, "Camera + goal + sampled path", 17)
        d.arrow([(414, 236), (456, 236)], INK_LINE, 1.8, head=7)
        d.text(472, 242, "Trained GEAR", 17, True)
        d.arrow([(603, 236), (645, 236)], INK_LINE, 1.8, head=7)
        d.text(662, 242, "Apply a bounded update and repeat", 17)


def build():
    data, proof = load_example("rainy-sidewalk")
    photo = EXAMPLES / "rainy-sidewalk.jpg"
    if sha256(photo.read_bytes()).hexdigest() != proof["files_sha256"][photo.name]:
        raise ValueError("The photo must match the rainy-sidewalk ESDF and path.")
    d = Diagram(W, H, "How GEAR learns a waypoint update",
                "The camera image, goal and current path feed a navigation VLA. Its predicted waypoint "
                "updates move the path. During training, the energy oracle supplies local targets from "
                "scene geometry. The correction loss sends a gradient back to the model. The robot "
                "repeats bounded model updates.", width_mm=178)
    d.el("metadata").text = json.dumps({**proof["figure_2"], "esdf_range_m": [-3, 3],
                                       "display_scale": SCALE, "path_lift_units": LIFT})
    inputs(d, data)
    training(d, data)
    oracle(d, data)
    deployment(d)
    return finish_fonts(d)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", action="store_true")
    args = parser.parse_args()
    svg = HERE / "07-canva-training-pipeline.svg"
    build().export(svg, png_width=2 * W)
    if args.pptx:
        export_pptx(svg, "GEAR training pipeline", W)


if __name__ == "__main__":
    main()
