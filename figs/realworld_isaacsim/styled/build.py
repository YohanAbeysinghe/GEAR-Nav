"""Restyle the six-scene Canva master from the local figure kit."""

import argparse
import base64
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from fontTools.ttLib import TTFont
from lxml import etree as ET
from PIL import ImageFont

HERE = Path(__file__).resolve().parent
FIGS = HERE.parents[1]
sys.path.insert(0, str(FIGS))
import figure_style  # noqa: E402

KIT = FIGS / "canva" / "GEAR-Nav-Canva.zip"
SOURCE = "Editable SVG/06-Real-World-and-Isaac-Sim.svg"
OUTPUT = HERE / "gear_realworld_isaacsim"
SVG = "{http://www.w3.org/2000/svg}"
WIDTH, INCHES = 1020, 3.4
MARGIN, GUTTER = 12, 18
PHOTO_WIDTH = (WIDTH - 2 * MARGIN - 2 * GUTTER) / 3
HEADING_SIZE, CAPTION_SIZE, KEY_SIZE = 37.5, 31, 30
INK, RULE = "#30363D", "#CDD2D6"
COLORS = {
    "GEAR-Nav": figure_style.TEASER_STAGE_COLORS["refined"],
    "OmniVLA": figure_style.TEASER_STAGE_COLORS["early"],
    "TIC-VLA": "#B43D82",
    "NaVILA": figure_style.TEASER_STAGE_COLORS["intermediate"],
}
# Distinguish the three reference routes even in a grayscale print.
DASHES = {"OmniVLA": (1.1, 5.8), "TIC-VLA": (9, 6.7)}


def add(parent, tag, **attributes):
    attrs = {key.replace("_", "-"): str(value) for key, value in attributes.items()}
    return ET.SubElement(parent, SVG + tag, attrs)


def label(parent, value, x, baseline, size, *, bold=False, anchor="start"):
    node = add(
        parent,
        "text",
        x=x,
        y=baseline,
        font_size=size,
        font_family=figure_style.SVG_FONT_FAMILY,
        font_weight="700" if bold else "400",
        fill=INK,
        text_anchor=anchor,
    )
    node.text = value


def embed_fonts(root, kit, fonts):
    """Browsers can use the embedded faces. Pango and Impress use the same local TTFs."""
    rules = []
    for weight, name in ((400, "Regular"), (700, "Bold")):
        filename = f"STIXTwoText-{name}.ttf"
        raw = kit.read("Fonts/" + filename)
        (fonts / filename).write_bytes(raw)
        with TTFont(BytesIO(raw), recalcTimestamp=False) as face:
            face.flavor = "woff"
            buf = BytesIO()
            face.save(buf)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{figure_style.FONT}';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{encoded}) format('woff')}}"
        )
    add(add(root, "defs"), "style", type="text/css").text = "\n".join(rules)


def restyle_scene(scene, scale, source_colors):
    """Paint the original curves, arrowheads and crosses in place."""
    for node in list(scene):
        method = source_colors.get(node.get("stroke"))
        for attr in ("stroke", "fill"):
            name = source_colors.get(node.get(attr))
            if name:
                node.set(attr, COLORS[name])
        if node.tag == SVG + "path" and method:
            width = 4.3 if method == "GEAR-Nav" else 2.9
            halo = node.getprevious()
            if halo.get("d") != node.get("d"):
                raise ValueError(f"Unpaired route outline for {node.get('id')}")
            node.set("stroke-width", f"{width / scale:.5f}")
            halo.set("stroke-width", f"{(width + 2.0) / scale:.5f}")
            halo.set("stroke-opacity", ".95")
            if method in DASHES:
                pattern = " ".join(f"{length / scale:.5f}" for length in DASHES[method])
                node.set("stroke-dasharray", pattern)
                halo.set("stroke-dasharray", pattern)
        elif node.tag == SVG + "rect":
            node.set("stroke", "#B8BFC5")
            node.set("stroke-width", f"{0.8 / scale:.5f}")
        elif node.get("id", "").endswith("-goal"):
            node.set("fill", figure_style.GOAL_FILL)
            xs, ys = polygon_axes(node)
            # The mean of a five-point star's vertices is its annotated center.
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            group = add(scene, "g", transform=f"translate({cx} {cy}) scale(1.23) translate({-cx} {-cy})")
            group.append(node)


