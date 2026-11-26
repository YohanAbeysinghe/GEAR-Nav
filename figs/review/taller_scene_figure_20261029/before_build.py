"""Six-scene figure with typography sized for the paper's 3.4-inch column.

Only local SVG/PDF/PNG assets are written; paper placement is separate.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build as shared

W = 1200
WIDTH_MM = 86.36
MARGIN, GAP = 8, 16
PW = (W-2*MARGIN-2*GAP)/3
REAL_Y = 90
REAL_CROPS = [(0.08, 0.58), (0.12, 0.62), (0.24, 0.74)]
REAL_H = PW*1920/1080*.50
LEGEND_Y = REAL_Y+REAL_H+30
SIM_HEADER_Y = REAL_Y+REAL_H+77
SIM_Y = SIM_HEADER_Y+56
SIM_H = PW*9/16
SIM_LABEL_Y = SIM_Y+SIM_H+38
H = math.ceil(SIM_LABEL_Y+14)
STEM = HERE/'gear_realworld_isaacsim'
INK = shared.INK


def title(parent, y, label):
    shared.element(parent, 'rect', x=MARGIN, y=y, width=W-2*MARGIN,
                   height=42, fill='#F4F5F7')
    shared.element(parent, 'rect', x=MARGIN, y=y, width=4, height=42,
                   fill=shared.REAL['models']['GEAR-Nav']['color'])
    shared.text(parent, 24, y+31, label, 37, bold=True)


def star(parent, x, y, ident):
    node = shared.star(parent, x, y, 15, ident=ident)
    node.set('stroke-width', '1.65')


def draw_route(parent, segment, mapping, color, ours, failed, ident):
    pts = [mapping(segment['start'])]
    commands = [f'M {pts[0][0]:.5f},{pts[0][1]:.5f}']
    for curve in segment['curves']:
        mapped = [mapping(curve[k:k+2]) for k in (0, 2, 4)]
        commands.append('C '+' '.join(f'{x:.5f},{y:.5f}' for x, y in mapped))
    attrs = dict(d=' '.join(commands), fill='none', stroke_linecap='round',
                 stroke_linejoin='round')
    if segment.get('dashed'):
        attrs['stroke_dasharray'] = '10 8'
    width = 6.4 if ours else 4.6
    shared.element(parent, 'path', **attrs, stroke='white',
                   stroke_width=width+2.3, stroke_opacity=.9)
    node = shared.element(parent, 'path', **attrs, stroke=color, stroke_width=width)
    node.set('id', ident)
    if segment.get('arrow', True) and not failed:
        curve = segment['curves'][-1]
        tip, control = mapping(curve[4:6]), mapping(curve[2:4])
        dx, dy = tip[0]-control[0], tip[1]-control[1]
        length = math.hypot(dx, dy)
        dx, dy = dx/length, dy/length
        tail = (tip[0]-dx*12, tip[1]-dy*12)
        arrow = [tip, (tail[0]-dy*5.3, tail[1]+dx*5.3),
                 (tail[0]+dy*5.3, tail[1]-dx*5.3)]
        shared.element(parent, 'polygon',
                       points=' '.join(f'{x:.4f},{y:.4f}' for x, y in arrow), fill=color)


def legend(parent):
    node = shared.layer(parent, 'method-key', 'Method legend')
    shared.element(node, 'rect', x=6, y=LEGEND_Y-19, width=285,
                   height=42, rx=4, fill='#FFF1D9')
    for i, name in enumerate(shared.REAL['models']):
        x = 18+i*300
        shared.element(node, 'path', d=f'M {x},{LEGEND_Y+3} h 34',
                       fill='none', stroke=shared.REAL['models'][name]['color'],
                       stroke_width=6.4 if name == 'GEAR-Nav' else 4.6)
        shared.text(node, x+46, LEGEND_Y+14, name, 35, bold=name == 'GEAR-Nav')


def build():
    protected = [shared.REAL_DIR/'annotations.json', shared.REAL_DIR/'reference_priors.json',
                 shared.HERE/'gear_realworld_isaacsim.pdf',
                 shared.SIM_DIR/'evidence.json',
                 shared.SIM_DIR/'space_review/goal_annotations.json']
    source_hashes = {str(p.relative_to(shared.ROOT)):shared.sha(p) for p in protected}
    root = ET.Element(f'{{{shared.SVG}}}svg', width=f'{WIDTH_MM}mm',
                      height=f'{WIDTH_MM*H/W}mm', viewBox=f'0 0 {W} {H}')
    shared.element(root, 'title').text = 'GEAR-Nav real-world and Isaac Sim scenes'
    shared.element(root, 'desc').text = (
        'All six existing scene views, with unchanged recorded GEAR-Nav route '
        'control points, schematic reference baseline paths, and target markers. '
        'Typography and line weights are sized for a 3.4-inch paper column. '
        'The simulation views come from separate illustrative oracle-goal runs.')
    shared.element(root, 'rect', width=W, height=H, fill='white')
    real = shared.layer(root, 'real-world', 'A — Real-world routes')
    title(real, 0, '(a) Real world')
    scene_records = []
    route_count = failure_count = 0
    for i, scene in enumerate(shared.REAL['scenes']):
        x = MARGIN+i*(PW+GAP)
        crop = REAL_CROPS[i]
        shared.text(real, x+PW/2, 76,
                    f"{scene['scene']} · {scene['goal_label']}", 35, anchor='middle')
        pane = shared.group(real, f'real-scene-{i+1}')
        image = (shared.REAL_DIR/scene['image']).resolve()
        source_hashes[str(image.relative_to(shared.ROOT))] = shared.sha(image)
        shared.photo(pane, image, x, REAL_Y, PW, REAL_H, crop_y=crop)

        def mapping(point):
            return (x+point[0]*PW, REAL_Y+(point[1]-crop[0])/(crop[1]-crop[0])*REAL_H)

        ordered = [p for p in scene['paths'] if p['model'] != 'GEAR-Nav'] + [
            p for p in scene['paths'] if p['model'] == 'GEAR-Nav']
        for path in ordered:
            name = path['model']
            color = shared.REAL['models'][name]['color']
            failed = path.get('termination', {}).get('type') in {'failure','collision'}
            for j, segment in enumerate(path['segments']):
                points = [segment['start']]+[c[k:k+2] for c in segment['curves'] for k in (0, 2, 4)]
                assert all(0 <= p[0] <= 1 and crop[0] <= p[1] <= crop[1] for p in points), (i, name)
                draw_route(pane, segment, mapping, color, name == 'GEAR-Nav', failed,
                           f'real-{i+1}-{name}-segment-{j}')
                route_count += 1
            if failed:
                endpoint = path['segments'][-1]['curves'][-1][4:6]
                node = shared.failure(pane, *mapping(endpoint), color, radius=10,
                                      ident=f'real-{i+1}-{name}-failure')
                node.set('stroke-width', '1.5')
                failure_count += 1
        assert crop[0] <= scene['goal'][1] <= crop[1]
        star(pane, *mapping(scene['goal']), ident=f'real-{i+1}-goal')
        scene_records.append({'scene':i+1,'crop_y':crop,'original_goal':scene['goal'],
                              'all_source_control_points_visible':True})
    legend(root)
    sim = shared.layer(root, 'navigation', 'B — Isaac Sim scene views')
    title(sim, SIM_HEADER_Y, '(b) Isaac Sim')
    for i, (view, goal) in enumerate(zip(shared.SIM, shared.SIM_GOALS)):
        x = MARGIN+i*(PW+GAP)
        image = shared.SIM_DIR/view['image']
        assert view['image'] == goal['image']
        assert shared.sha(image) == goal['image_sha256'] == view['sha256']
        source_hashes[str(image.relative_to(shared.ROOT))] = shared.sha(image)
        pane = shared.group(sim, f'sim-scene-{i+1}')
        shared.photo(pane, image, x, SIM_Y, PW, SIM_H)
        u, v = goal['goal_marker_uv_top_left']
        star(pane, x+u*PW, SIM_Y+v*SIM_H, ident=f'sim-{i+1}-goal')
        shared.text(sim, x+PW/2, SIM_LABEL_Y, view['name'], 35, anchor='middle')
    assert route_count == 12 and failure_count == 9
    texts = list(root.iter(f'{{{shared.SVG}}}text'))
    assert len(texts) == 12
    minimum_pt = min(float(t.get('font-size')) for t in texts)/W*3.4*72
    assert minimum_pt >= 7
    svg = STEM.with_suffix('.svg')
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(svg, encoding='utf-8', xml_declaration=True)
    shared.export_pdf([svg], STEM.with_suffix('.pdf'), WIDTH_MM, WIDTH_MM*H/W)
    subprocess.run(['rsvg-convert','-w','1800','-o',str(STEM.with_suffix('.png')),
                    str(svg)],check=True,
                   env={**os.environ,'FONTCONFIG_FILE':str(shared.FIGS/'fontconfig.conf')})
    for path, digest in source_hashes.items():
        assert shared.sha(shared.ROOT/path) == digest,path
    record = {'size_inches':[3.4,3.4*H/W],'size_svg':[W,H],
              'minimum_type_size_pt':minimum_pt,'photo_count':6,
              'panel_goal_markers':6,'realworld_route_segments':route_count,
              'reference_failure_markers':failure_count,
              'realworld_crops':scene_records,'all_path_control_points_preserved':True,
              'source_sha256':source_hashes,
              'scope':shared.REAL['interpretation'],
              'simulation_scope':'Separate illustrative oracle-goal runs, not matched to aggregate evaluation metrics.',
              'output_sha256':{p.name:shared.sha(p) for p in [svg,STEM.with_suffix('.pdf'),STEM.with_suffix('.png')]}}
    (HERE/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['size_inches','minimum_type_size_pt','photo_count','realworld_route_segments']},indent=2))


if __name__ == '__main__':
    build()
