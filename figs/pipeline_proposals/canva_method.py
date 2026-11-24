"""Matched scene maps, print styling and native Canva export for Figures 2 and 3."""

from __future__ import annotations

import json
from hashlib import sha256
from math import ceil, hypot
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import contourpy
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates

from draw_architecture import Diagram, ESDF_CMAP, ESDF_NORM, INK, ORANGE, TARGET, WAYPOINT_FILL

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "method_examples"
FONT_FAMILY = "Arial"
GRAY = "#D5D5D5"
SAND = "#F1E1C8"
INK_LINE = "#24282A"
MUTED = "#41464A"
BACKWARD = "#A34406"
PANEL_EDGE = "#484846"
INDICES = (5, 8, 11, 15)
SCALE = .8


def load_example(name):
    proof = json.loads((EXAMPLES / "provenance.json").read_text())
    saved = EXAMPLES / (name + ".npz")
    if sha256(saved.read_bytes()).hexdigest() != proof["files_sha256"][saved.name]:
        raise ValueError(f"Unexpected scene data for {name}")
    with np.load(saved) as data:
        return {key: data[key] for key in data.files}, proof


def finish_fonts(d):
    for node in d.root.iter("{http://www.w3.org/2000/svg}text"):
        node.set("font-family", f"{FONT_FAMILY}, Liberation Sans, sans-serif")
    return d


class DistanceMap:
    """Identical robot-frame projection for native ESDF cells and vector overlays."""

    def __init__(self, data):
        self.forward_max, self.left_min, self.left_max = data["limits"]
        f0, l0, res, _ = data["grid"]
        # Uniform samples at pixel centers. Stored ESDF values also index cell centers.
        nx = round((self.left_max - self.left_min) / res)
        ny = round(self.forward_max / res)
        u, v = np.meshgrid((np.arange(nx) + .5) / nx, (np.arange(ny) + .5) / ny)
        forward = (1 - v) * self.forward_max
        left = self.left_max - u * (self.left_max - self.left_min)
        rows, cols = (left - l0) / res - .5, (forward - f0) / res - .5
        if min(rows.min(), cols.min()) < -.002 or max(rows.max() - data["esdf"].shape[0] + 1,
                                                       cols.max() - data["esdf"].shape[1] + 1) > .002:
            raise ValueError("Distance-map crop exceeds the archived native grid.")
        z = map_coordinates(data["esdf"], [rows, cols], order=1, mode="nearest", prefilter=False)
        self.raster = Image.fromarray(np.uint8(255 * ESDF_CMAP(ESDF_NORM(z))[:, :, :3])).convert("RGBA")
        # Trace the signed field itself. The darker 0 m line is the obstacle boundary.
        contours = contourpy.contour_generator(z=z, line_type="Separate")
        ink = Image.new("RGBA", self.raster.size)
        pen = ImageDraw.Draw(ink)
        for level in (-2, -1, 0, 1, 2):
            color = (42, 42, 48, 155 if level == 0 else 75)
            for segment in contours.lines(level):
                pen.line([tuple(xy) for xy in segment], fill=color, width=4 if level == 0 else 2)
        self.raster = Image.alpha_composite(self.raster, ink)

    def project(self, point, origin, across, toward):
        f, left = point
        u = (self.left_max - left) / (self.left_max - self.left_min)
        v = 1 - f / self.forward_max
        return np.array(origin) + u * np.array(across) + v * np.array(toward)

    def plane(self, d, origin, across, toward):
        # Inverse-map a raster into the same affine plane as the editable paths.
        start = np.array(origin)
        basis = np.column_stack((across, toward))
        corners = np.array([start, start + basis[:, 0], start + basis.sum(axis=1), start + basis[:, 1]])
        lower, upper = corners.min(axis=0), corners.max(axis=0)
        size = upper - lower
        out = np.rint(size * 3).astype(int)
        source_pixels = np.diag(self.raster.size)
        back = source_pixels @ np.linalg.inv(basis)
        linear = back @ np.diag(size / out)
        shift = back @ (lower - start)
        affine = np.column_stack((linear, shift)).ravel()
        raster = self.raster.transform(tuple(out), Image.Transform.AFFINE, affine,
                                       resample=Image.Resampling.BICUBIC)
        d.image(raster, *lower, *size, fit="none").set("data-esdf-isolines-m", "-2,-1,0,1,2")
        d.line([*corners, corners[0]], "#72777A", .85)
        return lambda point: self.project(point, origin, across, toward)


def path_line(d, points, stroke=ORANGE, width=2.8):
    d.line(points, "white", width + 2.2)
    return d.line(points, stroke, width)


def correction_arrows(d, path, targets, project, marker_radius=2.3):
    for i in INDICES:
        start, end = project(path[i]), project(path[i] + SCALE * targets[i])
        length = float(np.linalg.norm(np.subtract(end, start)))
        if length > 0:
            head = min(6.2, .55 * length)
            line_width = min(2.15, .40 * length)
            d.arrow([start, end], "white", line_width + 1.3, head=head * 1.13)
            d.arrow([start, end], TARGET, line_width, head=head).set("data-target-waypoint", str(i))
    for i in INDICES:
        d.circle(*project(path[i]), marker_radius, WAYPOINT_FILL, INK, .75)
    d.circle(*project(path[0]), 3, "white", INK, 1)


def colorbar(d, x, y, width, height, label_size=15.5):
    # Native color strips keep both ends of the scale in Canva at every aspect ratio.
    count = 64
    for i, rgba in enumerate(ESDF_CMAP(np.linspace(0, 1, count))):
        color = "#" + "".join(f"{round(v * 255):02x}" for v in rgba[:3])
        # Overlap adjacent filled shapes to avoid light antialiasing seams in
        # Canva's small preview. The following strip sets each true boundary.
        strip_width = min(width * (count - i) / count, width / count + 2)
        strip = d.rect(x + width * i / count, y, strip_width, height, color, "none", 0, 0)
        if i == 0:
            strip.set("data-range-m", "-3,3")
    for fraction, label in ((0, "−3"), (.5, "0"), (1, "+3")):
        pos = x + fraction * width
        d.line([(pos, y + height), (pos, y + height + 3)], INK_LINE, .85)
        d.text(pos, y + height + 17, label, label_size, anchor="middle")


def export_pptx(svg, title_text, pixel_width):
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
        _, _, width, height = numbers(root.get("viewBox"))
        scale = pixel_width / width * 9525 / EMU
        root.set("viewBox", f"0 0 {width * scale:.12g} {height * scale:.12g}")
        root.set("transform", f"scale({scale:.12g})")
        slide = CanvaSlide(root, Path(temporary) / "Fonts", title_text)
        # Canva truncates fractional-point page sizes during import. A 955 pt page
        # gives the required 1,273 px height without moving or scaling the artwork.
        slide.deck.slide_height = Pt(ceil(slide.deck.slide_height.pt))
        slide.save(svg.with_suffix(".pptx"))
