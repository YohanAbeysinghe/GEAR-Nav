"""Three qualitative layouts using one recorded Amsterdam RGB–ESDF pair."""

import argparse
import hashlib
import json
import os
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
FIGS = SOURCE.parents[1]
sys.path.insert(0, str(FIGS))
import figure_style as style
from svg_diagram import Diagram, SVG

WIDTH, HEIGHT = 680, 542  # The original Canva design, in CSS pixels.
INK = "#283139"
MUTED = "#424B50"
WHITE = "#FFFFFF"
GEAR = "#D64A10"
ORACLE = "#006A70"
YELLOW = style.WAYPOINT_FILL
RANGE_M = 1.1

SCENE = json.loads((SOURCE / "scene.json").read_text())
ART = json.loads((SOURCE / "artwork.json").read_text())
CANDIDATE = np.asarray(ART["candidate"])
gear_sketch = json.loads((HERE / "gear_sketch.json").read_text())
DELTAS = {GEAR: np.asarray(gear_sketch["displacements"]), ORACLE: np.asarray(ART["oracle_displacement"])}
APPROACH, BESIDE = ART["highlight_waypoints"]
forward, left, _ = SCENE["bollard_surface_forward_left_up_m"]
BOLLARD = np.array([-left, forward])


def label(d, x, y, words, size=21, *, bold=False, anchor="start", color=INK, italic=False):
    text = d.text(x, y, words, size, bold=bold, anchor=anchor, color=color)
    if italic:
        text.set("font-style", "italic")
    return text


def ring(d, xy):
    # The same open ring locates the measured bollard surface in both views.
    d.circle(*xy, 5.2, "none", INK, 3.4)
    d.circle(*xy, 5.2, "none", WHITE, 1.8)


def photo(d, rect, center, *, fraction=1.0, callout=False, location=False):
    x, y, w, h = rect
    with Image.open(SOURCE / "camera.jpg") as original:
        width, height = original.size
        crop_w = round(fraction * min(width, height * w / h))
        crop_h = round(fraction * min(height, width * h / w))
        x0 = round(np.clip(center[0] * width - crop_w / 2, 0, width - crop_w))
        y0 = round(np.clip(center[1] * height - crop_h / 2, 0, height - crop_h))
        crop = original.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        crop.thumbnail((2 * w, 2 * h), Image.Resampling.LANCZOS)
        with tempfile.TemporaryDirectory() as tmp:
            asset = Path(tmp) / "camera.jpg"
            crop.save(asset, quality=95, subsampling=0)
            image = d.image(asset, x, y, w, h, fit="none")
    image.set("id", "recorded-amsterdam-camera")
    image.set("data-source-crop-px", f"{x0} {y0} {crop_w} {crop_h}")
    u, v = SCENE["bollard_image_uv"]
    point = np.array([x + (u * width - x0) * w / crop_w, y + (v * height - y0) * h / crop_h])
    assert x + 6 < point[0] < x + w - 6 and y + 6 < point[1] < y + h - 6
    if callout:
        tx, ty = point - [57, 22]
        line_end = np.array([tx + 6, ty - 5])
        towards_label = (line_end - point) / np.linalg.norm(line_end - point)
        d.line([point + towards_label * 6, line_end], INK, 3.4)
        d.line([point + towards_label * 6, line_end], WHITE, 1.6)
        d.rect(tx - 65, ty - 20, 74, 25, INK, "none", 1)
        label(d, tx + 3, ty, "Bollard", 20, anchor="end", color=WHITE)
    ring(d, point)
    if location:
        d.rect(x + 8, y + 8, 116, 28, INK, "none", 1)
        label(d, x + 16, y + 29, "Amsterdam", 20, color=WHITE)


def waypoint(d, xy, radius=6.6):
    d.circle(*xy, radius + 1.0, WHITE, "none", 0)
    return d.circle(*xy, radius, YELLOW, INK, 1.8)


def arrow(d, start, end, color, *, weight=4.0, head=14.5):
    start, end = np.asarray(start), np.asarray(end)
    unit = (end - start) / np.linalg.norm(end - start)
    normal = np.array([-unit[1], unit[0]])
    back = end - head * unit
    wings = [back + normal * head * 0.44, back - normal * head * 0.44]
    # Filled and open heads also distinguish the two directions in grayscale.
    shaft_end = back if color == GEAR else end
    d.line([start, shaft_end], WHITE, weight + 2.6)
    d.line([start, shaft_end], color, weight)
    if color == GEAR:
        d.el("polygon", points=" ".join(f"{a:.3f},{b:.3f}" for a, b in [wings[0], end, wings[1], back - unit]),
             fill=color, stroke=WHITE, stroke_width=1.25, stroke_linejoin="round")
    else:
        d.line([wings[0], end, wings[1]], WHITE, weight + 2.6)
        d.line([wings[0], end, wings[1]], color, weight)


