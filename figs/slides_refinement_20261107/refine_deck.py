"""Build a VEGA-inspired revision of the existing native GEAR-Nav deck.

This emits a reviewable mutation plan and local SVG proofs; it makes no remote
writes. Source videos and recorded paths are retained, not re-generated.
"""
from pathlib import Path
from types import SimpleNamespace
import ast
import base64
import copy
import hashlib
import html
import json
import math
import subprocess

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent
ROOT = FIGS.parent
ASSETS = HERE / 'assets'
BEFORE = json.loads((HERE/'raw-gear-before.json').read_text())['structuredContent']
NATIVE = {e['objectId']: e for s in BEFORE['slides'] for e in s['pageElements']}
OLD = json.loads((FIGS/'slides_polish_20261103/canvas.json').read_text())
INK = '#202124'
SERIF = 'Times New Roman'
DARK = '#191919'
WHITE = '#F5F5F5'
MUTED = '#C5C9CE'
ACCENT = '#F08A45'

# Reuse the established native-geometry and SVG rendering helpers only.
# Do not execute the older deck construction or overwrite its artifacts.
source = (FIGS/'slides_polish_20261103/polish_deck.py').read_text()
tree = ast.parse(source)
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in {'rgb', 'base_size', 'geometry', 'mutate', 'preview'}:
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(HERE/'refine_deck.py'), 'exec'), globals())
original_mutate = mutate

def mutate(e):
    req = original_mutate(e)
    if e['kind'] == 'image' and e.get('replace'):
        # Google changes intrinsic size on replacement. Normalize geometry from
        # native readback in repair_deck.py rather than using the old size.
        req = [{'replaceImage': {'imageObjectId': e['id'], 'url': e['asset'], 'imageReplaceMethod': 'CENTER_INSIDE'}}]
    if e['kind'] == 'text':
        # Font changes are an intentional deck-wide restyle. Each box serves
        # one semantic role; diagram figures retain their original typography.
        for r in req:
            if 'updateTextStyle' in r:
                q=r['updateTextStyle'];q['style']['baselineOffset']='NONE';q['fields']+=',baselineOffset'
    return req

def get(s, oid):
    return next(e for e in s['elements'] if e['id'] == oid)

def remove(s, *oids):
    s['elements'] = [e for e in s['elements'] if e['id'] not in oids]

def put(s, oid, **kwargs):
    e = next((e for e in s['elements'] if e['id']==oid), None)
    if e is None:
        e = dict(id=oid, page=s['id']);s['elements'].append(e)
    e.update(kwargs)
    return e

def text(s, oid, x,y,w,h,value,size=18,color=WHITE,bold=False,align='START',caption=False):
    return put(s,oid,kind='text',x=x,y=y,w=w,h=h,text=value,size=size,color=color,bold=bold,font='Arial',align=align,caption=caption)

def rectangle(s, oid, x,y,w,h,fill):
    return put(s,oid,kind='rect',x=x,y=y,w=w,h=h,fill=fill,stroke=None,r=0)

def picture(s,oid,name,x,y,w,replace=False):
    p=ASSETS/name;iw,ih=Image.open(p).size
    return put(s,oid,kind='image',asset=str(p),x=x,y=y,w=w,h=w*ih/iw,replace=replace)

def in_panel(e, panels):
    if e['kind'] != 'text': return False
    return any(p['x'] <= e['x']+e['w']/2 <= p['x']+p['w'] and p['y'] <= e['y']+e['h']/2 <= p['y']+p['h'] for p in panels)

