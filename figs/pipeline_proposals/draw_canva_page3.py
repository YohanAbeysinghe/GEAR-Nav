"""Render the GEAR training diagram for page 3 of the Canva design."""

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
    PRIOR,
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
MAP_SCALE = .655
MAP_Y = 54
ROUND_X = (212, 520)
MAP_WIDTH = MAP_W * MAP_SCALE
MAP_HEIGHT = MAP_H * MAP_SCALE
ROUND2_LABEL_WAYPOINT = 12
TEAL_DARK = "#134B52"
MUTED = "#464F57"
CONNECTOR = "#242F37"
TRAINING_FILL = "#D5D5D5"
ESDF_PANEL = "#F1E1C8"
ORACLE_FILL = "#FAEAD0"
GRADIENT = "#B84C09"
REPLAY_EDGE = "#9676AB"


def title(d, x, y, label, width=None, **kwargs):
    d.text(x, y, label, 19, True, max_width=width, **kwargs)


def draw_inputs(d, prior):
    with d.layer("Image, goal and starting path", "inputs"):
        title(d, 21, 30, "Image and goal", 140)
        d.image(ASSETS / "aggregation_replay_rgb.jpg", 21, 42, 140, 78.75)
        d.rect(21, 42, 140, 78.75, "none", "#8F9DA7", 0, .8)
        d.star(26, 137, 6)
        d.text(38, 142, "Goal", 16, True)
        d.text(21, 161, "Text · Image region", 15, max_width=140)
        d.text(21, 178, "Waypoint", 15)

        points = [(24 + 21 * forward, 195 - 6 * left) for forward, left in prior]
        d.line(points, PRIOR, 1.8, "4 3")
        d.circle(*points[0], 3, "white", INK, 1)
        d.text(76, 203, "Rough path", 15, max_width=87)
        d.arrow([(155, 197), (179, 197), (179, 109), (212, 109)],
                CONNECTOR, 1.7, head=6.5).set("data-flow", "rough-path-round-1")


def draw_round(d, field, path, directions, goal, depth):
    x = ROUND_X[depth]
    title_text = "Round 1 · Rough path" if depth == 0 else "Round 2 · GEAR’s path"
    color = PRIOR if depth == 0 else ORANGE

    def point(position):
        u, v = map_point(0, 0, position)
        return x + u * MAP_SCALE, MAP_Y + v * MAP_SCALE

    with d.layer(title_text, f"round-{depth + 1}-path"):
        d.text(x + MAP_WIDTH / 2, 48, title_text, 15.5, True, "middle", max_width=170)
        d.image(field, x, MAP_Y, MAP_WIDTH, MAP_HEIGHT)
        d.rect(x, MAP_Y, MAP_WIDTH, MAP_HEIGHT, "none", "#949D9F", 0, .85)
        xy = [point(p) for p in path]
        d.line(xy, "white", 5 if depth else 4)
        d.line(xy, color, 3 if depth else 2.15, None if depth else "5 3").set("data-path-depth", str(depth))
        for index in (2, 5, *ARROW_WAYPOINTS):
            d.circle(*xy[index], 2.05, WAYPOINT_FILL if depth else "white", color, .8)
        d.star(*point(goal), 5.2)
        for index in ARROW_WAYPOINTS:
            origin = xy[index]
            tip = point(path[index] + directions[index] * VECTOR_SCALE)
            length = float(np.linalg.norm(np.subtract(tip, origin)))
            head = min(6.2, length * .64)
            stroke = min(2.25, .8 + length * .34)
            d.arrow([origin, tip], "white", stroke + 1.7, head=head + .75)
            node = d.arrow([origin, tip], TARGET, stroke, head=head)
            node.set("data-target-waypoint", str(index))
            node.set("data-target-depth", str(depth))
        d.circle(*xy[0], 3, "white", INK, 1)
        if depth == 1:
            index = ROUND2_LABEL_WAYPOINT
            tip = point(path[index] + directions[index] * VECTOR_SCALE)
            d.line([tip, (586, 93), (591, 93)], TEAL_DARK, .85)
            d.rect(591, 83, 66, 16, "white", "none", 2).set("opacity", ".85")
            d.text(595, 94.5, "New target", 12.5, color=TEAL_DARK, max_width=59)


def bank(d, x, y, label, membership, fresh):
    fill = "#EEE5F4" if fresh else "#F4EDF7"
    edge = "#815D98" if fresh else REPLAY_EDGE
    card = d.rect(x, y, 106, 18, fill, edge, 3, 1.4 if fresh else 1)
    card.set("data-replay-membership", membership)
    d.text(x + 53, y + 13.8, label, 15, True, "middle", color="#543C64")


