"""Simplify slide 3 to five editable energy cards; emit requests, never send them.

Run from any directory with the repository's .venv/bin/python. This plan targets
the verified pre-edit slide; read the live slide before any remote replay.
"""
from pathlib import Path
from types import SimpleNamespace
import ast
import base64
import html
import json
import math
import subprocess

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent.parent
PAGE = 'gear_video_03'
INK = '#202124'
SERIF = 'Times New Roman'
ORANGE = '#E77722'
GOLD = '#FFC52F'
MUTED = '#C5C9CE'
RED = '#B66161'
NATIVE = {oid: {'size': {'width': {'magnitude': 3000000, 'unit': 'EMU'},
                        'height': {'magnitude': 3000000, 'unit': 'EMU'}}}
          for oid in ['gr_20261107_header_03', 'gv_0020',
                      'gr_20261107_num_03', 'gv_0057', 'gv_0120_energy']}

source = FIGS/'slides_polish_20261103/polish_deck.py'
for node in ast.parse(source.read_text()).body:
    if isinstance(node, ast.FunctionDef) and node.name in {'rgb', 'base_size', 'geometry', 'mutate', 'preview'}:
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), globals())

elements = []

def add(oid, kind, **props):
    e = dict(id=oid, page=PAGE, kind=kind, **props)
    elements.append(e)
    return e

def text(oid, x, y, w, h, value, size=14, color=INK, bold=False, align='CENTER'):
    return add(oid, 'text', x=x, y=y, w=w, h=h, text=value, size=size,
               color=color, bold=bold, font='Arial', align=align)

def rect(oid, x, y, w, h, fill, stroke=None):
    return add(oid, 'rect', x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, r=0)

def line(oid, a, b, color=ORANGE, width=2.5, arrow=False, dash=False):
    return add(oid, 'line', x1=a[0], y1=a[1], x2=b[0], y2=b[1],
               color=color, width=width, arrow=arrow, dash=dash)

def dot(oid, x, y, r=3, fill=GOLD, stroke=ORANGE):
    return add(oid, 'ellipse', x=x-r, y=y-r, w=r*2, h=r*2, fill=fill, stroke=stroke)

def star(oid, x, y):
    return add(oid, 'star', x=x-7, y=y-7, w=14, h=14, fill=GOLD, stroke='#A87518')

def path(prefix, pts, color=ORANGE, width=2.5, dash=False, waypoints=False):
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        line(f'{prefix}_seg_{i}', a, b, color, width, dash=dash)
    if waypoints:
        for i, (x,y) in enumerate(pts):
            dot(f'{prefix}_wp_{i}', x, y)

rect('gr_20261107_header_03', 0, 0, 720, 54, '#505050')
text('gv_0020', 24, 8, 670, 40, 'Five energy terms for supervision', 28, '#F5F5F5', True, 'START')
text('gv_0057', 24, 68, 672, 30,
     'Geometric cues for safe, goal-directed, smooth trajectories.', 16, '#F5F5F5', align='START')

terms = [
    ('Footprint\nclearance', 'Keep the robot\nclear of obstacles.'),
    ('Goal\nprogress', 'Move toward\nthe goal.'),
    ('Retreat\npenalty', 'Discourage steps\naway from goal.'),
    ('Early\nheading', 'Start in the\ngoal direction.'),
    ('Path\nsmoothness', 'Avoid abrupt\nturns.'),
]
for i, (title, caption) in enumerate(terms):
    x = 26 + i*136
    p = f'gs3_20261107_{i+1}'
    rect(p+'_card', x, 118, 124, 232, '#FFF0CC')
    text(p+'_title', x+4, 136, 116, 46, title, 17, bold=True)
    text(p+'_caption', x+2, 292, 120, 46, caption, 13)
    if i == 0:
        # Obstacle, robot footprint, and the free gap between them.
        rect(p+'_obstacle', x+17, 213, 20, 49, '#92989D')
        dot(p+'_robot', x+91, 237, 14, '#FFFFFF', ORANGE)
        line(p+'_clearance', (x+44,237), (x+71,237), INK, 1.3, True)
        line(p+'_clearance_reverse', (x+71,237), (x+44,237), INK, 1.3, True)
    elif i == 1:
        pts=[(x+19,259), (x+38,249), (x+57,234), (x+76,223)]
        path(p, pts, waypoints=True)
        line(p+'_toward', pts[-1], (x+89,215), arrow=True, width=2)
        star(p+'_goal', x+101, 209)
    elif i == 2:
        line(p+'_incoming', (x+17,259), (x+60,244))
        line(p+'_forward', (x+60,244), (x+93,220), arrow=True, width=2)
        line(p+'_retreat', (x+60,244), (x+39,220), RED, 2, True)
        line(p+'_cross_a', (x+37,204), (x+47,214), RED, 1.8)
        line(p+'_cross_b', (x+47,204), (x+37,214), RED, 1.8)
        dot(p+'_point', x+60,244)
        star(p+'_goal', x+103,209)
    elif i == 3:
        line(p+'_reference', (x+25,257), (x+86,257), '#A3A5A7', 1.4, dash=True)
        line(p+'_toward', (x+25,257), (x+64,231), width=3, arrow=True)
        line(p+'_goal_direction', (x+70,227), (x+92,213), '#A3A5A7', 1.2, dash=True)
        dot(p+'_start', x+25,257, 4, '#FFFFFF', INK)
        star(p+'_goal', x+103,207)
    else:
        # Contrasting a jagged and smooth path is a conceptual illustration.
        path(p+'_jagged', [(x+17,256),(x+38,216),(x+56,249),(x+76,213),(x+106,238)],
             '#A3A5A7', 1.5, True)
        pts=[(x+17,256),(x+27,246),(x+37,239),(x+48,234),
             (x+59,231),(x+71,230),(x+83,231),(x+95,234),(x+106,238)]
        path(p+'_smooth', pts, width=3)
        for j in [0,3,6,8]:
            dot(f'{p}_smooth_wp_{j}', *pts[j], r=2.7)

