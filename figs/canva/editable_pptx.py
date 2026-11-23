"""Translate the SVG features used in the six GEAR-Nav figures into native slide objects."""

import base64
from io import BytesIO
import math
from pathlib import Path
import re

import cv2
from fontTools.misc.transform import Identity
from fontTools.svgLib.path import parse_path
from fontTools.svgLib.path.shapes import PathBuilder
from lxml import etree as ET
import numpy as np
import pathops
from PIL import Image
from PIL import ImageColor
from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

EMU = 6350  # One design unit occupies half a point on the slide.
XLINK = "{http://www.w3.org/1999/xlink}href"
VECTOR_TAGS = {"rect", "circle", "ellipse", "path", "polyline", "polygon", "line"}
NONPAINTING = {"defs", "metadata", "title", "desc", "style"}


def tag(node):
    return ET.QName(node).localname


def numbers(value):
    return [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value)]


def transform(parent, instructions):
    for op, args in re.findall(r"([A-Za-z]+)\(([^)]*)\)", instructions or ""):
        v = numbers(args)
        if op == "translate":
            parent = parent.translate(v[0], v[1] if len(v) == 2 else 0)
        elif op == "scale":
            parent = parent.scale(*v)
        elif op == "rotate":
            x, y = v[1:] or (0, 0)
            parent = parent.translate(x, y).rotate(math.radians(v[0])).translate(-x, -y)
        else:
            raise ValueError(f"Unexpected transform {op}")
    return parent


def geometry(node, matrix):
    if tag(node) == "path":
        data = node.get("d")
    else:
        builder = PathBuilder()
        builder.add_path_from_element(node)
        data = builder.paths[0]
    path = pathops.Path()
    parse_path(data, path.getPen())
    return path.transform(*matrix)


def rectangle(left, top, right, bottom):
    result = pathops.Path()
    result.moveTo(left, top)
    result.lineTo(right, top)
    result.lineTo(right, bottom)
    result.lineTo(left, bottom)
    result.close()
    return result


def image_data(node):
    uri = node.get(XLINK) or node.get("href")
    encoding, data = uri.split(",", 1)
    if not encoding.startswith("data:image/") or not encoding.endswith(";base64"):
        raise ValueError("Expected an embedded image")
    return base64.b64decode(data)


def element(parent, tag_name, **values):
    return ET.SubElement(parent, qn("a:" + tag_name), {k: str(v) for k, v in values.items()})


def color(parent, value, alpha=1):
    rgb = ImageColor.getrgb(value)
    out = element(parent, "srgbClr", val=bytes(rgb).hex().upper())
    if alpha < 1:
        element(out, "alpha", val=round(alpha * 100000))


def figure_name(node):
    for key in ("id", "data-kind", "data-connection", "data-role", "data-module"):
        if node.get(key):
            return node.get(key)
    group = next((p.get("id") for p in node.iterancestors() if p.get("id")), "")
    return f"{group} {tag(node)}".strip()