def action_head(d, x, y):
    d.rect(x, y, 120, 46, "#E9E9E9", "#595959", 5, 1.15)
    # A small network glyph identifies the learned head.
    left = [(x + 13, y + 17), (x + 13, y + 30)]
    middle = [(x + 24, y + 12), (x + 24, y + 23.5), (x + 24, y + 35)]
    right = [(x + 35, y + 17), (x + 35, y + 30)]
    for starts, ends in ((left, middle), (middle, right)):
        for start in starts:
            for end in ends:
                d.line([start, end], "#484848", .7)
    for point in (*left, *middle, *right):
        d.circle(*point, 2.65, "white", "#3D3D3D", .85)
    d.text(x + 43, y + 20, "GEAR", 16.5, True)
    d.text(x + 43, y + 37, "Action head", 14, max_width=72)


def loss(d, center, suffix, round_id):
    x = center - 60
    d.rect(x, 174, 120, 30, "#F7F7F7", "#6B6B6B", 4, 1)
    d.text(center, 187, "Correction loss", 14.5, True, "middle", max_width=113)
    d.text(center, 199, suffix, 12.4, anchor="middle", color=MUTED)
    d.arrow([(center - 21, 130), (center - 21, 173)], CONNECTOR,
            1.35, head=5.5).set("data-flow", f"round-{round_id}-predictions")
    d.arrow([(center + 16, 173), (center + 16, 130)], GRADIENT, 1.6, "2 3",
            6).set("data-gradient", f"round-{round_id}-correction-loss-to-GEAR")
    d.text(center + 22, 157, "∇L", 14, color=GRADIENT)


def draw_training(d):
    with d.layer("Training on retained examples", "replay"):
        # Each map contributes only its new bank. Round 2 shows both as inputs to training.
        d.arrow([(265, 165.5), (265, 178)], CONNECTOR, 1.45, head=5.5).set("data-flow", "round-1-save-B1")
        d.arrow([(525, 165.5), (525, 201), (539, 201)], CONNECTOR, 1.45,
                head=5.5).set("data-flow", "round-2-save-B2")
        bank(d, 230, 179, "B₁", "round-1:B1", False)
        bank(d, 540, 170, "B₁", "round-2:B1", False)
        bank(d, 540, 192, "B₂", "round-2:B2", True)
        d.text(212, 212, "Saved paths + corrections", 14.2, color=MUTED, max_width=155)

        d.arrow([(337, 188), (371, 188)], CONNECTOR, 1.6, head=5.5).set("data-flow", "B1-to-loss")
        d.line([(647, 179), (656, 179), (656, 201), (647, 201)], CONNECTOR, 1.55)
        d.arrow([(656, 190), (672, 190)], CONNECTOR, 1.6,
                head=5.5).set("data-flow", "B1-B2-to-loss")

    with d.layer("Predict corrections and backpropagate the loss", "model-updates"):
        action_head(d, 372, 83)
        action_head(d, 673, 83)
        loss(d, 432, "Fit Round 1", 1)
        loss(d, 733, "Fit both rounds", 2)
        d.text(432, 74, "Energy-checked step", 14.5, anchor="middle", max_width=124)
        d.text(406, 154, "Predict", 13.5, anchor="end", color=MUTED)
        d.arrow([(356, 109), (371, 109)], CONNECTOR, 1.8, head=6).set("data-flow", "rough-path-to-update")
        d.arrow([(493, 109), (519, 109)], CONNECTOR, 1.8, head=6).set("data-flow", "update-to-round-2")
        d.text(733, 57, "Repeat, then train on", 13.1, anchor="middle", max_width=123)
        d.text(733, 72, "the full dataset", 13.1, anchor="middle", max_width=123)
        d.arrow([(733, 82), (733, 75)], CONNECTOR, 1.3, head=4.6).set("data-flow", "repeat-then-continue")


