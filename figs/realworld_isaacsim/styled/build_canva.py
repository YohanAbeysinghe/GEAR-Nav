"""Export the approved SVG to the 1400 × 924 px page in 3 GEAR Realworld."""

import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from build import FIGS
from build import KIT
from build import OUTPUT
from build import SVG
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from lxml import etree as ET
import pathops

sys.path.insert(0, str(FIGS / "canva"))
from editable_pptx import EMU  # noqa: E402
from editable_pptx import Slide  # noqa: E402
from editable_pptx import figure_name  # noqa: E402
from editable_pptx import geometry  # noqa: E402
from editable_pptx import numbers  # noqa: E402


class CubicPen(BasePen):
    """BasePen expands the TrueType implied points into single cubic Bézier segments for PowerPoint."""

    def __init__(self, destination):
        super().__init__(None)
        self.destination = destination

    def _moveTo(self, point):
        self.destination.moveTo(point)

    def _lineTo(self, point):
        self.destination.lineTo(point)

    def _curveToOne(self, first, second, end):
        self.destination.curveTo(first, second, end)

    def _closePath(self):
        self.destination.closePath()

    def _endPath(self):
        self.destination.endPath()


class CanvaPage(Slide):
    def __init__(self, root, fonts):
        super().__init__(root, fonts, "GEAR results")
        self.slide.name = "STIX Two Text"
        self.faces = {
            bold: TTFont(fonts / f"STIXTwoText-{face}.ttf") for bold, face in ((True, "Bold"), (False, "Regular"))
        }

    def freeform(self, path, *args):
        cubic = pathops.Path()
        path.draw(CubicPen(cubic.getPen()))
        super().freeform(cubic, *args)

    def text(self, node, matrix):
        # One graphic per label prevents font substitution and line wrapping on import.
        label = "".join(node.itertext())
        bold = node.get("font-weight") in ("700", "bold")
        metrics, face = self.fonts[bold], self.faces[bold]
        size = float(node.get("font-size"))
        x, y = (float(node.get(key)) for key in ("x", "y"))
        anchor = {"start": 0, "middle": 0.5, "end": 1}[node.get("text-anchor", "start")]
        left = x - anchor * metrics.getlength(label) * size / 512
        scale = size / face["head"].unitsPerEm
        glyphs, cmap = face.getGlyphSet(), face.getBestCmap()
        outline = pathops.Path()
        for index, char in enumerate(label):
            if char.isspace():
                continue
            cursor = (metrics.getlength(label[: index + 1]) - metrics.getlength(char)) * size / 512
            drawing = DecomposingRecordingPen(glyphs)
            glyphs[cmap[ord(char)]].draw(drawing)
            placement = matrix.translate(left + cursor, y).scale(scale, -scale)
            drawing.replay(TransformPen(outline.getPen(), placement))
        outline.convertConicsToQuads(0.02)
        self.freeform(outline, label, node.get("fill"), "none", 0, {"opacity": 1})

    def vector(self, node, matrix, opacity, clip):
        stroke = node.get("stroke", "none")
        width = float(node.get("stroke-width", 1))
        if stroke == "none" or width == 0:
            return super().vector(node, matrix, opacity, clip)
        path = geometry(node, matrix)
        name, fill = figure_name(node), node.get("fill", "black")
        if fill != "none":
            self.freeform(path, name, fill, "none", 0, {"opacity": opacity * float(node.get("fill-opacity", 1))})
        zoom = math.hypot(matrix.xx, matrix.xy)
        cap = {
            "round": pathops.LineCap.ROUND_CAP,
            "butt": pathops.LineCap.BUTT_CAP,
            "square": pathops.LineCap.SQUARE_CAP,
        }[node.get("stroke-linecap", "butt")]
        join = {
            "round": pathops.LineJoin.ROUND_JOIN,
            "miter": pathops.LineJoin.MITER_JOIN,
            "bevel": pathops.LineJoin.BEVEL_JOIN,
        }[node.get("stroke-linejoin", "miter")]
        dashes = [length * zoom for length in numbers(node.get("stroke-dasharray", ""))]
        outline = pathops.Path(path)
        outline.stroke(width * zoom, cap, join, 4, dashes or None)
        outline.convertConicsToQuads(0.04)
        self.freeform(
            outline, name + " stroke", stroke, "none", 0, {"opacity": opacity * float(node.get("stroke-opacity", 1))}
        )


def main():
    root = ET.parse(OUTPUT.with_suffix(".svg")).getroot()
    _, _, art_width, art_height = numbers(root.get("viewBox"))
    # The existing Canva document is 1400 × 924 CSS pixels. The kit uses half-point drawing units.
    width, height = (size * 914400 / (96 * EMU) for size in (1400, 924))
    scale = min(width / art_width, height / art_height)
    x, y = (width - scale * art_width) / 2, (height - scale * art_height) / 2
    root.attrib.update({"width": f"{width:g}px", "height": f"{height:g}px", "viewBox": f"0 0 {width:g} {height:g}"})
    root.find(SVG + "rect").attrib.update({"width": f"{width:g}", "height": f"{height:g}"})
    layers = root.findall(SVG + "g")
    art = ET.SubElement(root, SVG + "g", transform=f"translate({x} {y}) scale({scale})")
    art.extend(layers)
    output = OUTPUT.with_name(OUTPUT.name + "_canva.pptx")
    with TemporaryDirectory(dir=output.parent) as tmp, ZipFile(KIT) as kit:
        work = Path(tmp)
        for face in ("Regular", "Bold"):
            filename = f"STIXTwoText-{face}.ttf"
            (work / filename).write_bytes(kit.read("Fonts/" + filename))
        page = CanvaPage(root, work)
        try:
            page.save(work / output.name)
        finally:
            for face in page.faces.values():
                face.close()
            page.fonts.clear()
        (work / output.name).replace(output)


if __name__ == "__main__":
    main()