class Slide:
    def __init__(self, root, fonts, title):
        self.root = root
        self.ids = {e.get("id"): e for e in root.iter() if e.get("id")}
        self.fonts = {
            bold: ImageFont.truetype(str(fonts / f"STIXTwoText-{style}.ttf"), 512)
            for bold, style in ((True, "Bold"), (False, "Regular"))
        }
        self.deck = Presentation()
        _, _, self.width, self.height = numbers(root.get("viewBox"))
        self.deck.slide_width = round(self.width * EMU)
        self.deck.slide_height = round(self.height * EMU)
        self.deck.core_properties.title = title
        self.deck.core_properties.author = "GEAR-Nav"
        self.slide = self.deck.slides.add_slide(self.deck.slide_layouts[6])
        self.slide.name = title

    def box(self, bounds, name, kind=MSO_SHAPE.RECTANGLE):
        x, y, x2, y2 = bounds
        shape = self.slide.shapes.add_shape(
            kind, round(x * EMU), round(y * EMU), max(1, round((x2 - x) * EMU)), max(1, round((y2 - y) * EMU))
        )
        shape.name = name
        for child in list(shape._element):
            if tag(child) in {"style", "txBody"}:
                shape._element.remove(child)
        return shape._element.spPr

    def paint(self, props, fill, stroke, width, style):
        opacity = float(style.get("opacity", 1))
        if fill == "none":
            element(props, "noFill")
        else:
            color(element(props, "solidFill"), fill, opacity * float(style.get("fill-opacity", 1)))
        cap = {"round": "rnd", "square": "sq", "butt": "flat"}[style.get("stroke-linecap", "butt")]
        line = element(props, "ln", w=max(0, round(width * EMU)), cap=cap)
        if stroke == "none" or not width:
            element(line, "noFill")
            return
        color(element(line, "solidFill"), stroke, opacity * float(style.get("stroke-opacity", 1)))
        if "stroke-dasharray" in style:
            lengths = numbers(style["stroke-dasharray"])
            base = float(style.get("stroke-width", 1))
            dash = element(line, "custDash")
            for a, b in zip(lengths[::2], lengths[1::2]):
                element(dash, "ds", d=round(100000 * a / base), sp=round(100000 * b / base))
        element(line, {"round": "round", "bevel": "bevel", "miter": "miter"}[style.get("stroke-linejoin", "miter")])

    def colorbar(self, bounds, gradient, stroke, width, style):
        # A series of two-stop fills survives readers that discard intermediate stops.
        x, y, right, bottom = bounds
        start = len(self.slide.shapes)
        for left_stop, right_stop in zip(gradient, list(gradient)[1:]):
            left, stop = [float(node.get("offset").removesuffix("%")) / 100 for node in (left_stop, right_stop)]
            p = self.box(
                (x + left * (right - x), y, min(right, x + stop * (right - x) + 0.15), bottom), "ESDF color interval"
            )
            grad = element(p, "gradFill", rotWithShape="1")
            stops = element(grad, "gsLst")
            color(element(stops, "gs", pos=0), left_stop.get("stop-color"))
            color(element(stops, "gs", pos=100000), right_stop.get("stop-color"))
            element(grad, "lin", ang=0, scaled=0)
            element(element(p, "ln", w=0), "noFill")
        self.paint(self.box(bounds, "ESDF color scale border"), "none", stroke, width, style)
        self.slide.shapes.add_group_shape(list(self.slide.shapes)[start:]).name = "ESDF color scale"

    def freeform(self, path, name, fill, stroke, width, style):
        if not len(path):
            return
        # Bézier control points may lie outside the visible bounding box.
        x, y, right, bottom = path.bounds
        props = self.box((x, y, right, bottom), name)
        props.remove(props.prstGeom)
        geom = element(props, "custGeom")
        for child in ("avLst", "gdLst", "ahLst", "cxnLst"):
            element(geom, child)
        element(geom, "rect", l="l", t="t", r="r", b="b")
        p = element(
            element(geom, "pathLst"), "path", w=max(1, round((right - x) * 1000)), h=max(1, round((bottom - y) * 1000))
        )
        for command, points in path.segments:
            if command == "endPath":
                continue
            out = element(
                p,
                {
                    "moveTo": "moveTo",
                    "lineTo": "lnTo",
                    "curveTo": "cubicBezTo",
                    "qCurveTo": "quadBezTo",
                    "closePath": "close",
                }[command],
            )
            for xx, yy in points:
                element(out, "pt", x=round((xx - x) * 1000), y=round((yy - y) * 1000))
        self.paint(props, fill, stroke, width, style)

    def vector(self, node, matrix, opacity, clip):
        style = dict(node.attrib)
        style["opacity"] = opacity
        name = figure_name(node)
        fill, stroke = node.get("fill", "black"), node.get("stroke", "none")
        width = float(node.get("stroke-width", 1)) * math.hypot(matrix.xx, matrix.xy)
        path = geometry(node, matrix)
        if not len(path):
            return
        bounds = path.bounds
        if fill.startswith("url("):
            self.colorbar(bounds, self.ids[fill[5:-1]], stroke, width, style)
            return
        if clip is not None:
            margin = width / 2 if stroke != "none" else 0
            check = rectangle(bounds[0] - margin, bounds[1] - margin, bounds[2] + margin, bounds[3] + margin)
            if len(pathops.op(check, clip, pathops.PathOp.DIFFERENCE)):
                if fill != "none":
                    part = pathops.op(path, clip, pathops.PathOp.INTERSECTION)
                    self.freeform(part, name, fill, "none", 0, style)
                if stroke != "none" and width:
                    outlined = pathops.Path(path)
                    cap = (
                        pathops.LineCap.ROUND_CAP if node.get("stroke-linecap") == "round" else pathops.LineCap.BUTT_CAP
                    )
                    join = (
                        pathops.LineJoin.ROUND_JOIN
                        if node.get("stroke-linejoin") == "round"
                        else pathops.LineJoin.MITER_JOIN
                    )
                    dash = [v * math.hypot(matrix.xx, matrix.xy) for v in numbers(node.get("stroke-dasharray", ""))]
                    outlined.stroke(width, cap, join, 4, dash or None)
                    outlined.convertConicsToQuads(0.05)
                    part = pathops.op(outlined, clip, pathops.PathOp.INTERSECTION)
                    part.convertConicsToQuads(0.05)
                    self.freeform(part, name + " outline", stroke, "none", 0, style)
                return
        if tag(node) in {"circle", "ellipse", "rect"}:
            radius = float(node.get("rx", 0)) * matrix.xx
            kind = (
                MSO_SHAPE.OVAL
                if tag(node) != "rect"
                else MSO_SHAPE.ROUNDED_RECTANGLE
                if radius
                else MSO_SHAPE.RECTANGLE
            )
            props = self.box(bounds, name, kind)
            if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
                adj = min(0.5, radius / min(bounds[2] - bounds[0], bounds[3] - bounds[1]))
                element(props.prstGeom.avLst, "gd", name="adj", fmla=f"val {round(adj * 100000)}")
            self.paint(props, fill, stroke, width, style)
        else:
            self.freeform(path, name, fill, stroke, width, style)

    def text(self, node, matrix):
        label = "".join(node.itertext())
        scale = math.hypot(matrix.xx, matrix.xy)
        size = float(node.get("font-size"))
        bold = node.get("font-weight", "normal") in {"bold", "700"}
        tracking = float(node.get("letter-spacing", 0))
        advance = self.fonts[bold].getlength(label) * size / 512 + tracking * max(0, len(label) - 1)
        # Extra space accommodates font matching in importers. Alignment keeps the SVG anchor fixed.
        width, height = advance + size * 0.5, size * 1.35
        anchor = node.get("text-anchor", "start")
        left = float(node.get("x")) - {"start": 0, "middle": 0.5, "end": 1}[anchor] * width
        # With zero insets, STIX Two Text's Office baseline is one em below the box top.
        top = float(node.get("y")) - size
        cx, cy = matrix.transformPoint((left + width / 2, top + height / 2))
        width, height = width * scale, height * scale
        shape = self.slide.shapes.add_textbox(
            round((cx - width / 2) * EMU), round((cy - height / 2) * EMU), round(width * EMU), round(height * EMU)
        )
        shape.name = label
        shape.rotation = math.degrees(math.atan2(matrix.xy, matrix.xx)) % 360
        frame = shape.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.word_wrap = False
        frame.auto_size = MSO_AUTO_SIZE.NONE
        frame.vertical_anchor = MSO_ANCHOR.TOP
        paragraph = frame.paragraphs[0]
        paragraph.alignment = {"start": PP_ALIGN.LEFT, "middle": PP_ALIGN.CENTER, "end": PP_ALIGN.RIGHT}[anchor]
        paragraph.space_after = paragraph.space_before = Pt(0)
        run = paragraph.add_run()
        run.text = label
        run.font.name = "STIX Two Text"
        run.font.size = Pt(size * scale * EMU / 12700)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(*ImageColor.getrgb(node.get("fill", "black")))
        props = run._r.get_or_add_rPr()
        props.set("kern", "0")
        if tracking:
            props.set("spc", str(round(tracking * scale * EMU / 127)))

    def picture(self, node, matrix):
        data = image_data(node)
        iw, ih = Image.open(BytesIO(data)).size
        x, y = matrix.transformPoint((float(node.get("x", 0)), float(node.get("y", 0))))
        w, h = float(node.get("width")) * matrix.xx, float(node.get("height")) * matrix.yy
        aspect = node.get("preserveAspectRatio", "xMidYMid meet")
        crop_x = crop_y = 0
        if aspect != "none":
            if "slice" in aspect:
                scale = max(w / iw, h / ih)
                crop_x, crop_y = (1 - w / (iw * scale)) / 2, (1 - h / (ih * scale)) / 2
            else:
                scale = min(w / iw, h / ih)
                x, y = x + (w - iw * scale) / 2, y + (h - ih * scale) / 2
                w, h = iw * scale, ih * scale
        pic = self.slide.shapes.add_picture(
            BytesIO(data), round(x * EMU), round(y * EMU), round(w * EMU), round(h * EMU)
        )
        pic.name = figure_name(node)
        pic.crop_left = pic.crop_right = max(0, crop_x)
        pic.crop_top = pic.crop_bottom = max(0, crop_y)

    def equation(self, svg, matrix, opacity):
        # Combine an equation's glyph outlines into one movable, recolorable object.
        x, y, w, h = (float(svg.get(k)) for k in ("x", "y", "width", "height"))
        vx, vy, vw, vh = numbers(svg.get("viewBox"))
        scale = min(w / vw, h / vh)
        dx = 0 if "xMin" in svg.get("preserveAspectRatio", "") else (w - scale * vw) / 2
        matrix = matrix.translate(x + dx, y + (h - scale * vh) / 2).scale(scale).translate(-vx, -vy)
        paths = {}

        def visit(node, matrix, fill):
            t = tag(node)
            if t in NONPAINTING:
                return
            styles = dict(pair.strip().split(":", 1) for pair in node.get("style", "").split(";") if ":" in pair)
            fill = styles.get("fill", node.get("fill", fill)).strip()
            matrix = transform(matrix, node.get("transform"))
            if t == "use":
                visit(self.ids[node.get(XLINK)[1:]], matrix, fill)
            elif t in VECTOR_TAGS:
                if fill != "none":
                    paths.setdefault(fill, pathops.Path()).addPath(geometry(node, matrix))
            elif t == "g":
                for child in node:
                    visit(child, matrix, fill)
            else:
                raise ValueError(f"Unexpected equation element {t}")

        for child in svg:
            visit(child, matrix, "black")
        for fill, path in paths.items():
            self.freeform(path, "Equation · " + svg.get("id").split("_")[0], fill, "none", 0, {"opacity": opacity})

    def depth_mask(self, mask, matrix):
        # These SVG masks are binary white-with-alpha depth images. Intersecting the
        # original vectors with their silhouettes preserves foreground occlusion in Canva.
        image = Image.open(BytesIO(image_data(mask[0]))).convert("RGBA")
        pixels = np.asarray(image)
        if not (np.all(pixels[:, :, :3] == 255) and np.all(np.isin(pixels[:, :, 3], (0, 255)))):
            raise ValueError("Expected the binary depth mask recorded for this teaser")
        contours, _ = cv2.findContours(pixels[:, :, 3].copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        outline = pathops.Path()
        outline.fillType = pathops.FillType.EVEN_ODD
        for contour in contours:
            points = contour[:, 0, :]
            if len(points) >= 3:
                outline.moveTo(*points[0])
                for point in points[1:]:
                    outline.lineTo(*point)
                outline.close()
        return outline.transform(*matrix)

    def draw(self, node, matrix=Identity, opacity=1, clip=None):
        t = tag(node)
        if t in NONPAINTING:
            return
        matrix = transform(matrix, node.get("transform"))
        opacity *= float(node.get("opacity", 1))
        for attr in ("clip-path", "mask"):
            if node.get(attr):
                source = self.ids[node.get(attr)[5:-1]]
                new = self.depth_mask(source, matrix) if attr == "mask" else geometry(source[0], matrix)
                clip = new if clip is None else pathops.op(clip, new, pathops.PathOp.INTERSECTION)
        if t == "svg" and node is not self.root:
            self.equation(node, matrix, opacity)
        elif t in {"g", "svg"}:
            for child in node:
                self.draw(child, matrix, opacity, clip)
        elif t == "text":
            self.text(node, matrix)
        elif t == "image":
            self.picture(node, matrix)
        elif t in VECTOR_TAGS:
            self.vector(node, matrix, opacity, clip)
        else:
            raise ValueError(f"Unexpected visible SVG element {t}")

    def save(self, path: Path):
        self.draw(self.root)
        self.deck.save(path)
