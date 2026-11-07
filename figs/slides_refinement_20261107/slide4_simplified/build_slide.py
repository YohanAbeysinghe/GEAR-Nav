"""Build slide 4's simple aggregation loop locally; never send remote writes.

This mutation plan targets the verified pre-edit slide. Read the live slide
before any remote replay. Reuses established geometry and native text helpers.
"""
from pathlib import Path
from types import SimpleNamespace
import ast
import base64
import html
import json
import math
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent.parent
PAGE = 'gear_video_04'
INK = '#202124'
SERIF = 'Times New Roman'
ORANGE = '#E77722'
GOLD = '#FFC52F'
MUTED = '#C5C9CE'
NATIVE = {oid: {'size': {'width': {'magnitude': 3000000, 'unit': 'EMU'},
                        'height': {'magnitude': 3000000, 'unit': 'EMU'}}}
          for oid in ['gr_20261107_header_04', 'gv_0078',
                      'gr_20261107_num_04', 'gv_0136']}

sources = [
    (FIGS/'slides_polish_20261103/polish_deck.py',
     {'rgb', 'base_size', 'geometry', 'mutate', 'preview'}),
    (HERE.parent/'slide3_simplified/build_slide.py',
     {'add', 'text', 'rect', 'line', 'dot', 'star', 'path'}),
]
for source, names in sources:
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), globals())

elements = []
rect('gr_20261107_header_04', 0, 0, 720, 54, '#505050')
text('gv_0078', 24, 8, 670, 40, 'Energy-based dataset aggregation',
     28, '#F5F5F5', True, 'START')
text('gs4_20261107_subtitle', 24, 68, 672, 30,
     'Train on the paths the model actually visits.', 16, '#F5F5F5', align='START')

cards = [
    ('Generate paths', 'With the current\nGEAR model', '#E6EFFD'),
    ('Get corrections', 'Energy-based\nlocal corrections', '#FFF0CC'),
    ('Aggregate data', 'Keep examples\nfrom every round', '#EAE2EE'),
    ('Retrain GEAR', 'Learn from the\ncombined dataset', '#FADDDC'),
]
for i, (title, caption, fill) in enumerate(cards):
    x = 24 + 174*i
    p = f'gs4_20261107_{i+1}'
    rect(p+'_card', x, 131, 150, 164, fill)
    if i == 2:
        rect(p+'_accent', x, 131, 150, 4, '#A587B2')
    text(p+'_title', x+3, 145, 144, 28, title, 16, bold=True)
    text(p+'_caption', x+5, 248, 140, 40, caption, 14)
    if i == 0:
        path(p+'_path', [(x+25,224),(x+47,217),(x+70,201),(x+95,194)],
             waypoints=True)
        star(p+'_goal', x+123,187)
    elif i == 1:
        pts=[(x+24,224),(x+54,217),(x+84,214),(x+117,204)]
        path(p+'_path', pts, '#969CA2', 2)
        for j, (xx,yy) in enumerate(pts[1:]):
            line(f'{p}_correction_{j}', (xx,yy), (xx+5,yy-24), ORANGE, 2, True)
            dot(f'{p}_point_{j}', xx,yy, 2.8)
    elif i == 2:
        # Retained examples plus the current round, not a replacement dataset.
        rect(p+'_old_back', x+16, 192, 47, 30, '#D8CBE1', '#A587B2')
        rect(p+'_old_front', x+20, 198, 47, 30, '#FFFFFF', '#A587B2')
        text(p+'_old_label', x+20, 199, 47, 27, 'Old', 14)
        text(p+'_plus', x+67, 197, 22, 28, '+', 19, '#755786', True)
        rect(p+'_new', x+92, 198, 42, 30, '#FFE09A', '#A87518')
        text(p+'_new_label', x+92, 199, 42, 27, 'New', 14)
    else:
        rect(p+'_model', x+36, 193, 78, 36, '#FFFFFF', '#C1706C')
        text(p+'_model_label', x+36, 197, 78, 28, 'GEAR', 17, bold=True)

for i in range(3):
    line(f'gs4_20261107_flow_{i}', (179+174*i,212), (192+174*i,212), MUTED, 1.8, True)
