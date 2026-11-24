"""Render Figure 2 for the GEAR-Nav Canva design and the paper."""

from __future__ import annotations

import argparse
import hashlib
import json
from math import hypot
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageFont

from draw_architecture import (
    ARROW_WAYPOINTS,
    ASSETS,
    ESDF_CMAP,
    INK,
    MAP_H,
    MAP_W,
    ORANGE,
    TARGET,
    VECTOR_SCALE,
    WAYPOINT_FILL,
    Diagram,
    field_crop,
    map_point,
    read_example,
)


HERE = Path(__file__).resolve().parent
W, H = 1048, 260
FONT_FAMILY = "Arial"
MUTED = "#424950"
CONNECTOR = "#242A30"
TRAINING_FILL = "#DADADA"
ESDF_PANEL = "#F1E1C8"
GRADIENT = "#B64C0B"
PATH_LIFT = 22


def draw_inputs(d, path, goal):
    with d.layer("Camera image, goal and current path", "inputs"):
        d.text(14, 33, "Navigation inputs", 21, True)
        d.image(ASSETS / "aggregation_replay_rgb.jpg", 14, 53, 128, 72)
        d.rect(14, 53, 128, 72, "none", "#899296", 0, .85)
        d.text(78, 148, "Camera image", 16, anchor="middle")

        def project(p):
            forward, left = p
            return 164 - 21.5 * left, 125 - 21.5 * forward

        xy = [project(p) for p in path]
        d.line(xy, ORANGE, 2.75).set("data-path-depth", "0")
        for idx in (3, 6, 9, 12, 15):
            d.circle(*xy[idx], 2.25, WAYPOINT_FILL, INK, .8)
        d.circle(*xy[0], 3, "white", INK, 1)
        d.star(*project(goal), 5.5)
        d.text(189, 148, "Current path", 16, anchor="middle")
        d.star(21, 172, 5.5)
        d.text(34, 178, "Goal", 17, True)
        d.text(14, 199, "Text, image region or waypoint", 15.5)


def draw_training(d):
    with d.layer("Train the GEAR waypoint action head", "training"):
        d.rect(249, 8, 424, 201, TRAINING_FILL, "#3E4142", 12, 1.15)
        d.text(264, 33, "Learn waypoint corrections", 21, True)

        x, y = 268, 70
        d.rect(x, y, 143, 77, "#F4F4F4", "#565B5E", 6, 1.15)
        left = [(x + 13, y + 29), (x + 13, y + 48)]
        middle = [(x + 25, y + 20), (x + 25, y + 38.5), (x + 25, y + 57)]
        right = [(x + 37, y + 29), (x + 37, y + 48)]
        for starts, ends in ((left, middle), (middle, right)):
            for start in starts:
                for end in ends:
                    d.line([start, end], "#474B4C", .85)
        for point in (*left, *middle, *right):
            d.circle(*point, 2.8, "white", "#3D4142", .9)
        d.text(x + 45, y + 35, "GEAR VLA", 17.5, True)
        d.text(x + 45, y + 56, "Action head", 15.5)

        d.rect(540, y, 116, 77, "#F4F4F4", "#565B5E", 6, 1.15)
        d.text(598, 105, "Correction", 18, True, "middle")
        d.text(598, 128, "loss", 18, True, "middle")

        d.arrow([(228, 107), (267, 107)], CONNECTOR, 1.9, head=7).set("data-flow", "inputs-to-head")
        d.text(475, 84, "Prediction", 15.5, anchor="middle")
        d.arrow([(412, 95), (539, 95)], CONNECTOR, 1.9, head=7).set("data-flow", "predictions-to-loss")
        d.arrow([(539, 123), (412, 123)], GRADIENT, 1.95, "5 3.2",
                head=7.5).set("data-gradient", "correction-loss-to-action-head")
        d.text(475, 146, "Loss gradient", 15.5, anchor="middle", color=GRADIENT)
        d.text(264, 191, "Train on paths collected across rounds.", 16, color=MUTED)