class MapPanel:
    """An equal-scale metric crop with camera forward pointing up."""

    def __init__(self, d, field, rect, center, across):
        self.d = d
        self.x, self.y, w, h = rect
        self.scale = w / across
        self.left = center[0] - across / 2
        self.top = center[1] + h / (2 * self.scale)
        self.bottom = self.top - h / self.scale
        x0, x1, f0, f1 = SCENE["esdf_extent_right_forward_m"]
        assert x0 <= self.left < self.left + across <= x1 and f0 <= self.bottom < self.top <= f1
        # Pixel centers refer to the original 2 cm cells. There is no contour,
        # plot frame, grid overlay, or smoothing of the underlying field.
        resolution = SCENE["esdf_resolution_m"]
        col = (self.left - x0 + (np.arange(w * 2) + .5) / (2 * self.scale)) / resolution - .5
        row = (self.top - f0 - (np.arange(h * 2) + .5) / (2 * self.scale)) / resolution - .5
        rows, cols = np.meshgrid(row, col, indexing="ij")
        clearance = map_coordinates(field, [rows, cols], order=1, mode="nearest") - SCENE["footprint_radius_m"]
        colors = style.TEASER_ESDF_CMAP(np.clip((clearance / RANGE_M + 1) / 2, 0, 1), bytes=True)
        bg = d.image(Image.fromarray(colors[:, :, :3]), *rect, fit="none")
        bg.set("data-clearance-extent-m", f"{self.left} {self.left + across} {self.bottom} {self.top}")
        self.right = self.left + across

    def xy(self, point):
        return np.array([self.x + (point[0] - self.left) * self.scale,
                         self.y + (self.top - point[1]) * self.scale])

    def draw_path(self, points, color=INK, width=2.8, dash=None):
        # Both hand-drawn proposals are monotone in forward distance.
        right, forward = points.T
        assert np.all(np.diff(forward) > 0)
        low, high = max(self.bottom, forward[0]), min(self.top, forward[-1])
        levels = np.r_[low, forward[(forward > low) & (forward < high)], high]
        clipped = np.column_stack([np.interp(levels, forward, right), levels])
        assert np.all((self.left < clipped[:, 0]) & (clipped[:, 0] < self.right))
        mapped = [self.xy(point) for point in clipped]
        self.d.line(mapped, WHITE, width + 2.5, dash)
        self.d.line(mapped, color, width, dash)

    def updates(self, index, colors):
        origin = self.xy(CANDIDATE[index])
        for color in colors:
            tip = self.xy(CANDIDATE[index] + DELTAS[color][index])
            arrow(self.d, origin, tip, color)
        waypoint(self.d, origin)
        return origin


def clearance_key(d, x, y):
    label(d, x, y, "ESDF clearance", 19.5)
    label(d, x + 150, y, "Low", 18.5, color=MUTED)
    grad = style.TEASER_ESDF_CMAP(np.linspace(0, 1, 228), bytes=True)[None, :, :3]
    # Canva fits uploaded pictures to their intrinsic aspect ratio.
    d.image(Image.fromarray(np.repeat(grad, 32, axis=0)), x + 193, y - 11, 57, 8, fit="none")
    label(d, x + 258, y, "High", 18.5, color=MUTED)


def candidate_key(d, x, y):
    d.line([(x, y - 6), (x + 38, y - 6)], INK, 2.8)
    waypoint(d, (x + 19, y - 6), 5.4)
    label(d, x + 47, y, "Candidate path", 21)


def method_key(d, x, y, color, name, bold=False):
    arrow(d, (x, y - 6), (x + 36, y - 6), color, weight=3.4, head=11)
    label(d, x + 45, y, name, 22, bold=bold)


def key_row(d, y):
    candidate_key(d, 12, y)
    method_key(d, 241, y, GEAR, "GEAR")
    method_key(d, 448, y, ORACLE, "Geometric oracle")


def footer(d):
    label(d, 12, 531, "Illustrative paths and arrows", 20, italic=True, color=MUTED)
    clearance_key(d, 366, 531)


def shared_waypoint(d, field):
    with d.layer("Camera and matched bollard", "camera"):
        photo(d, (3, 3, 279, 435), (.555, .62), fraction=.83, callout=True)
    with d.layer("Shared waypoint on the local clearance field", "shared-waypoint"):
        view = MapPanel(d, field, (287, 3, 390, 435), (.77, 5.55), 3.0)
        view.draw_path(CANDIDATE)
        ring(d, view.xy(BOLLARD))
        view.updates(BESIDE, [ORACLE, GEAR])
    with d.layer("Labels and keys", "labels"):
        label(d, 142, 464, "Amsterdam", 24, bold=True, anchor="middle")
        label(d, 482, 464, "Shared waypoint", 24, bold=True, anchor="middle")
        key_row(d, 498)
        footer(d)


