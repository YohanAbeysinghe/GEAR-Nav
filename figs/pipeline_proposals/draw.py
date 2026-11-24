"""Five schematic GEAR-Nav pipeline studies. Run with .venv/bin/python."""

from __future__ import annotations

from math import atan2
from math import cos
from math import pi
from math import sin
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

from PIL import Image

OUT = Path(__file__).resolve().parent
W, H = 1160, 500
INK, MUTED, LINE = "#232931", "#505b65", "#c8cdd1"
ORANGE, TARGET, GOLD = "#e25b19", "#116575", "#ffc52f"
BLUE, AMBER, PURPLE, PEACH = "#e8f0fc", "#fff0cc", "#eee7f3", "#fae3de"
GRAY = "#54606e"
FONT = "STIX Two Text, Liberation Serif, Times New Roman, serif"
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def el(name, **attrs):
    return ET.Element(name, {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def group(parent, name=None, **attrs):
    if name:
        attrs["id"] = name
    node = el("g", **attrs)
    parent.append(node)
    return node


def add(g, tag, **attrs):
    node = el(tag, **attrs)
    g.append(node)
    return node


def txt(g, x, y, value, size=19, bold=False, anchor="start", color=INK, italic=False):
    node = add(
        g,
        "text",
        x=x,
        y=y,
        font_size=size,
        font_weight="bold" if bold else "normal",
        text_anchor=anchor,
        fill=color,
        font_style="italic" if italic else "normal",
    )
    node.text = value


def rect(g, x, y, w, h, fill="white", stroke=LINE, r=3, sw=1.2):
    return add(g, "rect", x=x, y=y, width=w, height=h, rx=r, fill=fill, stroke=stroke, stroke_width=sw)


def pts(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def line(g, points, color=INK, sw=1.8, dash=None):
    attr = dict(
        points=pts(points), fill="none", stroke=color, stroke_width=sw, stroke_linejoin="round", stroke_linecap="round"
    )
    if dash:
        attr["stroke_dasharray"] = dash
    return add(g, "polyline", **attr)


def arrow(g, points, color=INK, sw=1.9, head=8):
    line(g, points, color, sw)
    (px, py), (x, y) = points[-2:]
    angle = atan2(y - py, x - px)
    dx, dy = head * cos(angle), head * sin(angle)
    add(
        g,
        "polygon",
        points=pts([(x, y), (x - dx - dy * 0.45, y - dy + dx * 0.45), (x - dx + dy * 0.45, y - dy - dx * 0.45)]),
        fill=color,
    )


def circle(g, x, y, r, fill="white", stroke=INK, sw=1):
    return add(g, "circle", cx=x, cy=y, r=r, fill=fill, stroke=stroke, stroke_width=sw)


def star(g, x, y, r=8):
    vertices = []
    for i in range(10):
        a = i * pi / 5 - pi / 2
        radius = r if i % 2 == 0 else 0.44 * r
        vertices.append((x + radius * cos(a), y + radius * sin(a)))
    add(g, "polygon", points=pts(vertices), fill=GOLD, stroke=INK, stroke_width=1.2)


def box(g, x, y, w, h, title, detail="", fill="white"):
    rect(g, x, y, w, h, fill)
    center = x + w / 2
    txt(g, center, y + h / 2 + (1 if detail else 6), title, 20, True, "middle")
    if detail:
        txt(g, center, y + h / 2 + 20, detail, 16, anchor="middle", color=MUTED)


def note(g, x, y, title, *lines):
    txt(g, x, y, title, 22, True)
    for i, s in enumerate(lines):
        txt(g, x, y + 28 + i * 23, s, 18, color=MUTED)


def head(g, x, y, s):
    txt(g, x, y, s, 23, True)


def scene(g, x, y, w):
    """Draw the same symbolic camera view everywhere, with a pillar and doorway."""
    a = group(g, transform=f"translate({x} {y}) scale({w / 200})")

    def polygon(p, fill):
        add(a, "polygon", points=pts(p), fill=fill)

    rect(a, 0, 0, 200, 126, "#ebefed", "none", 0)
    polygon([(0, 0), (83, 38), (83, 73), (0, 126)], "#bdc8cb")
    polygon([(200, 0), (124, 38), (124, 73), (200, 126)], "#d8c7ac")
    polygon([(0, 126), (83, 70), (124, 70), (200, 126)], "#efe4d2")
    rect(a, 83, 38, 41, 34, "#e2e6e0", "none", 0)
    rect(a, 107, 43, 13, 28, "#82928d", "none", 0)
    rect(a, 109, 45, 9, 26, "#556767", "none", 0)
    for p in [
        [(8, 126), (88, 73)],
        [(72, 126), (98, 73)],
        [(161, 126), (114, 73)],
        [(200, 115), (123, 73)],
        [(27, 107), (176, 107)],
        [(57, 88), (148, 88)],
    ]:
        line(a, p, "#c5bba9", 0.8)
    polygon([(23, 8), (31, 12), (31, 104), (23, 110)], "#a2b0b4")
    polygon([(156, 23), (168, 18), (168, 102), (156, 94)], "#b8a78d")
    polygon([(52, 21), (64, 25), (64, 89), (52, 88)], "#889fae")
    polygon([(64, 25), (71, 22), (71, 85), (64, 89)], "#577480")
    star(a, 116, 72, 6)
    rect(a, 0, 0, 200, 126, "none", "#9da7a9", 0)


PATHS = {
    "near": [(99, 117), (91, 102), (85, 88), (84, 72), (86, 57), (98, 44), (116, 34)],
    "away": [(99, 117), (113, 100), (126, 88), (142, 83), (156, 88), (172, 102)],
    "next": [(99, 117), (99, 99), (98, 82), (102, 68), (110, 55), (123, 47)],
    "refined": [(99, 117), (100, 101), (102, 83), (107, 66), (116, 49), (127, 34), (138, 20)],
    "terms": [(99, 117), (113, 105), (98, 91), (85, 76), (85, 63), (96, 53), (116, 39), (128, 67), (143, 47)],
}
VECTOR = {
    "near": [(2, 13, -3), (3, 17, -2), (4, 13, -5)],
    "away": [(3, -2, -13), (4, -7, -16), (5, -13, -18)],
    "next": [(2, 5, -4), (4, 7, -8), (5, 10, -12)],
    "terms": [(3, 13, -3), (4, 16, -1), (7, 0, -15)],
}


def curve(g, points, learned=False, width=2.7):
    color = ORANGE if learned else GRAY
    line(g, points, "white", width + 1.9)
    line(g, points, color, width, None if learned else "4 3")
    for x, y in points[1:]:
        circle(g, x, y, 1.9, GOLD if learned else "#fafafa", color, 0.85)


def draw_field(g, x, y, w, kind="near", vectors=False, learned=False, prior=False, pins=False):
    a = group(g, transform=f"translate({x} {y}) scale({w / 200})")
    rect(a, 0, 0, 200, 132, "url(#open-space)", "none", 2)
    rect(a, 0, 0, 200, 132, "url(#pillar-field)", "none", 2)
    circle(a, 69, 69, 17.5, "none", "#7d97aa", 0.6).set("stroke-dasharray", "2 2")
    circle(a, 69, 69, 11.1, "#667f99", "white", 1.15)
    if prior:
        curve(a, PATHS["near"], width=1.7)
    path = PATHS[kind]
    curve(a, path, learned)
    if vectors:
        for j, dx, dy in VECTOR[kind]:
            px, py = path[j]
            arrow(a, [(px, py), (px + dx, py + dy)], TARGET, 2.2, 5.3)
    circle(a, *path[0], 3, "white", INK, 1)
    star(a, 140, 15, 6.8)
    if pins:
        # The pins sit outside the path; each leader terminates at its feature.
        for n, (lx, ly), (tx, ty) in [
            (1, (39, 71), (82, 73)),
            (2, (163, 30), (139, 43)),
            (3, (164, 76), (126, 61)),
            (4, (76, 118), (106, 111)),
            (5, (89, 27), (116, 39)),
        ]:
            line(a, [(lx, ly), (tx, ty)], INK, 0.85)
            circle(a, lx, ly, 5.6, INK, "white", 0.6)
            txt(a, lx, ly + 3.1, str(n), 9, True, "middle", "white")
    rect(a, 0, 0, 200, 132, "none", "#a4aab1", 2, 0.8)


def glyph(g, x, y, w, mode="candidate"):
    a = group(g, transform=f"translate({x} {y}) scale({w / 110})")
    path = [(3, 36), (20, 31), (37, 27), (54, 22), (71, 20), (88, 18), (104, 17)]
    curve(a, path, mode == "learned", width=2.4)
    if mode in ("target", "prediction"):
        for j in (2, 4, 6):
            px, py = path[j]
            arrow(a, [(px, py), (px + 4, py - 12)], TARGET if mode == "target" else ORANGE, 2.1, 4.6)
    circle(a, *path[0], 2.7, "white", INK, 1)


def target_detail(g, x, y, w, h, kind, learned=False):
    """Show the same oracle arrows as the corresponding map at a closer scale."""
    crop = add(
        g,
        "svg",
        x=x,
        y=y,
        width=w,
        height=h,
        viewBox="60 42 89 53",
        preserveAspectRatio="xMidYMid slice",
        overflow="hidden",
    )
    draw_field(crop, 0, 0, 200, kind, vectors=True, learned=learned)
    rect(g, x, y, w, h, "none", LINE, 0, 0.8)


def base(n, title):
    root = el("svg", xmlns=NS, width="178mm", height=f"{178 * H / W:.3f}mm", viewBox=f"0 0 {W} {H}", font_family=FONT)
    add(root, "title").text = f"GEAR-Nav pipeline concept {n}. {title}"
    add(root, "desc").text = "Layout proposal. All scenes, paths, distance fields and corrections are schematic."
    defs = add(root, "defs")
    grad = add(defs, "linearGradient", id="open-space", x1="0%", x2="100%", y1="0%", y2="13%")
    for pos, c in [("0%", "#c6d4eb"), ("34%", "#f1ede3"), ("76%", "#f3c0a6"), ("100%", "#f3cbb7")]:
        add(grad, "stop", offset=pos, stop_color=c)
    grad = add(defs, "radialGradient", id="pillar-field", cx="34.5%", cy="52.3%", r="51%")
    for pos, c, opacity in [
        ("0%", "#99b3d5", 1),
        ("32%", "#bacfea", 0.92),
        ("60%", "#edf0f1", 0.76),
        ("100%", "#f8e5d7", 0),
    ]:
        add(grad, "stop", offset=pos, stop_color=c, stop_opacity=opacity)
    rect(root, 0, 0, W, H, "white", "none", 0)
    h = group(root, "title-band")
    rect(h, 23, 14, 39, 32, INK, "none", 2)
    txt(h, 42.5, 37, str(n).zfill(2), 22, True, "middle", "white")
    txt(h, 78, 39, title, 32, True)
    txt(h, 1135, 36, "GEAR-Nav  /  Schematic", 17, anchor="end", color=MUTED)
    line(h, [(24, 58), (1136, 58)], LINE, 1.15)
    return root


def footer(root, deployment=True):
    a = group(root, "readout")
    if deployment:
        rect(a, 25, 410, 1110, 36, "#f3f5f4", "none", 3)
        txt(a, 39, 434, "At deployment", 18, True)
        txt(a, 189, 434, "Image, goal and current path", 18)
        arrow(a, [(411, 428), (450, 428)], INK, 1.6, 7)
        txt(a, 474, 434, "GEAR predicts a correction", 18)
        arrow(a, [(695, 428), (733, 428)], INK, 1.6, 7)
        txt(a, 755, 434, "Apply bounded update and repeat", 18)
        glyph(a, 1054, 409, 71, "learned")
    line(a, [(25, 457), (1135, 457)], LINE, 1)
    line(a, [(33, 476), (66, 476)], GRAY, 2.4, "5 4")
    txt(a, 75, 482, "Candidate path", 16)
    line(a, [(224, 476), (259, 476)], ORANGE, 2.7)
    circle(a, 243, 476, 2.8, GOLD, ORANGE, 1)
    txt(a, 271, 482, "Updated path", 16)
    arrow(a, [(428, 479), (460, 471)], TARGET, 2.4, 7)
    txt(a, 472, 482, "Oracle correction", 16)
    star(a, 676, 476, 7)
    txt(a, 691, 482, "Goal", 16)
    txt(a, 1134, 482, "Illustrative paths and fields", 16, anchor="end", color=MUTED, italic=True)


def two_paths():
    r = base(1, "One scene, two paths, two corrections")
    g = group(r, "scene-and-goal")
    head(g, 27, 90, "One observation and goal")
    scene(g, 28, 113, 228)
    txt(g, 28, 285, "Reach the marked doorway.", 19)
    txt(g, 28, 319, "Sample a starting path.", 17, color=MUTED)
    rect(g, 27, 341, 235, 43, AMBER, "none", 3)
    txt(g, 37, 359, "Training-only oracle", 16, True)
    txt(g, 37, 378, "ESDF and goal score each path.", 16)
    g = group(r, "two-candidates")
    head(g, 336, 90, "How should each path change?")
    for y, kind, title, one, two in [
        (107, "near", "Close to the pillar", "Move nearby", "waypoints outward."),
        (243, "away", "Turning away", "Steer the tail back", "toward the goal."),
    ]:
        draw_field(g, 335, y, 181, kind, vectors=True)
        note(g, 537, y + 42, title, one, two)
    line(g, [(260, 188), (294, 188)], INK)
    arrow(g, [(294, 188), (294, 165), (327, 165)])
    arrow(g, [(294, 188), (294, 302), (327, 302)])
    g = group(r, "retention-and-learning")
    head(g, 834, 90, "Learn from both")
    line(g, [(755, 166), (782, 166), (782, 295), (755, 295)], INK)
    arrow(g, [(782, 203), (826, 203)])
    box(g, 834, 169, 280, 66, "Retain both examples", "Candidate + oracle correction", PURPLE)
    arrow(g, [(974, 236), (974, 258)])
    box(g, 834, 263, 280, 66, "Train GEAR", "Sample all retained rounds", PEACH)
    arrow(g, [(974, 330), (974, 392), (429, 392), (429, 369)])
    txt(g, 699, 384, "Updated GEAR proposes the next candidate", 17, anchor="middle")
    footer(r)
    return r


def anatomy():
    r = base(2, "Where a waypoint correction comes from")
    g = group(r, "energy-on-the-path")
    head(g, 25, 91, "Five terms on one candidate")
    draw_field(g, 26, 111, 413, "terms", pins=True)
    labels = [
        ("Footprint clearance", "Gap between robot and pillar"),
        ("Goal progress", "Progress along the path"),
        ("Retreat penalty", "A segment moves away"),
        ("Early heading", "Direction near the origin"),
        ("Path smoothness", "Change between segments"),
    ]
    for i, (title, detail) in enumerate(labels):
        y = 124 + 54 * i
        circle(g, 467, y, 10, INK, "none")
        txt(g, 467, y + 5, str(i + 1), 15, True, "middle", "white")
        txt(g, 485, y + 5, title, 20, True)
        txt(g, 486, y + 26, detail, 17, color=MUTED)
    line(g, [(739, 101), (739, 382)], LINE, 1)
    g = group(r, "energy-to-oracle")
    head(g, 765, 91, "One target per candidate")
    box(g, 768, 107, 362, 55, "Combine terms into E(x)", "Weighted trajectory energy", AMBER)
    arrow(g, [(949, 163), (949, 179)])
    rect(g, 768, 183, 362, 80, "white")
    target_detail(g, 779, 196, 104, 53, "terms")
    txt(g, 896, 213, "Oracle correction", 21, True)
    txt(g, 896, 241, "Scale and check the step.", 17, color=MUTED)
    arrow(g, [(949, 264), (949, 282)])
    box(g, 768, 285, 362, 53, "Retain the labeled path", "Train GEAR on accumulated examples", PURPLE)
    arrow(g, [(1091, 339), (1091, 397), (238, 397), (238, 386)])
    txt(g, 853, 389, "Query the next model-generated candidate", 17, anchor="middle")
    footer(r)
    return r


def rounds():
    r = base(3, "Follow one scene through two training rounds")
    g = group(r, "training-rounds")
    head(g, 234, 89, "Round 1")
    head(g, 682, 89, "Round 2")
    txt(g, 340, 89, "From the sampled prior", 17, color=MUTED)
    txt(g, 788, 89, "From the updated model", 17, color=MUTED)
    for y in (99, 222, 295, 353):
        line(g, [(25, y), (1134, y)], LINE, 1)
    for y, s in [(162, "Candidate path"), (265, "Oracle target"), (331, "Retained examples")]:
        txt(g, 27, y, s, 20, True)
    for x, k, learned in [(233, "near", False), (681, "next", True)]:
        draw_field(g, x, 110, 153, k, learned=learned)
        target_detail(g, x + 21, 230, 110, 57, k, learned)
    note(g, 407, 151, "Sample a prior", "Same image and goal.")
    note(g, 856, 151, "Apply GEAR", "Bound and check the step.")
    txt(g, 404, 266, "Label the sampled path.", 18)
    txt(g, 854, 266, "Query at the new path.", 18)
    box(g, 234, 306, 168, 36, "Example 1", fill=PURPLE)
    box(g, 681, 306, 147, 36, "Example 1", fill=PURPLE)
    txt(g, 841, 332, "+", 22, True, "middle")
    box(g, 854, 306, 147, 36, "Example 2", fill=PURPLE)
    box(g, 234, 362, 323, 36, "Fit GEAR on round 1", fill=PEACH)
    box(g, 681, 362, 391, 36, "Fit GEAR on both rounds", fill=PEACH)
    arrow(g, [(558, 380), (621, 380), (621, 165), (672, 165)])
    arrow(g, [(1075, 380), (1128, 380)])
    txt(g, 1100, 372, "Repeat", 15, anchor="middle", color=MUTED)
    footer(r)
    return r


def two_lanes():
    r = base(4, "What geometry teaches and what runs on the robot")
    g = group(r, "training")
    rect(g, 25, 73, 1110, 173, "#fffaf0", "#e1c990", 5)
    head(g, 41, 101, "During training")
    for y, label, model, fill, mode in [
        (117, "ESDF + goal + path", "Energy oracle", AMBER, "target"),
        (178, "Image + goal + path", "GEAR", PEACH, "prediction"),
    ]:
        box(g, 42, y, 197, 46, label, fill="white")
        arrow(g, [(241, y + 23), (267, y + 23)])
        box(g, 273, y, 155, 46, model, fill=fill)
        arrow(g, [(430, y + 23), (450, y + 23)])
        glyph(g, 455, y + 1, 97, mode)
        txt(g, 569, y + 29, "Oracle label" if mode == "target" else "Prediction", 18)
    line(g, [(659, 140), (686, 140), (686, 201), (659, 201)])
    arrow(g, [(686, 171), (713, 171)])
    box(g, 719, 135, 194, 69, "Fit corrections", "Use all retained rounds", PURPLE)
    arrow(g, [(915, 170), (939, 170)])
    box(g, 945, 135, 169, 69, "Update GEAR", "Label new paths", PEACH)
    g = group(r, "deployment")
    rect(g, 25, 258, 1110, 182, "#f3f7f7", "#b7c6c8", 5)
    head(g, 41, 287, "On the robot")
    for x, w, label, fill in [
        (42, 197, "Image + goal + path", "white"),
        (273, 155, "GEAR", PEACH),
        (465, 178, "Predict correction", "white"),
        (679, 177, "Bounded update", "white"),
    ]:
        box(g, x, 308, w, 51, label, fill=fill)
    for x1, x2 in [(241, 267), (430, 457), (645, 671), (858, 905)]:
        arrow(g, [(x1, 333), (x2, 333)])
    draw_field(g, 913, 276, 195, "refined", learned=True, prior=True)
    txt(g, 1010, 427, "Reference field for display", 15, anchor="middle", color=MUTED, italic=True)
    arrow(g, [(770, 359), (770, 402), (141, 402), (141, 364)])
    txt(g, 462, 395, "Use the updated path as the next input", 18, anchor="middle")
    footer(r, False)
    return r


def record():
    r = base(5, "What goes into the training set?")
    g = group(r, "make-an-example")
    head(g, 27, 91, "Make a label")
    scene(g, 29, 110, 178)
    txt(g, 29, 247, "Sample a candidate path.", 18)
    box(g, 29, 265, 206, 62, "Energy oracle", "ESDF, goal and path", AMBER)
    arrow(g, [(236, 295), (267, 295)])
    g = group(r, "replay-record")
    head(g, 277, 91, "One retained example")
    rect(g, 292, 134, 510, 195, "#e0d5e7", "#ac9cb7", 6)
    rect(g, 284, 126, 510, 195, "#eee7f3", "#ac9cb7", 6)
    rect(g, 275, 118, 510, 195, "white", "#927e9f", 6, 1.6)
    for x in (402, 529, 656):
        line(g, [(x, 128), (x, 297)], "#e0dae3", 1)
    for x, label in [(339, "Image"), (465, "Goal"), (592, "Candidate"), (720, "Target")]:
        txt(g, x, 154, label, 21, True, "middle")
    scene(g, 286, 176, 105)
    star(g, 465, 207, 17)
    glyph(g, 538, 188, 107)
    glyph(g, 666, 188, 107, "target")
    for x, s in [(339, "Observation"), (465, "Doorway"), (592, "Current path"), (720, "Correction")]:
        txt(g, x, 270, s, 16, anchor="middle", color=MUTED)
    txt(g, 530, 353, "Earlier examples stay in replay.", 18, anchor="middle", color=MUTED)
    arrow(g, [(804, 211), (857, 211)])
    g = group(r, "learn-and-continue")
    head(g, 865, 91, "Use the examples")
    box(g, 864, 178, 261, 64, "Train GEAR", "Sample retained rounds", PEACH)
    arrow(g, [(996, 243), (996, 265)])
    box(g, 864, 271, 261, 58, "Full-dataset training", "Extend to more scenes", "white")
    line(g, [(900, 242), (900, 255), (837, 255), (837, 393)], INK)
    arrow(g, [(837, 393), (132, 393), (132, 333)])
    txt(g, 495, 385, "Generate the next candidate with the trained model", 17, anchor="middle")
    footer(r)
    return r


FIGURES = [
    ("01-two-paths", two_paths),
    ("02-energy-terms", anatomy),
    ("03-two-rounds", rounds),
    ("04-training-deployment", two_lanes),
    ("05-replay-example", record),
]


def render():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pages = []
        for name, make in FIGURES:
            svg = OUT / (name + ".svg")
            tree = ET.ElementTree(make())
            ET.indent(tree, space="  ")
            tree.write(svg, encoding="utf-8", xml_declaration=True)
            png = OUT / (name + ".png")
            subprocess.run(["rsvg-convert", "-w", "1392", "-o", str(png), str(svg)], check=True)
            pdf = Path(tmp) / (name + ".pdf")
            subprocess.run(["rsvg-convert", "-d", "72", "-p", "72", "-f", "pdf", "-o", str(pdf), str(svg)], check=True)
            pages.append(str(pdf))
        subprocess.run(["pdfunite", *pages, str(OUT / "five-pipelines.pdf")], check=True)
    # Give each alternative the same area in the comparison sheet.
    gap, w = 14, 840
    h = round(w * H / W)
    sheet = Image.new("RGB", (2 * w + 3 * gap, 3 * h + 4 * gap), "#e6e9e9")
    for i, (name, _) in enumerate(FIGURES):
        row, col = divmod(i, 2)
        left, top = gap + col * (w + gap), gap + row * (h + gap)
        if i == len(FIGURES) - 1:
            left = (sheet.width - w) // 2
        with Image.open(OUT / (name + ".png")) as im:
            sheet.paste(im.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), (left, top))
    sheet.save(OUT / "five-pipelines.png", optimize=True)


if __name__ == "__main__":
    render()