def draw_oracle(d, field, path, directions):
    """Project one archived path and its local correction targets over the ESDF."""
    left, top = 804, 72
    width, height, shear = 190, 81, 30
    oversample = 3
    warped = field.convert("RGBA").transform(
        ((width + shear) * oversample, height * oversample),
        Image.Transform.AFFINE,
        (
            field.width / (width * oversample),
            field.width * shear / (width * height * oversample),
            -field.width * shear / width,
            0,
            field.height / (height * oversample),
            0,
        ),
        resample=Image.Resampling.BILINEAR,
    )

    def project(position, above_plane=0):
        u, v = map_point(0, 0, position)
        return (left + shear + width * u / MAP_W - shear * v / MAP_H,
                top + height * v / MAP_H - above_plane)

    with d.layer("Training targets from scene geometry", "energy-oracle"):
        d.rect(684, 8, 356, 201, ESDF_PANEL, "#4E453A", 12, 1.15)
        d.text(700, 33, "Energy oracle", 21, True)
        d.text(1024, 32, "Training only", 15.5, anchor="end", color="#63481F")
        d.text(700, 55, "Map + goal + current path", 15.5, color=MUTED)

        d.image(warped, left, top, width + shear, height, fit="none").set("data-map-projection", "oblique")
        d.line([(left + shear, top), (left + shear + width, top),
                (left + width, top + height), (left, top + height), (left + shear, top)],
               "#858B8F", 1)
        for index in ARROW_WAYPOINTS:
            ground = project(path[index])
            d.line([project(path[index], PATH_LIFT), ground], INK, 1.4, "1.4 2.8").set(
                "data-projected-waypoint", str(index))
            d.circle(*ground, 2.35, "white", INK, .85)

        hover = [project(p, PATH_LIFT) for p in path]
        d.line(hover, "white", 4.8)
        d.line(hover, ORANGE, 2.8).set("data-inset-path-depth", "0")
        d.circle(*hover[0], 2.9, "white", INK, .95)
        for index in ARROW_WAYPOINTS:
            start = hover[index]
            end = project(path[index] + VECTOR_SCALE * directions[index], PATH_LIFT)
            length = hypot(end[0] - start[0], end[1] - start[1])
            head = min(7, .58 * length)
            d.arrow([start, end], "white", 3.9, head=head + 1)
            d.arrow([start, end], TARGET, 2.25, head=head).set("data-target-waypoint", str(index))
            d.circle(*start, 2.6, WAYPOINT_FILL, INK, .85)

        d.text(751, 99, "Target updates", 15.5, anchor="middle", color=TARGET)
        d.arrow([(814, 110), (657, 110)], TARGET, 2, head=7.5).set("data-flow", "oracle-targets-to-loss")

        bar_x, bar_y, bar_w, bar_h = 804, 173, 206, 9
        d.text(700, 184, "ESDF (m)", 16, color=MUTED)
        colors = np.uint8(ESDF_CMAP(np.linspace(0, 1, bar_w * 3))[None, :, :3] * 255)
        bar = Image.fromarray(np.repeat(colors, bar_h * 3, axis=0))
        d.image(bar, bar_x, bar_y, bar_w, bar_h, fit="none").set("data-range-m", "-3,3")
        for x, label in ((bar_x, "−3"), (bar_x + bar_w / 2, "0"), (bar_x + bar_w, "+3")):
            d.line([(x, bar_y + bar_h), (x, bar_y + bar_h + 3)], INK, .9)
            d.text(x, 201, label, 15, anchor="middle")


def draw_deployment(d):
    with d.layer("Model-only path refinement on the robot", "deployment"):
        d.rect(8, 219, 1032, 33, "#F2F2F2", "#A3A6A6", 5, 1)
        d.text(21, 242, "On the robot", 18, True)
        d.line([(145, 226), (145, 245)], "#A1A5A8", 1)
        d.text(164, 242, "Camera + goal + current path", 17)
        d.arrow([(400, 236), (447, 236)], CONNECTOR, 1.8, head=7)
        d.text(466, 242, "Trained GEAR", 17.5, True)
        d.arrow([(600, 236), (647, 236)], CONNECTOR, 1.8, head=7)
        d.text(667, 242, "Update the path and repeat", 17)


