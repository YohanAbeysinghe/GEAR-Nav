"""Render a side-by-side styling proof of the three-scene teaser."""

from io import BytesIO
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree as ET
from PIL import Image, ImageDraw, ImageFont

from build_stacked import HERE, KIT, OUTPUT, SVG, element


def proposed_style(root):
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


def main():
    root = ET.parse(str(OUTPUT.with_suffix(".svg"))).getroot()
    proposed_style(root)
    with TemporaryDirectory() as tmp, ZipFile(KIT) as kit:
        work = Path(tmp)
        for face in ("Regular", "Bold"):
            name = f"STIXTwoText-{face}.ttf"
            (work / name).write_bytes(kit.read("Fonts/" + name))
        config = ET.Element("fontconfig")
        ET.SubElement(config, "include").text = "/etc/fonts/fonts.conf"
        ET.SubElement(config, "dir").text = str(work)
        ET.SubElement(config, "cachedir").text = str(work / "cache")
        conf = work / "fonts.conf"
        ET.ElementTree(config).write(str(conf))
        png = subprocess.run(["rsvg-convert", "-b", "white"], input=ET.tostring(root),
                             env=dict(os.environ, FONTCONFIG_FILE=str(conf)),
                             check=True, stdout=subprocess.PIPE).stdout
        proposed = Image.open(BytesIO(png)).convert("RGB")
        current = Image.open(OUTPUT.with_suffix(".png")).convert("RGB")
        proof = Image.new("RGB", (2320, 1504), "#F0F1F2")
        draw = ImageDraw.Draw(proof)
        heading = ImageFont.truetype(str(work / "STIXTwoText-Bold.ttf"), 36)
        for title, img, x in (("Current", current, 32), ("Proposed", proposed, 1184)):
            draw.text((x, 18), title, font=heading, fill="#242A30")
            proof.paste(img, (x, 78))
        proof.save(HERE / "visual_comparison.jpg", quality=93, subsampling=0, optimize=True)


if __name__ == "__main__":
    main()