def matched_paths(d, field):
    with d.layer("Camera and matched bollard", "camera"):
        photo(d, (3, 3, 674, 203), (.5, .72), location=True, callout=True)
    for x, color, name in [(3, GEAR, "GEAR"), (343, ORACLE, "Geometric oracle")]:
        with d.layer(f"{name} proposal on the identical map", "gear" if color == GEAR else "oracle"):
            view = MapPanel(d, field, (x, 211, 334, 239), (.78, 5.51), 3.43)
            view.draw_path(CANDIDATE)
            view.draw_path(CANDIDATE + DELTAS[color], color, 3.7, "9,6" if color == ORACLE else None)
            ring(d, view.xy(BOLLARD))
            view.updates(BESIDE, [color])
    with d.layer("Labels and keys", "labels"):
        method_key(d, 118, 478, GEAR, "GEAR", bold=True)
        method_key(d, 405, 478, ORACLE, "Geometric oracle", bold=True)
        candidate_key(d, 12, 507)
        clearance_key(d, 366, 507)
        label(d, WIDTH / 2, 534, "Illustrative paths and arrows", 20, anchor="middle", italic=True, color=MUTED)


def two_waypoints(d, field):
    with d.layer("Two waypoint corrections on one clearance field", "two-waypoints"):
        view = MapPanel(d, field, (3, 3, 674, 452), (-.10, 5.54), 4.98)
        view.draw_path(CANDIDATE)
        ring(d, view.xy(BOLLARD))
        for index, words, dx, dy in [(BESIDE, "Near bollard", -30, -26), (APPROACH, "On approach", -38, 22)]:
            pos = view.updates(index, [ORACLE, GEAR])
            lx, ly = pos + [dx, dy]
            d.line([(lx + 6, ly - 5), pos + [-8, -4 if dy < 0 else 4]], INK, 1.35)
            label(d, lx, ly, words, 22, bold=True, anchor="end")
    with d.layer("Inset recorded camera frame", "camera"):
        d.rect(3, 3, 274, 181, WHITE, "none", 0)
        photo(d, (3, 3, 270, 177), (.51, .66), fraction=.87)
    with d.layer("Labels and keys", "labels"):
        label(d, 12, 207, "Amsterdam", 21, bold=True)
        key_row(d, 491)
        footer(d)


OPTIONS = [
    ("shared_waypoint", "Shared waypoint", shared_waypoint),
    ("matched_paths", "Matched paths", matched_paths),
    ("two_waypoints", "Two waypoints", two_waypoints),
]


def canva_lettering(root, fonts):
    """Keep each STIX label as one selectable graphic through Canva's PDF import."""
    root = deepcopy(root)
    with ExitStack() as files:
        faces = {}
        for weight in ("Regular", "Bold"):
            filename = fonts / f"STIXTwoText-{weight}.ttf"
            faces[weight] = (files.enter_context(TTFont(filename)), ImageFont.truetype(str(filename), 512))
        for el in root.iter(f"{{{SVG}}}text"):
            value = el.text
            face, metrics = faces["Bold" if el.get("font-weight") == "bold" else "Regular"]
            units = float(el.get("font-size")) / 512
            scale = float(el.get("font-size")) / face["head"].unitsPerEm
            anchor = {"start": 0, "middle": .5, "end": 1}[el.get("text-anchor")]
            x = float(el.get("x")) - anchor * metrics.getlength(value) * units
            y = float(el.get("y"))
            slant = .21 if el.get("font-style") == "italic" else 0
            glyphs, cmap = face.getGlyphSet(), face.getBestCmap()
            pen = SVGPathPen(glyphs, ntos=lambda n: f"{n:.3f}")
            for index, char in enumerate(value):
                if char.isspace():
                    continue
                offset = (metrics.getlength(value[:index + 1]) - metrics.getlength(char)) * units
                glyphs[cmap[ord(char)]].draw(TransformPen(pen, (scale, 0, scale * slant, -scale, x + offset, y)))
            fill = el.get("fill")
            el.clear()
            el.tag = f"{{{SVG}}}path"
            el.attrib.update({"d": pen.getCommands(), "fill": fill, "aria-label": value, "data-kind": value})
    return root