def scene_row(root, source, section_id, baseline, source_colors):
    original = source.find(f"{SVG}g[@id='{section_id}']")
    section = ET.SubElement(root, SVG + "g", original.attrib)
    heading, *captions = original.findall(SVG + "text")
    label(section, heading.text, MARGIN, baseline, HEADING_SIZE, bold=True)
    top = baseline + 17
    for index, (old_scene, caption) in enumerate(zip(original.findall(SVG + "g"), captions, strict=True)):
        scene = deepcopy(old_scene)
        photo = scene.find(SVG + "image")
        x, y, width, height = (float(photo.get(k)) for k in ("x", "y", "width", "height"))
        left = MARGIN + index * (PHOTO_WIDTH + GUTTER)
        scale = PHOTO_WIDTH / width
        # A single transform keeps each photograph and every annotation registered.
        scene.set("transform", f"translate({left:g} {top:g}) scale({scale:.12f}) translate({-x} {-y})")
        restyle_scene(scene, scale, source_colors)
        section.append(scene)
        caption_y = top + height * scale + 32
        label(section, caption.text, left + PHOTO_WIDTH / 2, caption_y, CAPTION_SIZE, anchor="middle")
    return caption_y


def polygon_axes(node):
    points = [tuple(map(float, pair.split(","))) for pair in node.get("points").split()]
    return zip(*points)


def marker_sample(parent, original, left, center_y, width):
    xs, ys = polygon_axes(original)
    scale = width / (max(xs) - min(xs))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    transform = f"translate({left + width / 2} {center_y}) scale({scale}) translate({-cx} {-cy})"
    add(parent, "g", transform=transform).append(deepcopy(original))


def legend(root, original, fonts, top):
    key = ET.SubElement(root, SVG + "g", original.attrib)
    add(key, "line", x1=MARGIN, x2=WIDTH - MARGIN, y1=top, y2=top, stroke=RULE, stroke_width=1.1)
    baseline = top + 34
    faces = {name: ImageFont.truetype(str(fonts / f"STIXTwoText-{name}.ttf"), 512) for name in ("Regular", "Bold")}
    entries = []
    for caption in original.findall(SVG + "text"):
        name = caption.text.removesuffix(" (ours)")
        icon = {"Goal": 22, "Failure": 15}.get(name, 32)
        face = faces["Bold" if name == "GEAR-Nav" else "Regular"]
        width = icon + 7 + face.getlength(name) * KEY_SIZE / 512
        entries.append((name, caption.getprevious(), icon, width))
    gap = (WIDTH - 2 * MARGIN - sum(width for _, _, _, width in entries)) / (len(entries) - 1)
    if gap < 12:
        raise ValueError("The shared legend needs more space between entries")
    left = MARGIN
    for name, symbol, icon, width in entries:
        bold = name == "GEAR-Nav"
        item = add(key, "g", id="key-" + name)
        center_y = baseline - KEY_SIZE * 0.33
        if name in COLORS:
            swatch = add(
                item,
                "line",
                x1=left,
                x2=left + icon,
                y1=center_y,
                y2=center_y,
                stroke=COLORS[name],
                stroke_width=4.3 if bold else 2.9,
                stroke_linecap="round",
            )
            if name in DASHES:
                swatch.set("stroke-dasharray", " ".join(map(str, DASHES[name])))
        else:
            marker_sample(item, symbol, left, center_y, icon)
        label(item, name, left + icon + 7, baseline, KEY_SIZE, bold=bold)
        left += width + gap
    return math.ceil(baseline + 14)


