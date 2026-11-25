"""Render a side-by-side styling proof of the three-scene teaser."""

from io import BytesIO
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree as ET
from PIL import Image, ImageDraw, ImageFont

from build_stacked import HERE, KIT, apply_panel_style, stack


def main():
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
        root = stack(kit.read("Editable SVG/04-Teaser.svg")).getroot()
        env = dict(os.environ, FONTCONFIG_FILE=str(conf))

        def render():
            png = subprocess.run(["rsvg-convert", "-b", "white"], input=ET.tostring(root),
                                 env=env, check=True, stdout=subprocess.PIPE).stdout
            return Image.open(BytesIO(png)).convert("RGB")

        current = render()
        apply_panel_style(root)
        proposed = render()
        proof = Image.new("RGB", (2320, 1504), "#F0F1F2")
        draw = ImageDraw.Draw(proof)
        heading = ImageFont.truetype(str(work / "STIXTwoText-Bold.ttf"), 36)
        for title, img, x in (("Current", current, 32), ("Proposed", proposed, 1184)):
            draw.text((x, 18), title, font=heading, fill="#242A30")
            proof.paste(img, (x, 78))
        proof.save(HERE / "visual_comparison.jpg", quality=93, subsampling=0, optimize=True)


if __name__ == "__main__":
    main()
