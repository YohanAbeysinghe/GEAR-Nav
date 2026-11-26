"""One-column qualitative example using recorded real and navigation views."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build as shared

W, H = 1200, 540
WIDTH_MM = 86.36  # 3.4-inch paper column.
MARGIN, GAP = 12, 20
PW = (W-2*MARGIN-GAP)/2
TOP = 59
SIM_CROP_X = (.15, .85)
PH = PW*1080/(1920*(SIM_CROP_X[1]-SIM_CROP_X[0]))
REAL_CROP = (.08, .08+PH/(PW*1920/1080))
STEM = HERE/'gear_realworld_isaacsim_compact'


def main():
    scene = shared.REAL['scenes'][0]
    view, goal = shared.SIM[0], shared.SIM_GOALS[0]
    real = (shared.REAL_DIR/scene['image']).resolve()
    sim = shared.SIM_DIR/view['image']
    assert shared.sha(sim) == view['sha256'] == goal['image_sha256']
    assert view['image'] == goal['image']
    root = ET.Element(f'{{{shared.SVG}}}svg', width=f'{WIDTH_MM}mm',
                      height=f'{WIDTH_MM*H/W}mm', viewBox=f'0 0 {W} {H}')
    shared.element(root, 'title').text = 'Representative real-world and navigation scenes'
    shared.element(root, 'desc').text = (
        'The orange route summarizes a selected real-world GEAR-Nav recording. '
        'The navigation image is an illustrative separate recorded run. '
        'Gold stars mark the target in each view.')
    shared.element(root, 'rect', width=W, height=H, fill='white')
    for i, label in enumerate(['(a) Real world', '(b) Navigation']):
        x = MARGIN+i*(PW+GAP)
        shared.text(root, x+PW/2, 41, label, 37, anchor='middle', bold=True)
    panel = shared.group(root, 'real-world-example')
    shared.photo(panel, real, MARGIN, TOP, PW, PH, crop_y=REAL_CROP)

    def mapping(point):
        return (MARGIN+point[0]*PW,
                TOP+(point[1]-REAL_CROP[0])/(REAL_CROP[1]-REAL_CROP[0])*PH)

    path = next(p for p in scene['paths'] if p['model'] == 'GEAR-Nav')
    for j, segment in enumerate(path['segments']):
        for point in [segment['start']]+[c[k:k+2] for c in segment['curves'] for k in (0, 2, 4)]:
            assert REAL_CROP[0] <= point[1] <= REAL_CROP[1]
        shared.route(panel, segment, mapping, shared.REAL['models']['GEAR-Nav']['color'],
                     True, False, f'gear-nav-recorded-route-{j}')
    shared.star(panel, *mapping(scene['goal']), ident='real-world-goal')
    panel = shared.group(root, 'navigation-example')
    x = MARGIN+PW+GAP
    with Image.open(sim) as source:
        source = source.convert('RGB')
        source = source.crop((round(SIM_CROP_X[0]*source.width), 0,
                              round(SIM_CROP_X[1]*source.width), source.height))
        source.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        source.save(buffer, format='JPEG', quality=95, subsampling=0)
    image = shared.element(panel, 'image', x=x, y=TOP, width=PW, height=PH,
                           preserveAspectRatio='none')
    image.set(f'{{{shared.XLINK}}}href', 'data:image/jpeg;base64,'+
              base64.b64encode(buffer.getvalue()).decode())
    shared.element(panel, 'rect', x=x, y=TOP, width=PW, height=PH,
                   fill='none', stroke='#D3D6DA', stroke_width=1)
    u, v = goal['goal_marker_uv_top_left']
    assert SIM_CROP_X[0] < u < SIM_CROP_X[1]
    shared.star(panel, x+(u-SIM_CROP_X[0])/(SIM_CROP_X[1]-SIM_CROP_X[0])*PW,
                TOP+v*PH, ident='navigation-goal')
    ET.indent(root, space='  ')
    svg = STEM.with_suffix('.svg')
    ET.ElementTree(root).write(svg, encoding='utf-8', xml_declaration=True)
    shared.export_pdf([svg], STEM.with_suffix('.pdf'), WIDTH_MM, WIDTH_MM*H/W)
    env = {**os.environ, 'FONTCONFIG_FILE':str(shared.FIGS/'fontconfig.conf')}
    subprocess.run(['rsvg-convert','-w','1800','-o',str(STEM.with_suffix('.png')),
                    str(svg)],check=True,env=env)
    record = {'size_inches':[3.4, 3.4*H/W],
              'real_world':{'scene':1,'image':str(real.relative_to(shared.ROOT)),
                            'source_sha256':shared.sha(real),'crop_y':REAL_CROP,
                            'path_source':'figs/realworld_paths/annotations.json',
                            'route':'GEAR-Nav only; schematic summary of selected recording',
                            'goal':scene['goal']},
              'navigation':{'scene':1,'image':str(sim.relative_to(shared.ROOT)),
                            'source_sha256':shared.sha(sim),'crop_x':SIM_CROP_X,
                            'goal_marker_uv_top_left':goal['goal_marker_uv_top_left'],
                            'scope':view['role']},
              'notes':'No baseline route overlays or numerical comparisons; all recorded GEAR-Nav route control points remain visible.',
              'output_sha256':{p.name:shared.sha(p) for p in [svg,STEM.with_suffix('.pdf'),STEM.with_suffix('.png')]}}
    (HERE/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'size_inches':record['size_inches'],'real_crop':REAL_CROP,'sim_crop':SIM_CROP_X},indent=2))


if __name__ == '__main__':
    main()
