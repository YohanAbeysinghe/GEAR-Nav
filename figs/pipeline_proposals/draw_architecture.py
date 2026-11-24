"""Render the two-column GEAR correction and replay proposal from a saved training round."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent
sys.path.insert(0, str(FIGS))
from figure_style import COLORS, ESDF_CMAP, ESDF_NORM, INK, ROLE, WAYPOINT_FILL
from svg_diagram import Diagram


ASSETS = FIGS / "pipeline" / "assets"
W, H = 1140, 405
MAP_W, MAP_H = 217, 170
FORWARD_MAX, FORWARD_MIN = 3.62, -0.18
PIXELS_PER_M = MAP_H / (FORWARD_MAX - FORWARD_MIN)
LEFT_MAX = 1.73
VECTOR_SCALE = 0.34
ARROW_WAYPOINTS = (8, 10, 12, 15)
PRIOR, ORANGE, TARGET = "#535E6C", COLORS[14], "#075E63"
MUTED, TRAINING = "#485661", "#895214"


def read_example():
    cache = ASSETS / "aggregation_replay.npz"
    proof = json.loads(cache.with_suffix(".json").read_text())
    if hashlib.sha256(cache.read_bytes()).hexdigest() != proof["cache_sha256"]:
        raise ValueError("The figure requires the matched aggregation replay archive.")
    with np.load(cache) as capture:
        return {key: capture[key] for key in capture.files}, proof


def map_point(x, y, point):
    forward, left = point
    return x + (LEFT_MAX - left) * PIXELS_PER_M, y + (FORWARD_MAX - forward) * PIXELS_PER_M


def field_crop(data):
    """Sample the same forward-up, equal-aspect robot frame for both plots."""
    oversample = 3
    u, v = np.meshgrid(
        (np.arange(MAP_W * oversample) + 0.5) / oversample,
        (np.arange(MAP_H * oversample) + 0.5) / oversample,
    )
    forward = FORWARD_MAX - v / PIXELS_PER_M
    left = LEFT_MAX - u / PIXELS_PER_M
    cols = (forward - float(data["x_min"])) / float(data["resolution"]) - 0.5
    rows = (left - float(data["y_min"])) / float(data["resolution"]) - 0.5
    values = map_coordinates(data["esdf"], [rows, cols], order=1, mode="constant", cval=np.nan)
    rgb = np.uint8(ESDF_CMAP(ESDF_NORM(values))[:, :, :3] * 255)
    rgb[~np.isfinite(values)] = (247, 247, 247)
    return Image.fromarray(rgb)


def draw_map(d, data, field, x, y, depth):
    row = data["depths"].tolist().index(depth)
    prior = data["paths"][data["depths"].tolist().index(0)]
    path = data["paths"][row]

    def pt(point):
        return map_point(x, y, point)

    with d.layer(f"Replay depth {depth}", f"round-{depth + 1}"):
        d.image(field, x, y, MAP_W, MAP_H)
        d.rect(x, y, MAP_W, MAP_H, "none", "#979C9D", 0, 0.9)
        points = [pt(p) for p in prior]
        d.line(points, "white", 4.3)
        d.line(points, PRIOR, 2.3, "5 4").set("data-path-depth", "0")
        current_color = PRIOR if depth == 0 else ORANGE
        if depth:
            points = [pt(p) for p in path]
            d.line(points, "white", 6)
            d.line(points, ORANGE, 3.8).set("data-path-depth", str(depth))
        for index in (2, 5, 8, 10, 12, 15):
            d.circle(*pt(path[index]), 2.6, WAYPOINT_FILL if depth else "white", current_color, 1.1)
        for index in ARROW_WAYPOINTS:
            start = path[index]
            end = start + VECTOR_SCALE * data["directions"][row, index]
            a, b = pt(start), pt(end)
            length = float(np.linalg.norm(np.subtract(b, a)))
            head = min(8, length * 0.5)
            d.arrow([a, b], "white", 4.2, head=head + min(1.2, head / 3))
            vector = d.arrow([a, b], TARGET, 2.5, head=head)
            vector.set("data-oracle-at-depth", str(depth))
            vector.set("data-waypoint", str(index))
        d.circle(*pt(path[0]), 4.0, "white", INK, 1.4)
        d.star(*pt(data["goal"]), 8)
        if depth == 0:
            middle_of_arrow = path[12] + 0.75 * VECTOR_SCALE * data["directions"][row, 12]
            d.text(x + 9, y + 62, "Oracle", 18.5, color=TARGET)
            d.text(x + 9, y + 81, "target", 18.5, color=TARGET)
            d.line([(x + 64, y + 70), (x + 86, y + 70), pt(middle_of_arrow)], TARGET, 1)
            # The physical scale bar sits away from the data in the lower-right corner.
            bx, by = x + MAP_W - 12, y + MAP_H - 15
            d.line([(bx - PIXELS_PER_M, by), (bx, by)], "white", 4.6)
            d.line([(bx - PIXELS_PER_M, by), (bx, by)], INK, 2.1)
            d.text(bx - PIXELS_PER_M / 2, by - 5, "1 m", 17.5, anchor="middle")
        else:
            tip = path[12] + VECTOR_SCALE * data["directions"][row, 12]
            d.text(x + 128, y + 47, "New target", 18.5, color=TARGET)
            d.line([(x + 131, y + 53), (x + 111, y + 53), pt(tip)], TARGET, 1)


def draw_model(d, data):
    with d.layer("Observation, goal and current path", "inputs"):
        d.text(24, 64, "RGB observation", 20)
        d.image(ASSETS / "aggregation_replay_rgb.jpg", 24, 73, 162, 91.125)
        d.rect(24, 73, 162, 91.125, "none", "#858B8F", 0, 0.9)
        x_goal, y_goal = data["goal"]
        d.text(24, 190, f"Goal  ({x_goal:.2f}, {y_goal:.2f}) m".replace("-", "−"), 18.5)
        d.text(24, 229, "Current path", 20, True)
        path = data["paths"][data["depths"].tolist().index(0)]
        points = [(47 - 20 * left, 278 - 20 * forward) for forward, left in path]
        d.line(points, PRIOR, 2.1, "4 3")
        for index in (3, 6, 9, 12, 15):
            d.circle(*points[index], 2.2, "white", PRIOR, 1.0)
        d.circle(*points[0], 3.3, "white", INK, 1.1)
        d.arrow([(88, 252), (243, 252)], width=1.9, head=7)
        d.line([(190, 182), (201, 182), (201, 112)], width=1.7)
        d.circle(201, 112, 2.6, INK, INK, 0)
        d.arrow([(188, 112), (247, 112)], width=1.9, head=7)

    with d.layer("GEAR correction model", "gear-model"):
        d.rect(249, 79, 172, 58, "#EAF0F4", "#8594A2", 4, 1.2)
        d.text(335, 105, "Vision–language", 21, True, "middle")
        d.text(335, 128, "π₀.₅ backbone", 21, True, "middle")
        d.arrow([(335, 138), (335, 160)], width=1.8, head=6.5)
        # Token colors identify the two input modalities. The drawn count is illustrative.
        for index, role in enumerate(("input", "input", "input", "input", "goal")):
            fill, edge = ROLE[role]
            d.rect(295 + index * 17, 164, 14, 13, fill, edge, 1.2, 1)
        d.arrow([(335, 181), (335, 217)], width=1.9, head=7)
        d.text(346, 202, "Context tokens", 17.5, color=MUTED)
        d.rect(244, 217, 185, 62, ROLE["learned"][0], ROLE["learned"][1], 7, 1.5)
        d.text(336, 244, "Waypoint expert", 22, True, "middle")
        d.text(336, 266, "2D correction head", 18.5, anchor="middle")


def draw_flow(d):
    with d.layer("Advance the path and learn from replay", "training-flow"):
        # The learned field enters the update operation, alongside the current path.
        d.arrow([(430, 248), (460, 248), (460, 286), (807, 286), (807, 191)],
                width=2.0, head=8)
        d.text(603, 279, "Predicted correction", 18.5, anchor="middle")
        d.arrow([(730, 164), (746, 164)], width=2.1, head=7.5)
        d.text(738, 155, "x₀", 17.5, anchor="middle")
        d.rect(746, 139, 122, 52, "#FFF9EC", "#C6A468", 5, 1.2)
        d.text(807, 161, "Bounded step", 18, True, "middle")
        d.text(807, 182, "Energy check", 17.5, anchor="middle")
        d.arrow([(868, 164), (891, 164)], width=2.1, head=7.5)
        d.text(879, 155, "x₁", 17.5, anchor="middle")

        # Training flows back from collected examples to the trainable model parameters.
        dash = "6 5"
        d.arrow([(1043, 253), (1043, 334), (858, 334)], TRAINING, 2.0, dash, 8)
        d.rect(601, 315, 256, 39, ROLE["replay"][0], ROLE["replay"][1], 5, 1.1)
        d.text(729, 341, "Replay from all rounds", 21, True, "middle")
        d.arrow([(600, 334), (335, 334), (335, 304)], TRAINING, 2.0, dash, 8)
        d.text(468, 327, "Fit to oracle targets", 18.5, anchor="middle", color=TRAINING)
        d.text(951, 327, "Store path + target", 18.5, anchor="middle", color=TRAINING)


def draw_legend(d):
    with d.layer("Path and distance keys", "legend"):
        d.line([(15, 368), (1125, 368)], "#D0D2D1", 1.1)
        y = 387
        d.line([(24, y), (59, y)], PRIOR, 2.3, "5 4")
        d.text(67, y + 6, "Prior", 18.5)
        d.line([(148, y), (185, y)], ORANGE, 3.4)
        d.circle(167, y, 2.8, WAYPOINT_FILL, ORANGE, 1.2)
        d.text(194, y + 6, "Updated path", 18.5)
        d.circle(354, y, 4, "white", INK, 1.4)
        d.text(370, y + 6, "Robot origin", 18.5)
        d.star(558, y, 7.5)
        d.text(574, y + 6, "Goal", 18.5)
        d.text(741, y + 6, "ESDF (m)", 18.5, color=MUTED)
        d.text(858, y + 6, "−3", 18.5, anchor="end")
        colors = np.uint8(ESDF_CMAP(np.linspace(0, 1, 256))[None, :, :3] * 255)
        d.image(Image.fromarray(colors), 867, y - 4, 145, 9, fit="none")
        d.line([(939.5, y - 5), (939.5, y + 6)], "#666666", 0.8)
        d.text(1020, y + 6, "+3", 18.5)


def main():
    data, proof = read_example()
    d = Diagram(W, H, "GEAR correction model and energy-based aggregation",
                "The same recorded scene and goal at two consecutive training rounds. "
                "Black arrows carry data and the dashed return carries replay supervision.", width_mm=178)
    d.el("metadata").text = json.dumps({
        "scene": proof["scene"], "cache": "../pipeline/assets/aggregation_replay.npz",
        "cache_sha256": proof["cache_sha256"], "archive_depths": [0, 1],
        "oracle_vector_display_scale": VECTOR_SCALE, "vector_waypoints": ARROW_WAYPOINTS,
        "map_orientation": "forward up, robot left to page left",
    })
    with d.layer("Model and training regions", "regions"):
        d.rect(8, 7, 456, 296, "#F5F7F8", "#B4BEC5", 9, 1.15)
        d.rect(481, 7, 651, 296, "#FFF9EF", "#CDBA98", 9, 1.15)
        d.text(24, 37, "GEAR correction model", 26, True)
        d.text(501, 37, "Energy-based aggregation", 26, True)
        d.text(1112, 35, "Training only", 19, anchor="end", color=TRAINING)
        d.text(620, 72, "Round 1 · Prior path", 20.5, True, "middle")
        d.text(1000, 72, "Round 2 · Model path", 20.5, True, "middle")
    draw_model(d, data)
    field = field_crop(data)
    draw_map(d, data, field, 512, 82, 0)
    draw_map(d, data, field, 892, 82, 1)
    draw_flow(d)
    draw_legend(d)
    d.export(HERE / "06-correction-and-replay.svg", png_width=2100)


if __name__ == "__main__":
    main()