line('gs4_20261107_loop_down', (621,301), (621,337), MUTED, 1.8)
line('gs4_20261107_loop_left', (621,337), (99,337), MUTED, 1.8)
line('gs4_20261107_loop_up', (99,337), (99,301), MUTED, 1.8, True)
text('gs4_20261107_repeat', 154, 305, 412, 28,
     'Repeat with the updated model', 16, '#F08A45')
text('gv_0136', 24, 382, 650, 18,
     'Aggregate path–correction pairs; train on all collected rounds.', 10, MUTED, align='START')
text('gr_20261107_num_04', 670, 386, 40, 18, '4', 9, MUTED, align='END')

notes = '''SIMPLIFIED SLIDE / 2026-11-07
Energy-based dataset aggregation

NARRATION
The current model visits new candidate paths. We query energy-based local corrections at those paths and add the examples to the existing dataset. GEAR learns from all collected rounds, and the updated model generates the next paths. The key is to keep earlier examples while adding supervision where the model now goes.

SOURCES AND SCOPE
GEAR-Nav Overleaf/main.tex, Energy-Based Dataset Aggregation. Each example retains the observation, goal, current candidate trajectory, and oracle correction. The first round starts from the structured prior; the diagram depicts the recurring loop after initialization. During training, learned updates use kinematic projection and an energy guard. These details are retained here in notes to keep the slide focused on aggregation. The energy oracle and guard are training-only. All visual paths are conceptual, not measured rollouts. No benchmark or convergence claim is added.

DESIGN
The complex pipeline image was replaced by four native editable cards and one return arrow. Old + New makes retention explicit. The diagram uses the same pale scientific palette and dark slide theme as the adjacent slides.
'''
requests = [{'deleteObject': {'objectId': 'gp_04_002'}}]
for e in elements:
    requests.extend(mutate(e))
    if e['kind'] == 'text':
        requests.append({'updateParagraphStyle': {'objectId': e['id'], 'textRange': {'type': 'ALL'},
            'style': {'indentStart': {'magnitude': 0, 'unit': 'PT'},
                      'indentEnd': {'magnitude': 0, 'unit': 'PT'},
                      'indentFirstLine': {'magnitude': 0, 'unit': 'PT'}},
            'fields': 'indentStart,indentEnd,indentFirstLine'}})
requests.extend([
    {'deleteText': {'objectId': 'SLIDES_API1052417964_5', 'textRange': {'type': 'ALL'}}},
    {'insertText': {'objectId': 'SLIDES_API1052417964_5', 'text': notes, 'insertionIndex': 0}},
])
canvas = dict(id=PAGE, n=4, bg='#191919', elements=elements)
for filename, value in [('requests.json', requests), ('canvas.json', canvas)]:
    (HERE/filename).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
(HERE/'speaker-notes.txt').write_text(notes)
preview(SimpleNamespace(**canvas))

# Match local SVG marker colors to native line colors.
svg_path = HERE/'proof/slide-04.svg'
ns = 'http://www.w3.org/2000/svg'
ET.register_namespace('', ns)
root = ET.parse(svg_path).getroot()
defs = root.find(f'{{{ns}}}defs')
for color in [ORANGE, MUTED]:
    marker_id = 'arrow_'+color[1:]
    marker = ET.SubElement(defs, f'{{{ns}}}marker', dict(id=marker_id,
        markerWidth='6', markerHeight='6', refX='5', refY='3', orient='auto'))
    ET.SubElement(marker, f'{{{ns}}}path', d='M0 0 L6 3 L0 6 Z', fill=color)
    for element in root.findall(f'{{{ns}}}line'):
        if element.get('marker-end') and element.get('stroke') == color:
            element.set('marker-end', f'url(#{marker_id})')
ET.ElementTree(root).write(svg_path, encoding='unicode')
subprocess.run(['rsvg-convert', '-o', str(HERE/'proof/slide-04.png'), str(svg_path)], check=True)
print(json.dumps({'slide': PAGE, 'elements': len(elements), 'requests': len(requests)}))