def pdf(pages, output, tmp, env):
    subprocess.run(["rsvg-convert", "--keep-image-data", "-d", "72", "-p", "72", "-f", "pdf",
                    "-o", tmp / "pages.pdf", *pages], check=True, env=env)
    subprocess.run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite", "-dOmitInfoDate=true",
                    "-dAutoRotatePages=/None", "-dFIXEDMEDIA", "-dPDFFitPage", "-dEmbedAllFonts=true",
                    "-dDEVICEWIDTHPOINTS=510", "-dDEVICEHEIGHTPOINTS=406.5",
                    f"-sOutputFile={output}", tmp / "pages.pdf"], check=True, env=env)


def canva_deck(pages, fonts):
    from fontTools.misc.transform import Identity
    from lxml import etree

    sys.path.insert(0, str(FIGS / "realworld_isaacsim/styled"))
    from build_canva import CanvaPage
    from editable_pptx import EMU

    roots = [etree.parse(str(path)).getroot() for path in pages]
    layout = CanvaPage(roots[0], fonts)
    layout.deck.core_properties.title = "5 Qualitative"
    layout.deck.slide_width = WIDTH * 9525
    # Leave a fractional pixel of bleed beneath the artwork in PowerPoint.
    layout.deck.slide_height = round((HEIGHT + .25) * 9525)
    scale = 9525 / EMU  # CSS pixel to the shared PowerPoint exporter's drawing unit.
    try:
        for i, (root, (_, name, _)) in enumerate(zip(roots, OPTIONS, strict=True)):
            if i:
                layout.slide = layout.deck.slides.add_slide(layout.deck.slide_layouts[6])
            layout.slide.name = name
            layout.root = root
            layout.ids = {el.get("id"): el for el in root.iter() if el.get("id")}
            layout.draw(root, Identity.scale(scale))
        layout.deck.save(HERE / "qualitative_canva.pptx")
    finally:
        for face in layout.faces.values():
            face.close()


def render(make_deck):
    for path, expected in [("camera.jpg", SCENE["source_sha256"]["rgb"]),
                           ("esdf_crop.npz", SCENE["esdf_crop_sha256"])]:
        assert hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() == expected
    with np.load(SOURCE / "esdf_crop.npz", allow_pickle=False) as capture:
        field = capture["signed_distance_m"]
    with tempfile.TemporaryDirectory(prefix="gear-qualitative-") as temp:
        tmp = Path(temp)
        # Use the same two licensed faces distributed with the other Canva figures.
        with ZipFile(FIGS / "canva/GEAR-Nav-Canva.zip") as archive:
            for weight in ("Regular", "Bold"):
                archive.extract(f"Fonts/STIXTwoText-{weight}.ttf", tmp)
        config = ET.Element("fontconfig")
        ET.SubElement(config, "include").text = "/etc/fonts/fonts.conf"
        ET.SubElement(config, "dir").text = str(tmp / "Fonts")
        ET.SubElement(config, "cachedir").text = str(tmp / "cache")
        conf = tmp / "fontconfig.xml"
        ET.ElementTree(config).write(conf)
        env = {**os.environ, "FONTCONFIG_FILE": str(conf), "SOURCE_DATE_EPOCH": "0"}

        svgs, imports = [], []
        proof = Image.new("RGB", (3 * 496, 428), "#FFFFFF")
        proof_text = ImageDraw.Draw(proof)
        proof_font = ImageFont.truetype(str(tmp / "Fonts/STIXTwoText-Bold.ttf"), 21)
        for i, (stem, name, draw) in enumerate(OPTIONS):
            d = Diagram(WIDTH, HEIGHT, name, "Recorded Amsterdam RGB and ESDF. Paths and arrows are illustrative.",
                        width_mm=WIDTH / 96 * 25.4)
            draw(d, field)
            ET.indent(d.root, space="  ")
            svg = HERE / f"{stem}.svg"
            ET.ElementTree(d.root).write(svg, encoding="utf-8", xml_declaration=True)
            svgs.append(svg)
            if make_deck:
                outlined = tmp / f"{stem}.svg"
                ET.ElementTree(canva_lettering(d.root, tmp / "Fonts")).write(
                    outlined, encoding="utf-8", xml_declaration=True
                )
                imports.append(outlined)
            subprocess.run(["rsvg-convert", "-w", "956", "-o", tmp / "page.png", svg], check=True, env=env)
            with Image.open(tmp / "page.png") as image:
                panel = image.convert("RGB").resize((478, 381), Image.Resampling.LANCZOS)
                proof.paste(panel, (i * 496 + 9, 38))
            proof_text.text((i * 496 + 11, 4), f"{i + 1}   {name}", font=proof_font, fill=INK)
        proof.save(HERE / "comparison.jpg", quality=94, subsampling=0)
        pdf(svgs, HERE / "qualitative_options.pdf", tmp, env)
        if make_deck:
            canva_deck(imports, tmp / "Fonts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canva", action="store_true", help="Also rebuild the layered Canva PowerPoint.")
    render(parser.parse_args().canva)