S=copy.deepcopy(OLD)
titles=[
    'GEAR-Nav',
    'Learn from video, without target paths',
    'Geometry defines the training signal',
    'GEAR-Nav training pipeline',
    'Train on paths the model visits',
    'GEAR model: learn a correction field',
    'Recorded model-only refinement',
    'Around an intervening chair',
    'Past a moving person',
    'Scooter goal among pedestrians',
    'Additional robot deployments',
    'From geometric supervision to visual refinement',
    'GEAR-Nav',
]
headings={2:'gv_0011',3:'gv_0020',4:'gv_0078',5:'gv_0138',6:'gv_0171',7:'gv_0193',8:'gv_0371',9:'gv_0382',10:'gv_0393',11:'gv_0404',12:'gv_0416'}
kickers={2:'gv_0010',3:'gv_0019',4:'gv_0077',5:'gv_0137',6:'gv_0170',7:'gv_0192',8:'gv_0370',9:'gv_0381',10:'gv_0392',11:'gv_0403',12:'gv_0415'}
for n,s in enumerate(S,1):
    s['bg']=DARK;s['title']=titles[n-1]
    panels=[e for e in s['elements'] if e['kind']=='rect' and e.get('fill') not in {'none','#343C42','#D9DCD8'} and e.get('h',0)>25]
    for e in s['elements']:
        if e['kind']=='text':
            e['font']='Arial'
            e['color']=INK if in_panel(e,panels) else (WHITE if e.get('bold') else MUTED)
        elif e['kind']=='line' and e['color']==INK:
            e['color']=MUTED
        elif e['kind']=='rect' and e.get('fill')=='#D9DCD8':
            e['fill']='#424242'
    if n in headings:
        # Keep each slide's native title box; add the VEGA-style header behind it.
        rid=f'gr_20261107_header_{n:02}'
        rectangle(s,rid,0,0,720,54,'#505050')
        bar=get(s,rid);s['elements'].remove(bar);s['elements'].insert(0,bar)
        text(s,headings[n],24,8,670,40,titles[n-1],26 if n==12 else 28,bold=True)
        remove(s,kickers[n],f'gp_{n:02}_001')
        # Footer numbering lives outside the media area.
        text(s,f'gr_20261107_num_{n:02}',670,386,40,18,str(n),9,MUTED,align='END',caption=True)

# Opening: preserve all three native robot videos, complete frames and intervals.
s=S[0]
text(s,'gv_0002',30,28,650,20,'GEOMETRIC ENERGY-GUIDED AGGREGATION AND REFINEMENT',10,MUTED,caption=True)
text(s,'gv_0003',28,92,290,65,'GEAR-Nav',46,bold=True)
text(s,'gv_0004',30,171,273,107,'Action-free spatial\ntrajectory refinement\nvia energy-based\naggregation',21,WHITE)
text(s,'gv_0005',30,310,274,48,'Learn corrections from video.\nRefine paths from vision.',15,MUTED)
text(s,'gv_0009',326,320,365,40,'Real-world robot deployments',12,MUTED,align='CENTER',caption=True)

# Motivation: one dominant observation and two short, connected statements.
s=S[1]
get(s,'gv_0014').update(x=24,y=100,w=384,h=216)
text(s,'gv_0015',24,324,384,20,'In-the-wild egocentric observation',11,MUTED,caption=True)
text(s,'gv_0013',437,101,260,100,'Video captures diverse\nnavigation scenes, but\nprovides no robot actions\nor target trajectories.',18,WHITE)
rectangle(s,'gv_0016',440,221,34,2,ACCENT)
text(s,'gv_0017',437,239,260,95,'Use scene geometry\nto teach how a path\nshould change.',22,WHITE,bold=True)
text(s,'gv_0018',24,361,650,22,'Geometric energy supplies local correction targets during training.',13,MUTED,caption=True)

# The two halves of the actual pipeline figure get separate full-width slides.
for index,oid,asset in [(2,'gp_03_002','pipeline-energy.png'),(3,'gp_04_002','pipeline-training.png')]:
    s=S[index];n=index+1
    keep={headings[n],f'gr_20261107_header_{n:02}',f'gr_20261107_num_{n:02}',oid}
    s['elements']=[e for e in s['elements'] if e['id'] in keep]
    if index==2:
        text(s,'gv_0057',24,65,672,30,'Supervise local corrections with a projection-aware energy oracle.',16,WHITE)
        picture(s,oid,asset,24,101,672,replace=True)
        text(s,'gv_0120_energy',24,386,650,16,'Training geometry only; no optimized target trajectory labels.',10,MUTED,caption=True)
    else:
        picture(s,oid,asset,24,67,672,replace=True)
        text(s,'gv_0136',24,385,650,17,'Oracle targets are aggregated across model-visited candidate paths.',10,MUTED,caption=True)