def build():
    data, proof = read_example()
    rgb_hash = hashlib.sha256((ASSETS / "aggregation_replay_rgb.jpg").read_bytes()).hexdigest()
    if rgb_hash not in proof["source_files"].values():
        raise ValueError("The RGB photograph must match the archived training condition.")
    row = data["depths"].tolist().index(0)
    path = data["paths"][row]
    d = Diagram(
        W, H, "GEAR learns waypoint corrections",
        "One training example. GEAR predicts waypoint updates from the camera image, goal and "
        "current path. The map-derived energy oracle supplies target updates. The correction "
        "loss trains the action head. On the robot, GEAR repeatedly updates the current path.",
        width_mm=178,
    )
    d.el("metadata").text = json.dumps({
        "scene": proof["scene"],
        "cache": "../pipeline/assets/aggregation_replay.npz",
        "cache_sha256": proof["cache_sha256"],
        "rgb_sha256": rgb_hash,
        "archive_depths": [0],
        "oracle_vector_display_scale": VECTOR_SCALE,
        "esdf_range_m": [-3, 3],
        "oblique_waypoints": list(ARROW_WAYPOINTS),
        "oblique_path_lift_display_units": PATH_LIFT,
        "map_orientation": "forward up, robot left to page left",
        "font_family": FONT_FAMILY,
    })
    draw_inputs(d, path, data["goal"])
    draw_training(d)
    draw_oracle(d, field_crop(data), path, data["directions"][row])
    draw_deployment(d)
    for label in d.root.iter("{http://www.w3.org/2000/svg}text"):
        label.set("font-family", f"{FONT_FAMILY}, Liberation Sans, sans-serif")
    return d


def export_pptx(svg, title_text):
    canva = HERE.parent / "canva"
    sys.path.insert(0, str(canva))
    from editable_pptx import EMU, Slide, figure_name, geometry, numbers, tag
    from lxml import etree
    import pathops
    from pptx.util import Pt

    fallback = {
        bold: ImageFont.truetype(
            f"/usr/share/fonts/liberation-sans/LiberationSans-{weight}.ttf", 512
        )
        for bold, weight in ((False, "Regular"), (True, "Bold"))
    }

    class CanvaSlide(Slide):
        def text(self, node, matrix):
            super().text(node, matrix)
            shape = self.slide.shapes[-1]
            run = shape.text_frame.paragraphs[0].runs[0]
            run.font.name = FONT_FAMILY
            # Canva can substitute a wider font and reflow PowerPoint text boxes.
            width = fallback[bool(run.font.bold)].getlength(run.text) * run.font.size.pt / 512
            extra = max(0, Pt(width + 7) - shape.width)
            anchor = node.get("text-anchor", "start")
            shape.left -= round(extra * {"start": 0, "middle": .5, "end": 1}[anchor])
            shape.width += extra

        def vector(self, node, matrix, opacity, clip):
            if tag(node) != "polyline":
                super().vector(node, matrix, opacity, clip)
                return
            # Filled shapes keep straight strokes and dashes visible in Canva's importer.
            scale = hypot(matrix.xx, matrix.xy)
            stroke = geometry(node, matrix)
            dash = [length * scale for length in numbers(node.get("stroke-dasharray") or "")]
            stroke.stroke(
                float(node.get("stroke-width")) * scale,
                pathops.LineCap.BUTT_CAP,
                pathops.LineJoin.BEVEL_JOIN,
                4,
                dash or None,
            )
            self.freeform(stroke, figure_name(node), node.get("stroke"), "none", 0, {"opacity": opacity})

    with TemporaryDirectory(prefix="gear-canva-fonts-") as temporary:
        with ZipFile(canva / "GEAR-Nav-Canva.zip") as kit:
            for weight in ("Regular", "Bold"):
                kit.extract(f"Fonts/STIXTwoText-{weight}.ttf", temporary)
        root = etree.parse(str(svg)).getroot()
        # Match the Canva page in pixels by writing a 96-dpi slide.
        scale = 9525 / EMU
        root.set("viewBox", f"0 0 {W * scale:g} {H * scale:g}")
        root.set("transform", f"scale({scale:g})")
        slide = CanvaSlide(root, Path(temporary) / "Fonts", title_text)
        slide.save(svg.with_suffix(".pptx"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", action="store_true", help="also export an editable one-page Canva import")
    args = parser.parse_args()
    svg = HERE / "07-canva-training-pipeline.svg"
    build().export(svg, png_width=W * 2)
    if args.pptx:
        export_pptx(svg, "GEAR learns waypoint corrections")


if __name__ == "__main__":
    main()
