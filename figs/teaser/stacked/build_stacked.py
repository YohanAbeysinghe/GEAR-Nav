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

    stages = element(key, "shared_refinement_key_items")
    goal_label, = stages.xpath('./*[local-name()="text" and text()="Goal"]')
    for item in list(goal_label.itersiblings()):
        stages.remove(item)

    for stage, left, label in (
        ("initial", 50, "Initial"),
        ("early", 290, "Ref 1"),
        ("intermediate", 520, "Ref 2"),
        ("refined", 751, "GEAR-Nav"),
    ):
        swatch = element(stages, f"legend_{stage}_swatch")
        swatch.set("x1", str(left))
        swatch.set("x2", str(left + 52))
        caption = swatch.getnext()
        caption.set("x", str(left + 67))
        caption.text = label

    arrows = stages.findall(f"{SVG}path[@fill='none']")
    for arrow, left in zip(arrows, (220, 448, 677), strict=True):
        arrow.set("d", f"M {left} 536 h 46 m -8 -7 l 8 7 -8 7")
    goal_label.getprevious().set("transform", "translate(-290 0)")
    goal_label.set("x", "1053")
    # Center the complete key within the same width as the three scene pairs.
    stages.set("transform", f"translate({width / 2:g} {panel_bottom + 39:.5f}) "
                            "scale(.92) translate(-584 -536)")


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
    height = math.ceil(panel_bottom + 66)
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


def apply_panel_style(root):
    """Place shared headings and margin labels around the three scene pairs."""
    width, height = 1104, 1388
    root.attrib.update({"viewBox": f"0 0 {width} {height}",
                        "width": f"{width}px", "height": f"{height}px"})
    root.find(SVG + "rect").attrib.update({"width": str(width), "height": str(height)})
    font = element(root, "scene_1_panel_label").find(SVG + "text").get("font-family")
    for x, label in ((56, "ESDF"), (365.45, "Camera view")):
        heading = ET.SubElement(root, SVG + "text", x=str(x), y="36", fill="#30363D")
        heading.attrib.update({"font-family": font, "font-size": "28", "font-weight": "700"})
        heading.text = label

    for index, number in enumerate((1, 2, 4)):
        scene = element(root, f"scene_{number}")
        scene.set("transform", f"translate(44 {40 + 10 * index}) {scene.get('transform')}")
        frame = element(scene, f"scene_{number}_frame")
        left, top = float(frame.get("x")), float(frame.get("y"))
        scene.remove(frame)
        inset = element(scene, f"scene_{number}_ESDF_inset")
        esdf, = inset.xpath('./*[local-name()="text" and text()="ESDF"]')
        inset.remove(esdf.getprevious())
        inset.remove(esdf)
        panel = element(scene, f"scene_{number}_panel_label")
        panel.remove(panel.find(SVG + "rect"))
        letter = panel.find(SVG + "text")
        letter.attrib.update({"x": str(left - 9), "y": str(top + 22), "font-size": "26",
                              "font-weight": "700", "fill": "#30363D"})
        for suffix, color, weight in (("halo", "#FFFFFF", "6"), ("path", "#F34B0B", "2")):
            path = element(scene, f"scene_{number}_camera_refined_{suffix}")
            path.attrib.update({"stroke": color, "stroke-width": weight,
                                "stroke-linejoin": "round"})

    element(root, "shared_refinement_key").set("transform", "translate(44 62)")


def build():
    svg = OUTPUT.with_suffix(".svg")
    pdf = OUTPUT.with_suffix(".pdf")
    with ZipFile(KIT) as kit, TemporaryDirectory() as tmp:
        tree = stack(kit.read("Editable SVG/04-Teaser.svg"))
        apply_panel_style(tree.getroot())
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
        width = tree.getroot().get("viewBox").split()[2]
        subprocess.run(["pdftocairo", "-png", "-singlefile", "-scale-to-x", width,
                        "-scale-to-y", "-1", pdf, OUTPUT], env=env, check=True)


if __name__ == "__main__":
    build()