# Editable aggregation loop, using the established scientific role colors.
s=S[4]
get(s,'gv_0145').update(size=16)
text(s,'gr_20261107_agg_intro',34,77,652,30,'Each learned update changes the next training state.',18,WHITE)
text(s,'gv_0158',150,257,420,30,'Advance the model-generated frontier',16,ACCENT,align='CENTER')
text(s,'gv_0169',34,351,652,28,'Query corrections at visited paths; retain supervision from all earlier rounds.',14,MUTED,align='CENTER')

# A large, faithful view of the model figure, with readable native explanation.
s=S[5]
keep={headings[6],'gr_20261107_header_06','gr_20261107_num_06','gv_0173'}
s['elements']=[e for e in s['elements'] if e['id'] in keep]
picture(s,'gv_0173','model-architecture.png',24,73,330,replace=True)
text(s,'gv_0174',381,83,311,30,'Condition on vision and the path',19,WHITE,True)
text(s,'gv_0179',381,121,311,56,'RGB and the navigation goal provide\ncontext; the current path enters\nthe waypoint expert.',16,MUTED)
text(s,'gv_0181',381,193,311,30,'Predict a local correction',19,WHITE,True)
text(s,'gv_0182',381,231,311,48,'Learn the energy-oracle direction\nat each aggregated path state.',16,MUTED)
text(s,'gv_0191',381,291,311,30,'Apply a bounded update; repeat',19,WHITE,True)
text(s,'gv_0189',381,330,311,52,'At deployment, refinement uses\nno ESDF or analytic energy queries.',16,MUTED)

# Retain the recorded refinement panels, their path vertices, and metric bounds.
s=S[6]
for oid in ['gv_0195','gv_0231','gv_0297']:get(s,oid).update(size=20,color=WHITE)
text(s,'gv_0369',34,354,652,27,'Saved checkpoint example. ESDF is shown only as a geometric reference.',12,MUTED,align='CENTER',caption=True)

# Consistent framing for the two paired portrait-video comparison slides.
for index,goal_kicker,goal_id,caption_id,labels,vids,foot,goal,detail in [
 (7,'gv_0373','gv_0374','gv_0375',['gv_0376','gv_0378'],['gv_0377','gv_0379'],'gv_0380','Person beyond\nthe chair','Navigate around close clutter\nwhile progressing to the goal.'),
 (8,'gv_0384','gv_0385','gv_0386',['gv_0387','gv_0389'],['gv_0388','gv_0390'],'gv_0391','Blue chair in\nthe lounge','Reach the destination as a\nperson crosses the route.')]:
    s=S[index]
    text(s,goal_kicker,30,105,260,20,'NAVIGATION GOAL',10,ACCENT,caption=True)
    text(s,goal_id,29,136,267,80,goal,26,WHITE,bold=True)
    text(s,caption_id,30,257,268,66,detail,16,MUTED)
    for lid,vid,x,label in zip(labels,vids,[330,525],['GEAR-Nav','OmniVLA']):
        text(s,lid,x,57,168.75,25,label,17,ACCENT if label=='GEAR-Nav' else WHITE,True,align='CENTER')
        get(s,vid).update(x=x,y=84,w=168.75,h=300)
    text(s,foot,30,360,278,30,'Representative separate trials · 1×',11,MUTED,caption=True)
    remove(s,'gv_0372' if index==7 else 'gv_0383')

