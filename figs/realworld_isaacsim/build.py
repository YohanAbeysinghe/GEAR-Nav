"""Combine recorded real-world routes and illustrative navigation scene views.

Local-only figure: .venv/bin/python figs/realworld_isaacsim/build.py
No inference, paper edits, Git staging, or remote calls are performed.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent
ROOT = FIGS.parent
sys.path.insert(0, str(FIGS))
from figure_style import GOAL_FILL, SVG_FONT_FAMILY
from svg_diagram import export_pdf

SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
INKSCAPE = 'http://www.inkscape.org/namespaces/inkscape'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)
ET.register_namespace('inkscape', INKSCAPE)
W, H = 2100, 1386
WIDTH_MM = 177.8  # 7 inches, matching the paper's full text width.
MARGIN, GAP = 12, 20
PW = (W-2*MARGIN-2*GAP)/3
RW_TOP = 100
RW_SPAN = .56
RW_HEIGHT = PW*1920/1080*RW_SPAN
SIM_TOP = 953
SIM_HEIGHT = PW*9/16
INK = '#242424'
FONT = SVG_FONT_FAMILY
STEM = 'gear_realworld_isaacsim'
REAL_DIR = FIGS/'realworld_paths'
SIM_DIR = FIGS/'isaacsim_results'
REAL = json.loads((REAL_DIR/'annotations.json').read_text())
SIM = json.loads((SIM_DIR/'evidence.json').read_text())['illustrative_views']
SIM_GOALS = json.loads((SIM_DIR/'space_review/goal_annotations.json').read_text())['views']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f'{{{SVG}}}{tag}',
                         {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text(parent, x, y, value, size=32, *, bold=False, anchor='start', fill=INK):
    node = element(parent, 'text', x=x, y=y, font_size=size,
                   font_family=FONT, font_weight='700' if bold else '400',
                   text_anchor=anchor, fill=fill)
    node.text = value
    return node


def group(parent, name):
    return element(parent, 'g', id=name)


def layer(parent, name, label):
    node = group(parent, name)
    node.set(f'{{{INKSCAPE}}}groupmode', 'layer')
    node.set(f'{{{INKSCAPE}}}label', label)
    return node


def photo(parent, path, x, y, width, height, *, crop_y=None):
    with Image.open(path) as source:
        image = source.convert('RGB')
        if crop_y:
            image = image.crop((0, round(crop_y[0]*image.height), image.width,
                                round(crop_y[1]*image.height)))
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        data = io.BytesIO()
        image.save(data, format='JPEG', quality=95, subsampling=0)
    node = element(parent, 'image', x=x, y=y, width=width, height=height,
                   preserveAspectRatio='none')
    node.set(f'{{{XLINK}}}href', 'data:image/jpeg;base64,'+
             base64.b64encode(data.getvalue()).decode())
    element(parent, 'rect', x=x, y=y, width=width, height=height,
            fill='none', stroke='#D3D6DA', stroke_width=1)


def star(parent, x, y, radius=17.5, ident=None):
    vertices = []
    for i in range(10):
        angle = i*math.pi/5-math.pi/2
        r = radius if i % 2 == 0 else .43*radius
        vertices.append((x+math.cos(angle)*r, y+math.sin(angle)*r))
    points = ' '.join(f'{a:.4f},{b:.4f}' for a, b in vertices)
    node = element(parent, 'polygon', points=points, fill=GOAL_FILL,
                   stroke=INK, stroke_width=2.1, stroke_linejoin='round')
    if ident:
        node.set('id', ident)
    return node


def failure(parent, x, y, color, radius=10.5, ident=None):
    # Editable X polygon with the same dark boundary as the goal stars.
    a = radius*.40
    points = [(-radius, -radius+a), (-radius+a, -radius), (0, -a),
              (radius-a, -radius), (radius, -radius+a), (a, 0),
              (radius, radius-a), (radius-a, radius), (0, a),
              (-radius+a, radius), (-radius, radius-a), (-a, 0)]
    node = element(parent, 'polygon',
                   points=' '.join(f'{x+u:.4f},{y+v:.4f}' for u, v in points),
                   fill=color, stroke=INK, stroke_width=1.8, stroke_linejoin='round')
    if ident:
        node.set('id', ident)
    return node


def route(parent, segment, mapping, color, ours, failed, ident):
    start = mapping(segment['start'])
    commands = [f'M {start[0]:.5f},{start[1]:.5f}']
    for curve in segment['curves']:
        pts = [mapping(curve[k:k+2]) for k in (0, 2, 4)]
        commands.append('C '+' '.join(f'{u:.5f},{v:.5f}' for u, v in pts))
    d = ' '.join(commands)
    width = 7.5 if ours else 5.4
    attrs = dict(d=d, fill='none', stroke_linecap='round', stroke_linejoin='round')
    if segment.get('dashed'):
        attrs['stroke_dasharray'] = '13 11'
    element(parent, 'path', **attrs, stroke='white', stroke_width=width+3,
            stroke_opacity=.88)
    node = element(parent, 'path', **attrs, stroke=color, stroke_width=width)
    node.set('id', ident)
    if segment.get('arrow', True) and not failed:
        curve = segment['curves'][-1]
        tip, control = mapping(curve[4:6]), mapping(curve[2:4])
        dx, dy = tip[0]-control[0], tip[1]-control[1]
        length = math.hypot(dx, dy)
        dx, dy = dx/length, dy/length
        tail = (tip[0]-dx*17, tip[1]-dy*17)
        points = [tip, (tail[0]-dy*7.2, tail[1]+dx*7.2),
                  (tail[0]+dy*7.2, tail[1]-dx*7.2)]
        element(parent, 'polygon', points=' '.join(f'{u:.4f},{v:.4f}' for u, v in points),
                fill=color)


def header(parent, y, label):
    element(parent, 'rect', x=MARGIN, y=y, width=W-2*MARGIN, height=48,
            rx=3, fill='#F4F5F7')
    element(parent, 'rect', x=MARGIN, y=y, width=5, height=48,
            fill=REAL['models']['GEAR-Nav']['color'])
    text(parent, 31, y+34, label, 36, bold=True)


def legend(parent):
    node = layer(parent, 'shared-legend', 'Methods and markers')
    element(node, 'rect', x=34, y=797, width=369, height=49,
            rx=6, fill='#FFF1D9')
    entries = [('GEAR-Nav', 59, 'GEAR-Nav (ours)'),
               ('OmniVLA', 453, 'OmniVLA'),
               ('TIC-VLA', 803, 'TIC-VLA'),
               ('NaVILA', 1135, 'NaVILA')]
    for model, x, label in entries:
        element(node, 'path', d=f'M {x},822 H {x+48}', fill='none',
                stroke=REAL['models'][model]['color'],
                stroke_width=7.5 if model == 'GEAR-Nav' else 5.4)
        text(node, x+64, 833, label, 32, bold=model == 'GEAR-Nav')
    star(node, 1538, 821, 14)
    text(node, 1564, 833, 'Goal', 32)
    failure(node, 1783, 821, '#888888', 10)
    text(node, 1808, 833, 'Failure', 32)


def build():
    protected = [ROOT/'GEAR-Nav Overleaf/main.tex',
                 ROOT/'GEAR-Nav Overleaf/sections/supplementary.tex',
                 ROOT/'GEAR-Nav Overleaf/fig/gear_realworld.pdf',
                 REAL_DIR/'annotations.json', REAL_DIR/'realworld_paths_column.svg',
                 REAL_DIR/'realworld_paths_column.pdf',
                 SIM_DIR/'space_review/compact_proposal.pdf']
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    source_paths = [REAL_DIR/'annotations.json', REAL_DIR/'reference_priors.json',
                    SIM_DIR/'evidence.json', SIM_DIR/'space_review/goal_annotations.json']
    root = ET.Element(f'{{{SVG}}}svg', width=f'{WIDTH_MM}mm',
                      height=f'{WIDTH_MM*H/W}mm', viewBox=f'0 0 {W} {H}')
    element(root, 'title').text = 'GEAR-Nav real-world and navigation qualitative scenes'
    element(root, 'desc').text = (
        'Real-world GEAR-Nav routes summarized from recordings, with schematic '
        'baseline paths adapted from VEGA. The navigation row contains illustrative '
        'recordings with manually marked target people. This figure contains no '
        'evaluation metrics and does not associate the illustrative runs with '
        'the aggregate evaluation table.')
    element(root, 'rect', width=W, height=H, fill='white')
    real_layer = layer(root, 'real-world', 'A — Real-world navigation')
    header(real_layer, 0, '(a) Real-world navigation')
    scene_records = []
    for i, scene in enumerate(REAL['scenes']):
        x = MARGIN+i*(PW+GAP)
        crop = [scene['crop_y'][0], scene['crop_y'][0]+RW_SPAN]
        bounds = [x, RW_TOP, PW, RW_HEIGHT]
        text(real_layer, x+PW/2, 82,
             f"Scenario {scene['scene']} · {scene['goal_label']}", 32, anchor='middle')
        pane = group(real_layer, f"real-scene-{scene['scene']}")
        image_path = (REAL_DIR/scene['image']).resolve()
        source_paths.append(image_path)
        photo(pane, image_path, *bounds, crop_y=crop)

        def mapping(point):
            return (x+point[0]*PW, RW_TOP+(point[1]-crop[0])/RW_SPAN*RW_HEIGHT)

        ordered = [p for p in scene['paths'] if p['model'] != 'GEAR-Nav'] + [
            p for p in scene['paths'] if p['model'] == 'GEAR-Nav']
        for path in ordered:
            name = path['model']
            color = REAL['models'][name]['color']
            failed = path.get('termination', {}).get('type') in {'failure', 'collision'}
            for j, segment in enumerate(path['segments']):
                # The crop preserves every original control point and goal.
                for point in [segment['start']]+[c[k:k+2] for c in segment['curves'] for k in (0, 2, 4)]:
                    assert crop[0] <= point[1] <= crop[1], (i, name, point)
                route(pane, segment, mapping, color, name == 'GEAR-Nav', failed,
                      f'real-{i+1}-{name}-segment-{j}')
            if failed:
                endpoint = path['segments'][-1]['curves'][-1][4:6]
                failure(pane, *mapping(endpoint), color,
                        ident=f'real-{i+1}-{name}-failure')
        star(pane, *mapping(scene['goal']), ident=f'real-{i+1}-goal')
        scene_records.append({'scenario': i+1, 'source': str(image_path.relative_to(ROOT)),
                              'original_crop_y': scene['crop_y'], 'combined_crop_y': crop,
                              'all_original_path_control_points_visible': True,
                              'goal': scene['goal'], 'bounds_svg': bounds})
    legend(root)
    sim_layer = layer(root, 'isaac-sim', 'B — Navigation environments')
    header(sim_layer, 876, '(b) Navigation environments')
    for i, (view, goal) in enumerate(zip(SIM, SIM_GOALS)):
        x = MARGIN+i*(PW+GAP)
        assert view['image'] == goal['image']
        image_path = SIM_DIR/view['image']
        assert sha(image_path) == goal['image_sha256'] == view['sha256']
        source_paths.append(image_path)
        pane = group(sim_layer, f'sim-scene-{i+1}')
        photo(pane, image_path, x, SIM_TOP, PW, SIM_HEIGHT)
        u, v = goal['goal_marker_uv_top_left']
        star(pane, x+u*PW, SIM_TOP+v*SIM_HEIGHT, ident=f'sim-{i+1}-goal')
        text(sim_layer, x+PW/2, 1370, view['name'], 32, anchor='middle')
    ET.indent(root, space='  ')
    svg = HERE/f'{STEM}.svg'
    ET.ElementTree(root).write(svg, encoding='utf-8', xml_declaration=True)
    env = {**os.environ, 'FONTCONFIG_FILE': str(FIGS/'fontconfig.conf')}
    export_pdf([svg], svg.with_suffix('.pdf'), WIDTH_MM, WIDTH_MM*H/W)
    subprocess.run(['rsvg-convert', '-w', '2520', '-o', str(svg.with_suffix('.png')),
                    str(svg)], check=True, env=env)
    # Import copy changes only canvas units and resolves the Figma font name.
    root.set('width', f'{W}px')
    root.set('height', f'{H}px')
    for node in root.iter(f'{{{SVG}}}text'):
        node.set('font-family', 'STIX Two Text')
    ET.ElementTree(root).write(HERE/'figma_import.svg', encoding='utf-8', xml_declaration=True)
    for p in protected:
        assert sha(p) == before[str(p.relative_to(ROOT))], p
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    record = {
        'title': 'GEAR-Nav real-world and navigation qualitative scenes',
        'size_svg': [W, H], 'size_inches': [7, 7*H/W],
        'target_figma_file': '3RjwsUydxXrFOknU4HhcTy',
        'figma_update': 'Cloud delivery is recorded separately in figma_sync/delivery.json; a local rebuild does not update Figma.',
        'git_tracking': 'Local-only assets under ignored /figs/.',
        'paper_unchanged': True, 'protected_sha256': before,
        'source_sha256': source_hashes, 'realworld_panels': scene_records,
        'photographs': 6, 'goal_stars_in_panels': 6,
        'realworld_model_routes': 12, 'realworld_failure_markers': 9,
        'route_coordinates': 'All source control points are preserved exactly; only the display crop changes.',
        'realworld_baselines': REAL['interpretation'],
        'navigation_scope': 'Illustrative separate recordings; no trajectory or linkage to aggregate metrics is inferred.',
        'minimum_text_size_at_7_inches_pt': 32/W*7*72,
        'evaluation_numbers': 0,
        'output_sha256': {p.name: sha(p) for p in [svg, svg.with_suffix('.pdf'),
                            svg.with_suffix('.png'), HERE/'figma_import.svg']},
    }
    (HERE/'provenance.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: record[k] for k in ['size_inches', 'photographs',
                     'goal_stars_in_panels', 'paper_unchanged', 'figma_update']}, indent=2))


if __name__ == '__main__':
    build()
