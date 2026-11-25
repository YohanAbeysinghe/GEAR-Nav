"""Build a timestamped strip from the external-camera recording of Scene 3."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import INK, SVG_FONT_FAMILY
from svg_diagram import export_pdf

MOVIE = HERE.parent / "realworld_exp/Scene 3/ASTAR/IMG_4546.MOV"
SVG = HERE / "pedestrian_pass.svg"
WIDTH_IN = 7.08
STAGES = [(20.0, "Pedestrian approaches"), (27.5, "Pedestrian passes"),
          (30.5, "Walkway clears"), (54.0, "Robot nears scooter")]


def extract(video):
    import cv2

    gap, panel = 4, 174
    image_height = 235
    width = panel * len(STAGES) + gap * (len(STAGES) - 1)
    height = image_height + 21
    ns = "http://www.w3.org/2000/svg"
    xlink = "http://www.w3.org/1999/xlink"
    ET.register_namespace("", ns)
    ET.register_namespace("xlink", xlink)
    svg = ET.Element(f"{{{ns}}}svg", {
        "width": f"{WIDTH_IN}in", "height": f"{WIDTH_IN * height / width:.6f}in",
        "viewBox": f"0 0 {width} {height}",
    })
    ET.SubElement(svg, "title").text = "A pedestrian passes the robot on its approach to the scooter"
    ET.SubElement(svg, "rect", width=str(width), height=str(height), fill="white")
    provenance = {"source": video.name, "scene": 3, "view": "external camera", "frames": []}
    with video.open("rb") as stream:
        provenance["source_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    capture = cv2.VideoCapture(str(video))
    try:
        for i, (seconds, label) in enumerate(STAGES):
            capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
            ok, frame = capture.read()
            actual = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not ok or abs(actual - seconds) > .05:
                raise RuntimeError(f"Could not decode the frame at {seconds} seconds")
            h, w = frame.shape[:2]
            crop_height = round(w * image_height / panel)
            top = h - crop_height
            if top < 0:
                raise ValueError(f"Expected a portrait recording, got {w} × {h}")
            cropped = frame[top:, :]
            thumb = cv2.resize(cropped, (panel * 4, image_height * 4), interpolation=cv2.INTER_AREA)
            ok, jpeg = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 91])
            if not ok:
                raise RuntimeError("Could not encode the selected frame")
            image = base64.b64encode(jpeg).decode("ascii")
            x = i * (panel + gap)
            group = ET.SubElement(svg, "g", id=f"stage-{i+1}")
            ET.SubElement(group, "image", {
                "x": str(x), "width": str(panel), "height": str(image_height), f"{{{xlink}}}href": "data:image/jpeg;base64," + image,
            })
            text = ET.SubElement(group, "text", {
                "x": str(x + 1), "y": str(image_height + 15), "font-size": "11.8",
                "font-family": SVG_FONT_FAMILY, "fill": INK,
            })
            ET.SubElement(text, "tspan", {"font-weight": "bold"}).text = f"{actual:.1f} s"
            ET.SubElement(text, "tspan", dx="5").text = label
            provenance["frames"].append({"requested_s": seconds, "decoded_s": actual,
                                         "displayed_frame_index": int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
                                         "source_size_px": [w, h], "crop_xywh_px": [0, top, w, crop_height]})
    finally:
        capture.release()
    ET.SubElement(svg, "metadata").text = json.dumps(provenance)
    ET.ElementTree(svg).write(SVG, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", action="store_true", help="refresh the embedded frames from the original movie")
    args = parser.parse_args()
    if args.extract:
        extract(MOVIE)
    _, _, width, height = map(float, ET.parse(SVG).getroot().get("viewBox").split())
    export_pdf([SVG], SVG.with_suffix(".pdf"), WIDTH_IN * 25.4, WIDTH_IN * 25.4 * height / width)
    env = {**os.environ, "FONTCONFIG_FILE": str(HERE.parent / "fontconfig.conf")}
    subprocess.run(["rsvg-convert", "-w", "1840", "-o", str(SVG.with_suffix(".png")), str(SVG)], check=True, env=env)