# The user confirmed that VEGA's labels are authoritative for these two clips
# despite their older download-folder names. Use the exact source IDs/intervals.
s=S[7]
remove(s,'gv_0373','gv_0375')
text(s,'gv_0374',24,365,650,23,'Goal: reach the person beyond the intervening chair',13,WHITE)
text(s,'gv_0380',24,386,640,17,'Separate trials · 1× playback · Baseline labels follow VEGA',10,MUTED,caption=True)
for label,lid,vid,x in [('GEAR-Nav','gv_0376','gv_0377',24),('OmniVLA','gv_0378','gv_0379',198),('NaVILA','gr_20261107_navila_label','gr_20261107_navila_video',372),('TIC-VLA','gr_20261107_tic_label','gr_20261107_tic_video',546)]:
    text(s,lid,x,59,151.875,25,label,17,ACCENT if label=='GEAR-Nav' else WHITE,True,align='CENTER')
    if vid in NATIVE:get(s,vid).update(x=x,y=90,w=151.875,h=270)
    else:
        key,fid,start,end=('vega-navila','1SwtuXQgXN-oztTsK9iVlgyUCvEywbsMm',6000,36000) if label=='NaVILA' else ('vega-ticvla','1tnb1Fm5BEpfdefOssROZBGLqcb78qA1A',2000,33213)
        put(s,vid,kind='video',asset=str(ASSETS/(key+'.jpg')),x=x,y=90,w=151.875,h=270,source_id=fid,start=start,end=end)

# Three-column native videos, full aspect ratio, without imitation frame crops.
for index in [9,10]:
    s=S[index]
    for e in s['elements']:
        if e['kind']=='text' and e.get('y')==54:e.update(size=17,color=ACCENT if e['text']=='GEAR-Nav' else WHITE)
    if index==9:
        text(s,'gv_0395',30,386,300,16,'Goal: scooter beyond the pedestrians',10,MUTED,caption=True)
        text(s,'gv_0402',340,386,338,16,'Separate trials · 1× playback',10,MUTED,align='END',caption=True)

# Recap: preserve native visuals and put the train/deploy distinction up front.
s=S[11]
text(s,'gv_0419',34,94,203,23,'TRAINING',12,ACCENT,True,caption=True)
text(s,'gv_0427',484,94,203,23,'DEPLOYMENT',12,ACCENT,True,caption=True)
text(s,'gv_0420',34,301,203,30,'Geometric supervision',17,WHITE,True)
text(s,'gv_0428',484,301,203,30,'Visual refinement',19,WHITE,True)
text(s,'gv_0430',34,363,652,24,'Learn corrections from geometry. Apply the learned field from vision.',13,MUTED,align='CENTER',caption=True)

s=S[12]
text(s,'gv_0432',34,67,650,65,'GEAR-Nav',46,WHITE,True)
text(s,'gv_0433',34,155,650,84,'Action-free spatial trajectory refinement\nvia energy-based aggregation',27,WHITE)
text(s,'gv_0435',34,308,650,59,'Geometric supervision during training.\nVision-conditioned refinement at deployment.',19,MUTED)

NARRATION=[
 'GEAR-Nav learns local trajectory corrections from geometric energy. At deployment, it repeatedly refines a candidate path using vision and a navigation goal.',
 'Egocentric videos provide diverse navigation scenes without robot actions or target trajectories. Reconstructed scene geometry supplies the signal for how a candidate path should change.',
 'The analytic energy measures footprint clearance, goal progress, retreat, early heading, and smoothness. The oracle normalizes and caps the gradient, then selects a step that remains acceptable after projection. The label is a local direction, not an optimized target trajectory.',
 'We initialize candidate paths, query correction labels, retain them in replay, and train GEAR on the accumulated states. The learned model advances the path frontier. The full-dataset continuation uses the current model to generate states and learns from oracle labels on those states.',
 'The model determines the paths it will encounter next. We query the energy oracle at those model-visited paths and retain labels from prior rounds. An energy acceptance guard is used during training collection only.',
 'The pretrained visual-language model provides context, while the waypoint expert sees the current trajectory. GEAR predicts a correction and applies a bounded update. This loop is reused at deployment without an ESDF, energy gradient, or energy acceptance test.',
 'These panels show saved model-only states at zero, six, and fourteen updates. The ESDF is a visualization reference, not a model input. This qualitative checkpoint illustration is distinct from the paper’s fixed twelve-step evaluation budget.',
 'In the first scenario, the goal is a person beyond an intervening chair. The recordings show GEAR-Nav, OmniVLA, NaVILA, and TIC-VLA in representative separate trials. The user confirmed the NaVILA and TIC-VLA labels from the supplied VEGA deck.',
 'The second scenario reaches a blue chair while a person crosses the lounge. These recordings show GEAR-Nav and OmniVLA in separate trials.',
 'The outdoor goal is a scooter beyond pedestrians. These representative trials compare GEAR-Nav, OmniVLA, and NaVILA.',
 'Additional recordings show GEAR-Nav deployments in the indoor, lounge, and outdoor scenes.',
 'Geometry supplies supervision during training. Aggregation covers model-visited paths. Deployment uses the learned field to refine paths from visual inputs.',
 'GEAR-Nav: action-free spatial trajectory refinement via energy-based aggregation.'
]