text('gv_0120_energy', 24, 382, 650, 18,
     'Geometric supervision is used during training.', 10, MUTED, align='START')
text('gr_20261107_num_03', 670, 386, 40, 18, '3', 9, MUTED, align='END')

notes = '''SIMPLIFIED SLIDE / 2026-11-07
Five energy terms for supervision

NARRATION
We use five energy terms to supervise refinement: footprint clearance, goal progress, retreat penalty, early heading, and path smoothness.

SOURCES AND SCOPE
The five names follow the current pipeline figure in figs/pipeline/build_diagram.py. The geometric energy is described in GEAR-Nav Overleaf/main.tex. These editable illustrations explain the terms; they are schematic, not measured robot trajectories. This slide describes the formulation and does not imply every term has a nonzero weight in every run. Geometry supplies supervision during training; it is not an inference input.

EDIT CUE
Show all five cards together. Historical video timing: 00:20–00:28.
'''
requests = [{'deleteObject': {'objectId': 'gp_03_002'}}]
for e in elements:
    requests.extend(mutate(e))
    if e['kind'] == 'text':
        requests.append({'updateParagraphStyle': {'objectId': e['id'], 'textRange': {'type': 'ALL'},
            'style': {'indentStart': {'magnitude': 0, 'unit': 'PT'},
                      'indentEnd': {'magnitude': 0, 'unit': 'PT'},
                      'indentFirstLine': {'magnitude': 0, 'unit': 'PT'}},
            'fields': 'indentStart,indentEnd,indentFirstLine'}})
requests.extend([
    {'deleteText': {'objectId': 'SLIDES_API1052417964_3', 'textRange': {'type': 'ALL'}}},
    {'insertText': {'objectId': 'SLIDES_API1052417964_3', 'text': notes, 'insertionIndex': 0}},
])
canvas = dict(id=PAGE, n=3, bg='#191919', elements=elements)
for filename, value in [('requests.json', requests), ('canvas.json', canvas)]:
    (HERE/filename).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
(HERE/'speaker-notes.txt').write_text(notes)
preview(SimpleNamespace(**canvas))
# Give each local SVG arrow the same color as its native Slides line.
svg_path = HERE/'proof/slide-03.svg'
svg = svg_path.read_text()
for color in [ORANGE, RED]:
    marker = 'arrow_'+color[1:]
    svg = svg.replace('</defs>', f'<marker id="{marker}" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="{color}"/></marker></defs>')
    svg = svg.replace(f'stroke="{color}" stroke-width="2" marker-end="url(#a)"', f'stroke="{color}" stroke-width="2" marker-end="url(#{marker})"')
    svg = svg.replace(f'stroke="{color}" stroke-width="3" marker-end="url(#a)"', f'stroke="{color}" stroke-width="3" marker-end="url(#{marker})"')
svg_path.write_text(svg)
subprocess.run(['rsvg-convert', '-o', str(HERE/'proof/slide-03.png'), str(svg_path)], check=True)
print(json.dumps({'slide': PAGE, 'elements': len(elements), 'requests': len(requests)}))
