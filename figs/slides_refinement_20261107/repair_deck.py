"""Consolidated corrections from first native PDF review; no remote writes."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'raw-output.json').read_text())['structuredContent']
actual={e['objectId']:e for s in raw['slides'] for e in s['pageElements']}
canvas=json.loads((HERE/'canvas.json').read_text())
desired={e['id']:e for s in canvas for e in s['elements']}
initial=json.loads((HERE/'requests.json').read_text())
req=[]

def transform(oid):
    e=desired[oid];a=actual[oid]
    dims=[a['size'][k]['magnitude']/(12700 if a['size'][k]['unit']=='EMU' else 1) for k in ['width','height']]
    return {'updatePageElementTransform':{'objectId':oid,'applyMode':'ABSOLUTE','transform':{'scaleX':e['w']/dims[0],'scaleY':e['h']/dims[1],'shearX':0,'shearY':0,'translateX':e['x'],'translateY':e['y'],'unit':'PT'}}}

# Replacement changed intrinsic image sizes: derive scale from actual readback.
for oid in ['gp_03_002','gp_04_002','gv_0173']:
    req.append(transform(oid))

# Remove inherited list formatting from the rewritten prose box.
req.extend([
 {'deleteParagraphBullets':{'objectId':'gv_0013','textRange':{'type':'ALL'}}},
 {'updateParagraphStyle':{'objectId':'gv_0013','textRange':{'type':'ALL'},'style':{'indentStart':{'magnitude':0,'unit':'PT'},'indentEnd':{'magnitude':0,'unit':'PT'},'indentFirstLine':{'magnitude':0,'unit':'PT'}},'fields':'indentStart,indentEnd,indentFirstLine'}},
 {'updateTextStyle':{'objectId':'gv_0145','textRange':{'type':'ALL'},'style':{'fontSize':{'magnitude':16,'unit':'PT'}},'fields':'fontSize'}}
])
for oid in desired:
    if oid.startswith('gr_20261107_num_'):req.append(transform(oid))

# Apply only the newly confirmed four-method comparison changes on slide 8.
changed={'gv_0374','gv_0380','gv_0376','gv_0377','gv_0378','gv_0379','gr_20261107_navila_label','gr_20261107_navila_video','gr_20261107_tic_label','gr_20261107_tic_video'}
for oid in ['gv_0373','gv_0375']:req.append({'deleteObject':{'objectId':oid}})
for r in initial:
    data=next(iter(r.values()));oid=data.get('objectId')
    if oid in changed and 'deleteObject' not in r:req.append(r)
note_id=raw['slides'][7]['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
for r in initial:
    if next(iter(r.values())).get('objectId')==note_id:req.append(r)
(HERE/'repair-requests.json').write_text(json.dumps(req,indent=2)+'\n')
print(json.dumps({'repair_requests':len(req),'new_videos':2}))