requests=[];image_requests=[];plans=[]
for i,s in enumerate(S):
    n=i+1;old_slide=BEFORE['slides'][i];used={e['id'] for e in s['elements']}
    for e in s['elements']:
        if e['kind']=='video':
            assert e['id'] in NATIVE or e.get('source_id')
            assert abs(e['w']/e['h']-9/16)<1e-8
        if e['kind']=='image':
            iw,ih=Image.open(e['asset']).size
            assert abs(e['w']/e['h']-iw/ih)<0.005
    assert all(e['objectId'] in used for e in old_slide['pageElements'] if 'video' in e)
    requests.append({'updatePageProperties':{'objectId':s['id'],'pageProperties':{'pageBackgroundFill':{'solidFill':{'color':{'rgbColor':rgb(DARK)},'alpha':1}}},'fields':'pageBackgroundFill'}})
    mapping=[]
    for e in old_slide['pageElements']:
        oid=e['objectId'];action='keep/edit' if oid in used else 'delete'
        kind='video' if 'video' in e else 'image' if 'image' in e else 'shape/line'
        reason='Retain source video and playback; resize proportionally' if kind=='video' else 'Reuse existing element in its semantic role'
        if action=='delete':
            reason='Replace the simplified diagram with the actual paper figure' if n in [3,4,6] else 'Remove redundant decoration or superseded text'
            requests.append({'deleteObject':{'objectId':oid}})
        mapping.append(dict(id=oid,kind=kind,action=action,reason=reason))
    for e in s['elements']:
        if e['kind']=='video' and e['id'] not in NATIVE:
            requests.extend([{'createVideo':{'objectId':e['id'],'source':'DRIVE','id':e['source_id'],'elementProperties':{'pageObjectId':s['id'],'size':{'width':{'magnitude':e['w'],'unit':'PT'},'height':{'magnitude':e['h'],'unit':'PT'}},'transform':{'scaleX':1,'scaleY':1,'translateX':e['x'],'translateY':e['y'],'unit':'PT'}}}}, {'updateVideoProperties':{'objectId':e['id'],'videoProperties':{'autoPlay':True,'mute':True,'start':e['start'],'end':e['end']},'fields':'autoPlay,mute,start,end'}}])
            continue
        r=mutate(e)
        if e['kind']=='image' and (e.get('replace') or e['id'] not in NATIVE):image_requests.append(dict(path=e['asset'],requests=r))
        else:requests.extend(r)
    note_id=old_slide['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
    original_notes=''.join(t.get('textRun',{}).get('content','') for el in old_slide['slideProperties']['notesPage'].get('pageElements',[]) if el['objectId']==note_id for t in el.get('shape',{}).get('text',{}).get('textElements',[]))
    note=('REFINED SLIDE / 2026-11-07\n'+s['title']+'\n\nNARRATION\n'+NARRATION[i]+'\n\nSOURCES AND SCOPE\nCurrent GEAR-Nav manuscript and its figure PDFs. Original native DRIVE clips retain their exact source IDs, intervals, mute and autoplay settings. All clips play at 1×. Comparisons are representative separate trials. No quantitative performance claim is added.\n\n')
    if n==8:note+='Additional baseline clips: NaVILA = 1SwtuXQgXN-oztTsK9iVlgyUCvEywbsMm (IMG_3134.MOV, seconds 6–36); TIC-VLA = 1tnb1Fm5BEpfdefOssROZBGLqcb78qA1A (IMG_3132.MOV, seconds 2–33.213). Labels come from VEGA slide p2 and were explicitly confirmed by the user on 2026-11-07. The older download manifest folder labels conflict; retain this provenance rather than silently rewriting the source record.\n\n'
    if n in [3,4]:note+='Figure source: GEAR-Nav Overleaf/fig/gear_pipeline.pdf, cropped at the semantic panel boundary. Pipeline replay progressions are schematic; they are not measured rollout states.\n\n'
    if n==6:note+='Figure source: GEAR-Nav Overleaf/fig/gear_model_simple.pdf, architecture panel (a). Action-free describes navigation adaptation; the pretrained backbone may have robot-action pretraining.\n\n'
    if n==7:note+='The sixth state comes from a same-checkpoint continuation from saved depth 3, with the original provenance retained below. This is not a single uninterrupted trace.\n\n'
    note+='ORIGINAL PRODUCTION NOTES (HISTORICAL TIMING)\n'+original_notes
    requests.extend([{'deleteText':{'objectId':note_id,'textRange':{'type':'ALL'}}},{'insertText':{'objectId':note_id,'insertionIndex':0,'text':note}}])
    exemplar='p5' if n in [3,4,6] else 'p2' if n in [8,9,10,11] else 'p1' if n in [1,13] else 'vega_motivation'
    plans.append(dict(slide=n,id=s['id'],title=s['title'],narrative=NARRATION[i],construction='Edit existing slide and reusable elements in place',source_exemplar_slide=exemplar,source_exemplar_deck='VEGA',mapping=mapping))
    preview(SimpleNamespace(n=n,bg=s['bg'],elements=s['elements']))

zorder=[{'updatePageElementsZOrder':{'pageElementObjectIds':[e['id']],'operation':'BRING_TO_FRONT'}} for s in S for e in s['elements']]
for name,value in [('requests',requests),('image-requests',image_requests),('zorder-requests',zorder),('slide-plan',plans),('canvas',S)]:
    (HERE/(name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
sources=['GEAR-Nav Overleaf/main.tex','GEAR-Nav Overleaf/fig/gear_pipeline.pdf','GEAR-Nav Overleaf/fig/gear_model_simple.pdf','figs/pipeline/assets/scene_data.npz','figs/model/plots/sixth_iteration.npz','figs/realworld_exp/download_manifest.json']
provenance=dict(presentation_id=BEFORE['presentationId'],source_revision=BEFORE['revisionId'],slides=len(S),native_videos_retained=13,native_videos_added=2,additional_model_inference=False,figma_calls=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},baseline_label_resolution='User explicitly confirmed on 2026-11-07: use labels shown in VEGA. IMG_3134 is labeled NaVILA and IMG_3132 is labeled TIC-VLA. Historical folder labels are retained unchanged.')
(HERE/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
pages=sorted((HERE/'proof').glob('slide-*.png'));contact=Image.new('RGB',(1440,math.ceil(len(pages)/3)*293),DARK);draw=ImageDraw.Draw(contact)
for i,p in enumerate(pages):
    im=Image.open(p);im.thumbnail((470,265));x=i%3*480;y=i//3*293;contact.paste(im,(x,y+20));draw.text((x+10,y+3),str(i+1),fill='white')
contact.save(HERE/'local-contact.jpg')
print(json.dumps(dict(slides=len(S),requests=len(requests),image_batches=len(image_requests),zorder=len(zorder))))
