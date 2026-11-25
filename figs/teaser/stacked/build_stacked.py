"""Build the three-row Canva teaser from the editable GEAR-Nav figure kit."""

import math
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree as ET


HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1] / "canva" / "GEAR-Nav-Canva.zip"
OUTPUT = HERE / "gear_teaser_stacked"
SVG = "{http://www.w3.org/2000/svg}"
PADDING = 12
ROW_GAP = 18


def element(root, name):
    match, = root.xpath(".//*[@id=$name]", name=name)
    return match


def arrange_key(root, width, panel_bottom):
    key = element(root, "shared_refinement_key")
    key.attrib.pop("transform")
    divider = key.find(SVG + "line")
    line_y = panel_bottom + 11
    divider.attrib.update({
        "x1": str(PADDING), "x2": str(width - PADDING),
        "y1": str(line_y), "y2": str(line_y),
    })

    # Keep the original swatches, arrows, goal, gradient, and editable text.
    # At single-column width the two legend rows can use the same type size.
    stages = element(key, "shared_refinement_key_items")
    goal_label, = stages.xpath('./*[local-name()="text" and text()="Goal"]')
    goal_symbol = goal_label.getprevious()
    scale_key = ET.SubElement(key, SVG + "g", id="goal_and_distance_key")
    for item in list(stages)[stages.index(goal_symbol):]:
        scale_key.append(item)

    # Coordinates 620 and 1681 are the horizontal centers of the two source
    # legend segments. Both share a swatch centerline at y=536.
    for row, source_center, y in (
        (stages, 620, panel_bottom + 39),
        (scale_key, 1681, panel_bottom + 86),
    ):
        row.set("transform", f"translate({width / 2:g} {y:.5f}) scale(.86) "
                             f"translate({-source_center} -536)")


def stack(source):
    root = ET.fromstring(source)
    discarded = element(root, "scene_3")
    root.remove(discarded)
    defs = root.find(SVG + "defs")
    for definition in list(defs):
        if definition.get("id", "").startswith("scene_3_"):
            defs.remove(definition)

    next_top = PADDING
    for original, label in ((1, "(a)"), (2, "(b)"), (4, "(c)")):
        scene = element(root, f"scene_{original}")
        frame = element(scene, f"scene_{original}_frame")
        dx = PADDING - float(frame.get("x"))
        dy = next_top - float(frame.get("y"))
        scene.set("transform", f"translate({dx:.8f} {dy:.8f})")
        panel_label = element(scene, f"scene_{original}_panel_label")
        panel_label.find(SVG + "text").text = label
        next_top += float(frame.get("height")) + ROW_GAP

    width = int(float(frame.get("width"))) + 2 * PADDING
    panel_bottom = next_top - ROW_GAP
    height = math.ceil(panel_bottom + 137)
    arrange_key(root, width, panel_bottom)
    root.attrib.update({"viewBox": f"0 0 {width} {height}",
                        "width": f"{width}px", "height": f"{height}px"})
    root.find(SVG + "rect").attrib.update({"width": str(width), "height": str(height)})
    root.find(SVG + "title").text = "GEAR-Nav trajectory refinement"
    root.find(SVG + "desc").text = (
        "Top to bottom: a café sidewalk, a rainy night sidewalk, and a market passage. "
        "Each ESDF and camera view shows the same illustrative path stages. "
        "The initial path is sampled. Later stages are authored illustrations."
    )
    return ET.ElementTree(root)


def build():
    svg = OUTPUT.with_suffix(".svg")
    pdf = OUTPUT.with_suffix(".pdf")
    with ZipFile(KIT) as kit, TemporaryDirectory() as tmp:
        tree = stack(kit.read("Editable SVG/04-Teaser.svg"))
        tree.write(str(svg), encoding="UTF-8", xml_declaration=True)
        work = Path(tmp)
        for face in ("STIXTwoText-Regular.ttf", "STIXTwoText-Bold.ttf"):
            (work / face).write_bytes(kit.read("Fonts/" + face))
        config = ET.Element("fontconfig")
        ET.SubElement(config, "include").text = "/etc/fonts/fonts.conf"
        ET.SubElement(config, "dir").text = str(work)
        ET.SubElement(config, "cachedir").text = str(work / "font-cache")
        conf = work / "fonts.conf"
        ET.ElementTree(config).write(str(conf), encoding="UTF-8")
        env = dict(os.environ, FONTCONFIG_FILE=str(conf))
        intermediate = work / "source.pdf"
        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", intermediate, svg], env=env, check=True)
        subprocess.run([
            "gs", "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.7", "-dAutoRotatePages=/None",
            "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
            "-dEmbedAllFonts=true", f"-sOutputFile={pdf}", intermediate,
        ], env=env, check=True)
        subprocess.run(["pdftocairo", "-png", "-singlefile", "-scale-to-x", "1048",
                        "-scale-to-y", "-1", pdf, OUTPUT], env=env, check=True)


if __name__ == "__main__":
    build()