def draw_oblique_field(d, field, prior):
    """Tilt the shared raster and put each dotted stem over its real waypoint."""
    left, top = 830, 65
    width, height, shear = 164, 72, 31
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

    def project(point):
        u, v = map_point(0, 0, point)
        return left + shear + (u / MAP_W) * width - (v / MAP_H) * shear, top + (v / MAP_H) * height

    with d.layer("Training-only ESDF", "esdf-inset"):
        d.rect(812, 8, 228, 211, ESDF_PANEL, "#282522", 12, 1.15)
        title(d, 825, 30, "Obstacle distance", 145)
        d.text(1028, 48, "Training only", 13.5, anchor="end", color="#75501A", max_width=80)
        d.image(warped, left, top, width + shear, height, fit="none").set("data-map-projection", "oblique")
        d.line(
            [(left + shear, top), (left + shear + width, top),
             (left + width, top + height), (left, top + height), (left + shear, top)],
            "#7D8382", .95,
        )
        for index in ARROW_WAYPOINTS:
            x, y = project(prior[index])
            d.line([(x, y - 25), (x, y)], INK, 1.3, "1 3").set("data-projected-waypoint", str(index))
            d.circle(x, y, 2.45, "white", INK, .85)
        hover = [(x, y - 25) for x, y in map(project, prior)]
        d.line(hover, "white", 4.1)
        d.line(hover, PRIOR, 2.35)
        for index in ARROW_WAYPOINTS:
            d.circle(*hover[index], 2.9, WAYPOINT_FILL, INK, .9)

        colors = np.uint8(ESDF_CMAP(np.linspace(0, 1, 363))[None, :, :3] * 255)
        # Match the displayed aspect ratio so Canva imports the whole scale.
        bar = Image.fromarray(np.repeat(colors, 24, axis=0))
        d.text(827, 157, "ESDF (m)", 14.2, color=MUTED)
        d.image(bar, 896, 149, 121, 8, fit="none").set("data-range-m", "-3,3")
        for x, label in ((896, "−3"), (956.5, "0"), (1017, "+3")):
            d.line([(x, 157), (x, 160)], INK, .8)
            d.text(x, 173, label, 13.5, anchor="middle")

        d.rect(825, 180, 202, 30, ORACLE_FILL, "#A68154", 4, 1)
        d.text(926, 193, "Energy oracle", 15, True, "middle")
        d.text(926, 206, "Map + goal + path → targets", 13.6, anchor="middle", max_width=193)


def draw_deployment(d):
    with d.layer("Model-only path refinement on the robot", "deployment"):
        d.rect(8, 228, 1032, 24, "#F1F1F1", "#A6A6A6", 5, 1)
        d.text(21, 245, "On the robot", 16.5, True)
        d.text(133, 245, "Camera + goal + current path", 16)
        d.arrow([(350, 240), (382, 240)], CONNECTOR, 1.7, head=6)
        d.text(397, 245, "Trained GEAR", 16, True)
        d.arrow([(512, 240), (553, 240)], CONNECTOR, 1.7, head=6)
        d.text(568, 245, "Update path and repeat", 16)


def build():
    data, proof = read_example()
    rgb_hash = hashlib.sha256((ASSETS / "aggregation_replay_rgb.jpg").read_bytes()).hexdigest()
    if rgb_hash not in proof["source_files"].values():
        raise ValueError("The RGB photograph must match the archived training condition.")
    d = Diagram(
        W, H, "GEAR learns to improve its own paths",
        "Two consecutive training rounds from the same recorded condition. "
        "Round 1 trains on B1. Round 2 trains on retained B1 and new B2. "
        "The ESDF inset shows where the starting path queries the map.",
        width_mm=178,
    )
    d.el("metadata").text = json.dumps({
        "scene": proof["scene"],
        "cache": "../pipeline/assets/aggregation_replay.npz",
        "cache_sha256": proof["cache_sha256"],
        "rgb_sha256": rgb_hash,
        "archive_depths": [0, 1],
        "oracle_vector_display_scale": VECTOR_SCALE,
        "esdf_range_m": [-3, 3],
        "oblique_waypoints": list(ARROW_WAYPOINTS),
        "oblique_path_lift_display_units": 25,
        "map_orientation": "forward up, robot left to page left",
        "font_family": FONT_FAMILY,
    })
    with d.layer("Energy-based dataset aggregation", "training-region"):
        d.rect(184, 8, 618, 211, TRAINING_FILL, "#262626", 12, 1.15)
        d.text(196, 30, "GEAR learns from its own paths", 18, True, max_width=280)
        d.arrow([(499, 25), (479, 25)], GRADIENT, 1.6, "2 3", 6).set("data-key", "loss-gradient")
        d.text(506, 30, "Loss gradient", 15.5, color=GRADIENT, max_width=112)
        d.arrow([(620, 25), (642, 25)], TARGET, 1.8, head=6)
        d.text(650, 30, "Waypoint corrections", 15.5, color=TEAL_DARK, max_width=140)
    field = field_crop(data)
    indices = data["depths"].tolist()
    prior = data["paths"][indices.index(0)]
    draw_inputs(d, prior)
    for depth in (0, 1):
        row = indices.index(depth)
        draw_round(d, field, data["paths"][row], data["directions"][row], data["goal"], depth)
    draw_training(d)
    draw_oblique_field(d, field, prior)
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
        export_pptx(svg, "GEAR learns to improve its own paths")


if __name__ == "__main__":
    main()