def compose(kit, fonts):
    raw = kit.read(SOURCE)
    source = ET.fromstring(raw)
    root = ET.Element(SVG + "svg", nsmap=source.nsmap)
    for name in ("title", "desc"):
        root.append(deepcopy(source.find(SVG + name)))
    metadata = add(root, "metadata")
    metadata.text = json.dumps(
        {
            "source": f"figs/canva/{KIT.name} / {SOURCE}",
            "source_sha256": sha256(raw).hexdigest(),
            "canva_design": "DAHbx9IfKNo",
            "geometry": "Each scene uses one uniform transform for the archived photograph, routes and markers.",
            "font_license": kit.read("Fonts/OFL.txt").decode("utf-8"),
        },
        ensure_ascii=False,
    )
    embed_fonts(root, kit, fonts)
    background = add(root, "rect", width=WIDTH, fill="white")
    key = source.find(f"{SVG}g[@id='shared-legend']")
    source_colors = {p.get("stroke"): p.getnext().text.removesuffix(" (ours)") for p in key.findall(SVG + "path")}
    bottom = scene_row(root, source, "real-world", 37, source_colors)
    bottom = scene_row(root, source, "isaac-sim", bottom + 57, source_colors)
    height = legend(root, key, fonts, bottom + 19)
    background.set("height", str(height))
    root.attrib.update(
        {"viewBox": f"0 0 {WIDTH} {height}", "width": f"{INCHES}in", "height": f"{INCHES * height / WIDTH:.9f}in"}
    )
    return root, height


def build(with_pptx):
    with ZipFile(KIT) as kit, TemporaryDirectory(dir=HERE, prefix=".render-") as tmp:
        work = Path(tmp)
        staged = work / OUTPUT.name
        svg, pdf, png = (staged.with_suffix(ext) for ext in (".svg", ".pdf", ".png"))
        root, height = compose(kit, work)
        ET.ElementTree(root).write(str(svg), encoding="UTF-8", xml_declaration=True)
        config = ET.Element("fontconfig")
        ET.SubElement(config, "include").text = "/etc/fonts/fonts.conf"
        ET.SubElement(config, "dir").text = str(work)
        ET.SubElement(config, "cachedir").text = str(work / "font-cache")
        conf = work / "fonts.conf"
        ET.ElementTree(config).write(str(conf))
        env = dict(os.environ, FONTCONFIG_FILE=str(conf))
        intermediate = work / "source.pdf"
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", "-w", str(WIDTH), "-h", str(height), "-o", intermediate, svg],
            check=True,
            env=env,
        )
        subprocess.run(
            [
                "gs",
                "-q",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.7",
                "-dAutoRotatePages=/None",
                "-dFIXEDMEDIA",
                "-dPDFFitPage",
                "-dEmbedAllFonts=true",
                "-dDownsampleColorImages=false",
                f"-dDEVICEWIDTHPOINTS={INCHES * 72:.6f}",
                f"-dDEVICEHEIGHTPOINTS={INCHES * 72 * height / WIDTH:.6f}",
                f"-sOutputFile={pdf}",
                intermediate,
            ],
            check=True,
            env=env,
        )
        subprocess.run(
            ["pdftocairo", "-png", "-singlefile", "-scale-to-x", "1530", "-scale-to-y", "-1", pdf, staged],
            check=True,
            env=env,
        )
        exports = [svg, pdf, png]
        if with_pptx:
            sys.path.insert(0, str(FIGS / "canva"))
            from editable_pptx import Slide

            deck = staged.with_suffix(".pptx")
            Slide(root, work, "GEAR-Nav real-world and Isaac Sim scenes").save(deck)
            exports.append(deck)
        for path in exports:
            path.replace(HERE / path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", action="store_true", help="also write the editable Canva import")
    build(parser.parse_args().pptx)
