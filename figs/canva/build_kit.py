"""Build the six-figure kit from the workspace or from an extracted archive.

Run `python build_kit.py --from-kit /path/to/extracted-kit` for an offline
rebuild. The exporter uses python-pptx 1.0.2, skia-pathops 0.8.0.post2,
FontTools, OpenCV, NumPy, Pillow and lxml. Rendering uses rsvg-convert,
Ghostscript, LibreOffice Impress and Poppler. The original workspace build downloads the
two licensed STIX faces unless a verified --fonts directory is supplied.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import posixpath
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

import cv2
from editable_pptx import EMU
from editable_pptx import Slide
from editable_pptx import figure_name
from editable_pptx import image_data
from editable_pptx import numbers
from editable_pptx import tag
from editable_pptx import transform
from fontTools.misc.transform import Identity
from lxml import etree as ET
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent
FONT_REVISION = "744a22a4dd626cd14d75728aef34fc8ad7c85db0"
FONT_URL = f"https://raw.githubusercontent.com/stipub/stixfonts/{FONT_REVISION}/"
FONT_HASHES = {
    "STIXTwoText-Regular.ttf": "0566a1be411c0b2463fad8563b33f1c299442b8882c7fce9ef95e079f43233da",
    "STIXTwoText-Bold.ttf": "89adbb9907c40465e061f084598dbebd5a802e30c6e2d38612205b9c87281cae",
    "OFL.txt": "0c8825913b60d858aacdb33c4ca6660a7d64b0d6464702efbb19313f5765861a",
}


@dataclass(frozen=True)
class Figure:
    stem: str
    title: str
    source: str
    frame: str
    equations: str = ""
    adjustment: str = ""


FIGURES = (
    Figure(
        "01-Pipeline",
        "Pipeline",
        "figma_sync/gear_pipeline_final_20261029/pipeline_upload.svg",
        "Kq08SDzEtcJXw4VazviTWy/Astar---Pipeline?node-id=4-2",
        "pipeline/equations.json",
    ),
    Figure(
        "02-Original-Model",
        "Original model diagram",
        "figma_sync/contrast_revision_20261026/model_upload.svg",
        "twSYxYaV3PrBTfHVBGjkXQ/Astar---Model-Diagram?node-id=4-2",
        "model/equations.json",
        "The saved Figma placement moved the cached oracle target symbol 14 design units to the right.",
    ),
    Figure(
        "03-Paper-Model",
        "Simplified paper model",
        "figma_sync/model_publication_flow_20261029/model_simple_upload.svg",
        "l0fcecr2A1QI6cixD7GaP6/Astar---Model_Simple?node-id=5-48",
        "model_simple/equations.json",
        "The saved Figma placement centers the goal-modality label at x=330 with −0.7-unit letter spacing.",
    ),
    Figure(
        "04-Teaser",
        "Teaser",
        "teaser/compact/figma_sync/teaser_upload.svg",
        "63xZwS3SRmnpVyrBe3Q7f3/Astar---Teaser?node-id=17-2",
    ),
    Figure(
        "05-Supplementary",
        "Supplementary figure",
        "supplementary/supplementary.svg",
        "8M8sL3KmT4wxeUgFyh8Tvv/Astar---Supplementary?node-id=4-75",
        "supplementary/equations.json",
        "Uses the corrected local supplementary master and its recorded sixth-iteration middle path.",
    ),
    Figure(
        "06-Real-World-and-Isaac-Sim",
        "Real-world and Isaac Sim",
        "realworld_isaacsim/figma_import.svg",
        "3RjwsUydxXrFOknU4HhcTy/GEAR-Realworld-Issacsim?node-id=3-8",
    ),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command(args, env):
    return subprocess.run([str(a) for a in args], env=env, check=True, capture_output=True, text=True).stdout


def prepare_fonts(kit, work, existing):
    fonts = kit / "Fonts"
    for name, expected in FONT_HASHES.items():
        if existing:
            data = (existing / name).read_bytes()
        else:
            with urlopen(
                FONT_URL + ("fonts/static_ttf/" if name.endswith(".ttf") else "") + name, timeout=30
            ) as response:
                data = response.read()
        if digest(data) != expected:
            raise ValueError(f"Unexpected STIX source hash for {name}")
        (fonts / name).write_bytes(data)
    config = ET.Element("fontconfig")
    ET.SubElement(config, "include").text = "/etc/fonts/fonts.conf"
    ET.SubElement(config, "dir").text = str(fonts)
    ET.SubElement(config, "cachedir").text = str(work / "font-cache")
    conf = work / "fontconfig.xml"
    ET.ElementTree(config).write(str(conf), encoding="utf-8", xml_declaration=True)
    return dict(os.environ, FONTCONFIG_FILE=str(conf), XDG_CACHE_HOME=str(work / "cache"))


def source_svg(figure, kit, existing):
    source = existing / "Editable SVG" / (figure.stem + ".svg") if existing else FIGS / figure.source
    raw = source.read_bytes()
    root = ET.fromstring(raw)
    if not existing:
        if figure.stem == "02-Original-Model":
            (target,) = root.xpath('//*[@id="cached-target_cached-target"]')
            target.set("x", str(float(target.get("x")) + 14))
        elif figure.stem == "03-Paper-Model":
            (label,) = root.xpath('//*[local-name()="text" and text()="Text / Image / Metric"]')
            label.set("x", "330")
            label.set("letter-spacing", "-0.7")
    _, _, w, h = numbers(root.get("viewBox"))
    root.set("width", f"{w:g}px")
    root.set("height", f"{h:g}px")
    root.set("version", "1.1")
    destination = kit / "Editable SVG" / (figure.stem + ".svg")
    ET.ElementTree(root).write(str(destination), encoding="UTF-8", xml_declaration=True)
    if figure.equations:
        name = figure.stem + ".json"
        source_eq = existing / "Equation sources" / name if existing else FIGS / figure.equations
        shutil.copyfile(source_eq, kit / "Equation sources" / name)
        formulas = json.loads(source_eq.read_text(encoding="utf-8"))
        tex = "\n\n".join(f"% {key}\n{formula}" for key, formula in formulas.items())
        (kit / "Equation sources" / (figure.stem + ".tex")).write_text(tex + "\n", encoding="utf-8")
    return root, destination, digest(raw)


def picture_sources(root, kit, figure):
    out = kit / "Images" / figure.stem
    out.mkdir()
    visible = []
    for i, node in enumerate(root.xpath('//*[local-name()="image"]'), 1):
        data = image_data(node)
        mask = any(tag(parent) == "mask" for parent in node.iterancestors())
        name = figure_name(node).replace(" ", "-")
        if mask:
            name = node.getparent().get("id")
        suffix = "png" if data.startswith(b"\x89PNG") else "jpg"
        (out / f"{i:02d}-{name}.{suffix}").write_bytes(data)
        if not mask:
            visible.append(digest(data))
    return visible


def inspect_powerpoint(file, root, images):
    with ZipFile(file) as z:
        if z.testzip():
            raise ValueError(f"Damaged PowerPoint: {file}")
        slide = ET.fromstring(z.read("ppt/slides/slide1.xml"))
        deck = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/slides/_rels/slide1.xml.rels"))
        media = {r.get("Id"): posixpath.normpath(posixpath.join("ppt/slides", r.get("Target"))) for r in rels}
        nodes = slide.xpath('//*[local-name()="sp"]')
        text_boxes = [n for n in nodes if n.find("{*}txBody") is not None]
        labels = ["".join(n.xpath('.//*[local-name()="t"]/text()')) for n in text_boxes]
        source_labels = ["".join(t.itertext()) for t in root.xpath('//*[local-name()="text"]')]
        if labels != source_labels:
            raise ValueError(f"{file.stem}: an SVG label did not become a matching native text box")
        title_names = [n.find("{*}nvSpPr/{*}cNvPr").get("name") for n in nodes]
        equations = [s for s in title_names if s.startswith("Equation · ")]
        source_equations = root.xpath('.//*[local-name()="svg"]')
        if len(equations) != len(source_equations):
            raise ValueError(f"{file.stem}: the equation outlines do not match the source")
        pictures = slide.xpath('//*[local-name()="pic"]')
        picture_hashes = []
        for pic in pictures:
            blip = pic.find(".//{*}blip")
            rel = next(v for k, v in blip.attrib.items() if k.endswith("}embed"))
            picture_hashes.append(digest(z.read(media[rel])))
        if picture_hashes != images:
            raise ValueError(f"{file.stem}: a picture differs from its embedded source")
        _, _, w, h = numbers(root.get("viewBox"))
        size = deck.find("{*}sldSz")
        if (int(size.get("cx")), int(size.get("cy"))) != (round(w * EMU), round(h * EMU)):
            raise ValueError(f"{file.stem}: the slide dimensions differ from the source")
        groups = len(slide.xpath('//*[local-name()="grpSp"]'))
        if len(nodes) + len(pictures) + groups > 1400:
            raise ValueError(f"{file.stem}: exceeds Canva's published per-file element limit")
        return {
            "editable_text_boxes": len(labels),
            "vector_shapes": len(nodes) - len(labels),
            "equations_in_vector_shapes": len(equations),
            "picture_objects": len(pictures),
            "groups": groups,
        }


def compare_render(source_png, rendered_pdf, svg, work, env):
    prefix = work / ("proof-" + rendered_pdf.stem)
    command(["pdftoppm", "-png", "-singlefile", "-scale-to-x", "1500", "-scale-to-y", "-1", rendered_pdf, prefix], env)
    expected = cv2.imread(str(source_png))
    actual = cv2.imread(str(prefix.with_suffix(".png")))
    actual = cv2.resize(actual, (expected.shape[1], expected.shape[0]), interpolation=cv2.INTER_AREA)
    # An importer can lose all but the first two gradient stops in a small legend.
    root = ET.parse(svg).getroot()
    _, _, w, h = numbers(root.get("viewBox"))
    for bar in root.xpath('//*[starts-with(@fill, "url(")]'):
        matrix = Identity
        for group in reversed(list(bar.iterancestors())):
            matrix = transform(matrix, group.get("transform"))
        bx, by, bw, bh = [float(bar.get(k)) for k in ("x", "y", "width", "height")]
        for ratio in (0.055, 0.255, 0.505, 0.755, 0.955):
            x, y = matrix.transformPoint((bx + bw * ratio, by + bh / 2))
            i, j = round(y * expected.shape[0] / h), round(x * expected.shape[1] / w)
            if np.max(np.abs(expected[i, j].astype(float) - actual[i, j])) > 15:
                raise ValueError(f"{rendered_pdf.stem}: ESDF legend color mismatch")
    # Reduce differences from font hinting and subpixel rasterization in the two renderers.
    delta = np.abs(
        cv2.GaussianBlur(actual.astype(np.float32), (0, 0), 2)
        - cv2.GaussianBlur(expected.astype(np.float32), (0, 0), 2)
    ).mean(axis=2)
    mean = round(float(np.mean(delta)), 3)
    if mean > 4:
        raise ValueError(f"{rendered_pdf.stem}: visual comparison needs inspection ({mean}/255)")
    return mean


def overview(kit):
    sheet = Image.new("RGB", (1920, 1256), "#f1f3f5")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(kit / "Fonts/STIXTwoText-Bold.ttf"), 28)
    for i, fig in enumerate(FIGURES):
        left, top = 20 + i % 3 * 634, 16 + i // 3 * 620
        draw.rectangle((left, top, left + 610, top + 598), fill="white")
        draw.text((left + 16, top + 9), fig.title, font=font, fill="#24313c")
        with Image.open(kit / "Previews" / (fig.stem + ".png")) as im:
            im.thumbnail((584, 526), Image.Resampling.LANCZOS)
            sheet.paste(im, (left + (610 - im.width) // 2, top + 52 + (526 - im.height) // 2))
    sheet.save(kit / "Figure index.jpg", quality=93, optimize=True)


def build(output, existing=None, fonts=None):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="gear-canva-") as tmp:
        work = Path(tmp)
        kit = work / "kit"
        for folder in ("Canva import", "Editable SVG", "Vector PDF", "Previews", "Images", "Equation sources", "Fonts"):
            (kit / folder).mkdir(parents=True)
        env = prepare_fonts(kit, work, fonts or (existing / "Fonts" if existing else None))
        manifest = {
            "font_revision": FONT_REVISION,
            "verification": "Local PowerPoint XML and LibreOffice rendering",
            "figures": {},
        }
        for fig in FIGURES:
            root, source, source_hash = source_svg(fig, kit, existing)
            deck = kit / "Canva import" / (fig.stem + ".pptx")
            source_pdf = kit / "Vector PDF" / (fig.stem + ".pdf")
            preview = kit / "Previews" / (fig.stem + ".png")
            images = picture_sources(root, kit, fig)
            Slide(root, kit / "Fonts", fig.title).save(deck)
            _, _, w, h = numbers(root.get("viewBox"))
            intermediate = work / "svg-source.pdf"
            command(
                ["rsvg-convert", "-f", "pdf", "-w", round(w / 2), "-h", round(h / 2), "-o", intermediate, source], env
            )
            command(
                [
                    "gs",
                    "-q",
                    "-dBATCH",
                    "-dNOPAUSE",
                    "-sDEVICE=pdfwrite",
                    "-dCompatibilityLevel=1.7",
                    "-dAutoRotatePages=/None",
                    "-dDownsampleColorImages=false",
                    "-dDownsampleGrayImages=false",
                    "-dEmbedAllFonts=true",
                    f"-sOutputFile={source_pdf}",
                    intermediate,
                ],
                env,
            )
            command(["rsvg-convert", "-b", "white", "-w", "1500", "-o", preview, source], env)
            if not command(["pdftotext", source_pdf, "-"], env).strip():
                raise ValueError(f"{fig.stem}: reference PDF has no selectable text")
            record = {
                "title": fig.title,
                "figma_frame": "https://www.figma.com/design/" + fig.frame,
                "source": str(source.relative_to(kit)) if existing else "figs/" + fig.source,
                "input_sha256": source_hash,
                "packaged_svg_sha256": digest(source.read_bytes()),
                "size_in_design_units": [w, h],
                **inspect_powerpoint(deck, root, images),
            }
            if fig.adjustment:
                record["source_note"] = fig.adjustment
            if fig.equations:
                eq = json.loads((kit / "Equation sources" / (fig.stem + ".json")).read_text())
                ids = [e.get("id").split("_")[0] for e in root.xpath('.//*[local-name()="svg"]')]
                if Counter(ids) != Counter(eq.keys()):
                    raise ValueError(f"{fig.stem}: LaTeX keys do not match the equation drawings")
            manifest["figures"][fig.stem] = record

        decks = sorted((kit / "Canva import").glob("*.pptx"))
        command(
            [
                "soffice",
                "-env:UserInstallation=" + (work / "lo-profile").as_uri(),
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                work,
                *decks,
            ],
            env,
        )
        for deck in decks:
            rendered = work / (deck.stem + ".pdf")
            metrics = manifest["figures"][deck.stem]
            if "STIXTwoText" not in command(["pdffonts", rendered], env):
                raise ValueError(f"{deck.stem}: round trip lost the STIX Two Text font")
            metrics["blurred_mean_rgb_error_of_255"] = compare_render(
                kit / "Previews" / (deck.stem + ".png"),
                rendered,
                kit / "Editable SVG" / (deck.stem + ".svg"),
                work,
                env,
            )
        overview(kit)
        shutil.copyfile(HERE / "README.md", kit / "START HERE.md")
        write_json(kit / "manifest.json", manifest)
        archive = work / "bundle.zip"
        with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=7) as z:
            for file in sorted(kit.rglob("*")):
                if file.is_file():
                    z.write(file, file.relative_to(kit))
        with ZipFile(archive) as z:
            if z.testzip() or len([n for n in z.namelist() if n.endswith(".pptx")]) != len(FIGURES):
                raise ValueError("Final ZIP verification failed")
        shutil.copyfile(archive, output.with_suffix(".zip.tmp"))
        output.with_suffix(".zip.tmp").replace(output)
        shutil.copyfile(kit / "Figure index.jpg", output.with_suffix(".jpg"))
        for name, stats in manifest["figures"].items():
            print(
                name,
                stats["editable_text_boxes"],
                "labels,",
                stats["vector_shapes"],
                "vectors,",
                stats["picture_objects"],
                "pictures",
            )
        print(output, output.stat().st_size, "bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "GEAR-Nav-Canva.zip")
    parser.add_argument("--from-kit", type=Path, help="Use the SVGs, equations and fonts in an extracted kit")
    parser.add_argument("--fonts", type=Path, help="Use these previously downloaded STIX fonts")
    args = parser.parse_args()
    build(args.output, args.from_kit, args.fonts)
