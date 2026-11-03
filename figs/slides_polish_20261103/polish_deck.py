"""Restyle the existing 13-slide film deck without replacing its native videos.

Reads a connector snapshot, emits native Slides mutations, SVG proofs, notes,
and source provenance. No inference, fabricated paths, or remote writes here.
"""
from pathlib import Path
import base64
import copy
import hashlib
import html
import json
import math
import subprocess
import sys

import contourpy
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent
ROOT = FIGS.parent
sys.path.insert(0, str(FIGS))
from figure_style import ESDF_CMAP, ESDF_NORM, ROLE

BEFORE = json.loads((HERE/'raw-template.json').read_text())['structuredContent']
OLD = json.loads((FIGS/'video_slides_20261103/canvas.json').read_text())
PLAN = json.loads((FIGS/'video_slides_20261103/slide_plan.json').read_text())
NATIVE = {e['objectId']:e for s in BEFORE['slides'] for e in s['pageElements']}
INK='#202124'; MUTED='#60646A'; ACCENT='#E66F21'; DARK='#111619'
BG='#FCFCFA'; LIGHT='#E8E9E6'; WHITE='#FFFFFF'; GOLD='#FFC52F'
SERIF='Times New Roman'; SANS='Arial'
ASSETS=HERE/'assets'; ASSETS.mkdir(exist_ok=True)

with np.load(FIGS/'pipeline/assets/scene_data.npz') as z:
    ESDF=z['esdf'].copy(); GOAL=z['goal'].copy()
    PATHS={k:z[f'path_{k}'].copy() for k in (0,1,3,7,14)}
    ORACLE=z['oracle_direction'].copy()
with np.load(FIGS/'model/plots/sixth_iteration.npz') as z:
    PATHS[6]=z['path_6'].copy()
RATIO=1.45
BOUNDS=[-.15,5.4,-5.55/RATIO/2,5.55/RATIO/2]
xx=np.linspace(BOUNDS[0],BOUNDS[1],1160)
yy=np.linspace(BOUNDS[2],BOUNDS[3],800)
gx,gy=np.meshgrid(xx,yy)
values=map_coordinates(ESDF,[(gy+10)/.02-.5,gx/.02-.5],order=1,mode='nearest')
im=Image.fromarray(np.uint8(ESDF_CMAP(ESDF_NORM(values[::-1]))*255)).convert('RGB')
draw=ImageDraw.Draw(im)
contours=contourpy.contour_generator(x=xx,y=yy,z=values).lines(0)
for c in contours:
    pts=[((float(x)-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0])*1159,
          (BOUNDS[3]-float(y))/(BOUNDS[3]-BOUNDS[2])*799) for x,y in c]
    if len(pts)>1: draw.line(pts,fill='#4F5865',width=3)
im.save(ASSETS/'esdf-reference.png')

def rgb(c):
    return {k:int(c[i:i+2],16)/255 for k,i in [('red',1),('green',3),('blue',5)]}

class Slide:
    def __init__(self,n,title,section,dark=False):
        self.n=n; self.old=OLD[n-1]; self.id=self.old['id']; self.dark=dark
        self.title=title; self.section=section; self.bg=DARK if dark else BG
        self.elements=[]; self.used=set(); self.new=0
        self.mapping=[]
    def add(self,kind,oid=None,**kw):
        if oid is None:
            self.new+=1;oid=f'gp_{self.n:02}_{self.new:03}'
        assert oid not in self.used,oid
        self.used.add(oid)
        e=dict(kind=kind,id=oid,page=self.id,**kw);self.elements.append(e)
        return oid
    def text(self,oid,x,y,w,h,text,size=16,color=None,bold=False,font=SERIF,align='START',caption=False):
        assert text.strip()
        return self.add('text',oid,x=x,y=y,w=w,h=h,text=text,size=size,
                        color=color or (WHITE if self.dark else INK),bold=bold,
                        font=font,align=align,caption=caption)
    def rect(self,oid,x,y,w,h,fill='none',stroke=None,r=0):
        return self.add('rect',oid,x=x,y=y,w=w,h=h,fill=fill,stroke=stroke,r=r)
    def line(self,oid,x1,y1,x2,y2,color=INK,width=1.2,arrow=False,dash=False):
        return self.add('line',oid,x1=x1,y1=y1,x2=x2,y2=y2,color=color,width=width,arrow=arrow,dash=dash)
    def image(self,oid,asset,x,y,w,h):
        iw,ih=Image.open(asset).size
        assert abs(w/h-iw/ih)<.004,(asset,w/h,iw/ih)
        return self.add('image',oid,asset=str(asset),x=x,y=y,w=w,h=h)
    def video(self,oid,x,y,h):
        old=next(e for e in self.old['elements'] if e['id']==oid)
        w=h*9/16
        return self.add('video',oid,asset=str(FIGS/'video_slides_20261103/assets'/(old['asset']+'.jpg')),x=x,y=y,w=w,h=h)
    def header(self,kicker,title,rule):
        self.text(kicker,34,17,630,18,self.section,10,MUTED,False,SANS,caption=True)
        self.text(title,33,45,655,42,self.title,29,bold=True)
        self.rect(rule,34,390,652,.65,'#343C42' if self.dark else '#D9DCD8')
        self.text(None,657,383,30,19,str(self.n),9,MUTED,font=SANS,align='END',caption=True)
    def map(self,x,y,w,depth=0,pool=(),prior=False,oracle=False):
        h=w/RATIO; pools={}
        for e in self.old['elements']:
            if e['id'] in pool and e['kind']!='image':pools.setdefault(e['kind'],[]).append(e['id'])
        def oid(k):return pools.get(k,[]).pop(0) if pools.get(k) else None
        self.image(None,ASSETS/'esdf-reference.png',x,y,w,h)
        self.rect(oid('rect'),x,y,w,h,'none','#A0A5AC')
        lo,hi,bottom,top=BOUNDS
        def pt(p):return x+(float(p[0])-lo)/(hi-lo)*w,y+(top-float(p[1]))/(top-bottom)*h
        def path(values,color,dash=False,points=True):
            if not dash:
                for a,b in zip(values,values[1:]): self.line(oid('line'),*pt(a),*pt(b),WHITE,3.8)
            for a,b in zip(values,values[1:]):self.line(oid('line'),*pt(a),*pt(b),color,2.1 if not dash else 1.4,dash=dash)
            if points:
                for p in values:
                    a,b=pt(p);self.add('ellipse',oid('ellipse'),x=a-1.7,y=b-1.7,w=3.4,h=3.4,fill=GOLD if depth else '#899096',stroke=color)
        if prior and depth:path(PATHS[0],'#899096',True,False)
        path(PATHS[depth],ACCENT if depth else '#899096',depth==0)
        if oracle:
            for i in (3,6,9,12,15):self.line(oid('line'),*pt(PATHS[0][i]),*pt(PATHS[0][i]+.65*ORACLE[i]),ACCENT,1.65,True)
        a,b=pt(GOAL);self.add('star',oid('star'),x=a-5.5,y=b-5.5,w=11,h=11,fill=GOLD,stroke=INK)
        a,b=pt([0,0]);self.add('ellipse',oid('ellipse'),x=a-3,y=b-3,w=6,h=6,fill=WHITE,stroke=INK)
        self.mapping.append(dict(role='recorded path panel',depth=depth,metric_bounds=BOUNDS,
                                 source='model/plots/sixth_iteration.npz' if depth==6 else 'pipeline/assets/scene_data.npz'))
    def panel(self,box,title,sub,x,y,w,h,role,label,detail):
        fill,border=ROLE[role]
        self.rect(box,x,y,w,h,fill,border,r=4)
        self.text(title,x+7,y+8,w-14,30,label,18,bold=True,align='CENTER')
        self.text(sub,x+7,y+37,w-14,h-37,detail,12.5,MUTED,font=SANS,align='CENTER')

def ids(a,b):return [f'gv_{i:04}' for i in range(a,b+1)]
S=[]
def new(n,title,section,dark=False):
    s=Slide(n,title,section,dark);S.append(s);return s

s=new(1,'GEAR-Nav','SUPPLEMENTARY VIDEO',True)
s.rect('gv_0001',34,390,652,.65,'#343C42')
s.text('gv_0002',34,30,450,20,'ROBOT NAVIGATION  /  SUPPLEMENTARY VIDEO',10,'#ABB3B9',font=SANS,caption=True)
s.text('gv_0003',32,98,290,61,'GEAR-Nav',46,bold=True)
s.text('gv_0004',34,172,267,103,'Action-free spatial\ntrajectory refinement\nvia energy-based aggregation',22)
s.text('gv_0005',34,310,267,47,'Learning corrections\nfrom geometric energy',15,'#BBC3C8',font=SANS)
for oid,x in [('gv_0006',331),('gv_0007',452),('gv_0008',573)]:s.video(oid,x,105,200)
s.text('gv_0009',331,320,354,37,'Indoor and outdoor robot deployments',11,'#BBC3C8',font=SANS,align='CENTER',caption=True)

s=new(2,'Learning from video without target paths','MOTIVATION')
s.header('gv_0010','gv_0011','gv_0012')
s.image('gv_0014',FIGS/'video_slides_20261103/assets/rgb.jpg',34,113,384,216)
s.text('gv_0015',34,337,384,20,'In-the-wild egocentric observation',11,MUTED,font=SANS,caption=True)
s.text('gv_0013',451,117,235,85,'Video provides scenes,\nbut no robot actions\nor target paths.',22)
s.rect('gv_0016',454,233,36,2,ACCENT)
s.text('gv_0017',451,249,235,84,'Learn how a\ncandidate path\nshould change.',24,bold=True)
s.text('gv_0018',34,365,650,20,'Geometric supervision for navigation adaptation',12,MUTED,font=SANS,caption=True)

s=new(3,'Geometry defines the training signal','TRAINING  /  GEOMETRIC ENERGY')
s.header('gv_0019','gv_0020','gv_0021')
s.map(34,121,282,0,ids(22,56))
s.text('gv_0057',34,327,282,22,'Candidate path in reconstructed geometry',11,MUTED,font=SANS,caption=True)
rows=[('gv_0058','gv_0059','gv_0060',114,'Goal-directed progress','Reach the destination; discourage retreat.'),
      ('gv_0064','gv_0065','gv_0066',187,'Footprint clearance','Penalize collisions and close obstacles.'),
      ('gv_0070','gv_0071','gv_0072',260,'Motion regularity','Encourage smooth, goal-facing paths.')]
for rid,tid,bid,y,t,b in rows:
    s.rect(rid,351,y+2,2,48,ROLE['energy'][1])
    s.text(tid,365,y,320,29,t,21,bold=True)
    s.text(bid,366,y+31,320,32,b,13.5,MUTED,font=SANS)
s.text('gv_0076',351,339,334,34,'E(x; g, Φ) = ∑q λq Eq(x; g, Φ)',20,align='CENTER')

s=new(4,'Learn waypoint corrections','TRAINING  /  ENERGY-DERIVED SUPERVISION')
s.header('gv_0077','gv_0078','gv_0079')
s.map(34,122,282,0,ids(80,119),oracle=True)
s.text('gv_0120',34,329,282,24,'Local energy-descent directions',12,MUTED,font=SANS,caption=True)
s.panel('gv_0121','gv_0122','gv_0123',351,119,147,76,'energy','Energy oracle','Training geometry')
s.panel('gv_0124','gv_0125','gv_0126',541,119,145,76,'energy','Oracle target','Direction d*')
s.panel('gv_0128','gv_0129','gv_0130',351,254,147,76,'learned','GEAR model','Image + goal + path')
s.panel('gv_0131','gv_0132','gv_0133',541,254,145,76,'learned','Regression loss','Match oracle labels')
s.line('gv_0127',504,157,534,157,arrow=True)
s.line('gv_0134',504,292,534,292,arrow=True)
s.line('gv_0135',613,202,613,247,width=1.2,arrow=True,dash=True)
s.text('gv_0136',351,346,335,26,'Supervise the current candidate path.',14,MUTED,font=SANS,align='CENTER')

s=new(5,'Aggregate labels along model rollouts','TRAINING  /  DATASET AGGREGATION')
s.header('gv_0137','gv_0138','gv_0139')
panels=[('gv_0140','gv_0141','gv_0142',34,'input','Path states','Visited paths'),
        ('gv_0144','gv_0145','gv_0146',205,'energy','Energy oracle','Query labels'),
        ('gv_0148','gv_0149','gv_0150',376,'replay','Replay','All prior rounds'),
        ('gv_0152','gv_0153','gv_0154',547,'learned','Train GEAR','All replay rounds')]
for b,t,u,x,r,label,detail in panels:s.panel(b,t,u,x,124,140,89,r,label,detail)
for oid,x in [('gv_0143',180),('gv_0147',351),('gv_0151',522)]:s.line(oid,x,168,x+18,168,arrow=True)
s.line('gv_0155',617,219,617,247)
s.line('gv_0156',617,247,104,247)
s.line('gv_0157',104,247,104,219,arrow=True)
s.text('gv_0158',174,257,372,27,'Visit the next candidate paths',16,ACCENT,align='CENTER')
for i,(box,txt,label) in enumerate([('gv_0159','gv_0160','B₁'),('gv_0161','gv_0162','B₂'),('gv_0163','gv_0164','B₃'),('gv_0165','gv_0166','…'),('gv_0167','gv_0168','Bᵣ')]):
    x=191+i*67;s.rect(box,x,305,58,31,ROLE['replay'][0],ROLE['replay'][1],r=3)
    s.text(txt,x+3,307,52,26,label,17,align='CENTER')
s.text('gv_0169',34,351,652,25,'Retain correction labels across aggregation rounds.',14,MUTED,font=SANS,align='CENTER')

s=new(6,'Refine a path from vision','DEPLOYMENT  /  PATH-CONDITIONED MODEL')
s.header('gv_0170','gv_0171','gv_0172')
s.image('gv_0173',FIGS/'video_slides_20261103/assets/rgb.jpg',34,112,171,96.1875)
s.text('gv_0174',34,213,171,22,'RGB observation',11,MUTED,font=SANS,align='CENTER',caption=True)
s.rect('gv_0175',34,251,171,54,ROLE['goal'][0],ROLE['goal'][1],r=4)
s.text('gv_0176',41,263,157,29,'Navigation goal',19,bold=True,align='CENTER')
s.panel('gv_0177','gv_0178','gv_0179',255,181,171,78,'neutral','Pretrained VLA','Visual + goal context')
s.panel('gv_0180','gv_0181','gv_0182',484,181,179,78,'learned','Waypoint expert','Predict a correction')
s.rect(None,484,105,179,52,ROLE['input'][0],ROLE['input'][1],r=4)
s.text(None,490,116,167,30,'Candidate path',17,bold=True,align='CENTER')
s.rect('gv_0190',484,305,179,44,ROLE['neutral'][0],ROLE['neutral'][1],r=4)
s.text('gv_0191',490,313,167,31,'Bounded path update',16.5,bold=True,align='CENTER')
s.line('gv_0183',212,159,248,203,arrow=True)
s.line('gv_0184',212,278,248,238,arrow=True)
s.line('gv_0185',432,220,477,220,arrow=True)
s.line('gv_0186',573,163,573,174,arrow=True)
s.line('gv_0187',573,265,573,298,arrow=True)
s.line('gv_0188',669,327,693,327)
s.line(None,693,327,693,131)
s.line(None,693,131,669,131,arrow=True)
s.text('gv_0189',444,355,241,24,'Repeat with the updated path',13,MUTED,font=SANS,align='CENTER')
s.text(None,34,332,371,46,'No ESDF or energy queries\nat deployment',18)

s=new(7,'Recorded model-only refinement','DEPLOYMENT  /  SAVED CHECKPOINT EXAMPLE')
s.header('gv_0192','gv_0193','gv_0194')
for x,depth,tid,pool in [(34,0,'gv_0195',ids(196,230)),(262,6,'gv_0231',ids(232,296)),(490,14,'gv_0297',ids(298,362))]:
    s.text(tid,x,118,196,30,'Initial path' if depth==0 else f'After {depth} updates',21,bold=True,align='CENTER')
    s.map(x,160,196,depth,pool,prior=True)
s.line('gv_0363',236,228,255,228,arrow=True)
s.line('gv_0364',464,228,483,228,arrow=True)
s.line('gv_0365',121,326,148,326,'#899096',1.5,dash=True)
s.text('gv_0366',155,315,174,25,'Initial candidate',13,MUTED,font=SANS)
s.line('gv_0367',369,326,396,326,ACCENT,2.1)
s.text('gv_0368',403,315,210,25,'Learned refinement',13,MUTED,font=SANS)
s.text('gv_0369',34,355,652,24,'ESDF shown for reference; the model does not query it.',12,MUTED,font=SANS,align='CENTER',caption=True)

def comparison(n,title,kicker,rule,goal_kicker,goal,body,methods,foot,labels,vids):
    s=new(n,title,kicker,True)
    # The portrait recordings set the composition; keep their full frames.
    s.text(kicker,34,28,245,20,f'REAL-WORLD  /  SCENARIO {n-7}',10,'#ABB3B9',font=SANS,caption=True)
    s.text(rule,33,88,237,94,title,29,bold=True)
    s.text(goal_kicker,34,215,237,20,'GOAL',10,GOLD,font=SANS,caption=True)
    s.text(goal,33,242,237,75,body,24)
    s.text(methods,34,340,237,35,'Representative separate trials',10.5,'#BBC3C8',font=SANS,caption=True)
    for lid,vid,x,label in zip(labels,vids,[294,510],['GEAR-Nav','OmniVLA']):
        s.text(lid,x,22,183.375,26,label,19,ACCENT if label=='GEAR-Nav' else '#CFD8E5',bold=True,align='CENTER')
        s.video(vid,x,55,326)
    s.text(foot,294,385,399,18,'1× playback',10,'#BBC3C8',font=SANS,align='CENTER',caption=True)
    return s

s=comparison(8,'Around an\nintervening chair','gv_0370','gv_0371','gv_0373','gv_0374','Person beyond\nthe chair','gv_0375','gv_0380',['gv_0376','gv_0378'],['gv_0377','gv_0379'])
s.rect('gv_0372',34,390,236,.65,'#343C42')
s=comparison(9,'Past a moving\nperson','gv_0381','gv_0382','gv_0384','gv_0385','Blue chair in\nthe lounge','gv_0386','gv_0391',['gv_0387','gv_0389'],['gv_0388','gv_0390'])
s.rect('gv_0383',34,390,236,.65,'#343C42')

s=new(10,'Scooter goal among pedestrians','REAL-WORLD  /  SCENARIO 3',True)
s.text('gv_0393',33,16,582,38,s.title,28,bold=True)
s.text('gv_0392',596,22,92,20,'SCENARIO 3',10,'#ABB3B9',font=SANS,align='END',caption=True)
for x,t,v,label in [(34,'gv_0396','gv_0397','GEAR-Nav'),(276,'gv_0398','gv_0399','OmniVLA'),(518,'gv_0400','gv_0401','NaVILA')]:
    s.text(t,x,54,168.75,27,label,19,ACCENT if label=='GEAR-Nav' else '#CFD8E5',bold=True,align='CENTER')
    s.video(v,x,85,300)
s.text('gv_0395',34,386,285,18,'Goal: scooter beyond the pedestrians',10,'#BBC3C8',font=SANS,caption=True)
s.text('gv_0402',332,386,355,18,'Separate trials · 1× playback',10,'#BBC3C8',font=SANS,align='END',caption=True)

s=new(11,'Additional robot deployments','REAL-WORLD  /  GEAR-NAV',True)
s.text('gv_0404',33,16,620,38,s.title,28,bold=True)
s.text('gv_0403',589,22,98,20,'GEAR-Nav',10,'#ABB3B9',font=SANS,align='END',caption=True)
for x,t,v,f,label in [(34,'gv_0406','gv_0407','gv_0408','Indoor'),(276,'gv_0409','gv_0410','gv_0411','Lounge'),(518,'gv_0412','gv_0413','gv_0414','Outdoor')]:
    s.text(t,x,54,168.75,27,label,19,bold=True,align='CENTER')
    s.video(v,x,85,300)
    s.text(f,x,386,168.75,18,'1× playback',10,'#BBC3C8',font=SANS,align='CENTER',caption=True)

s=new(12,'From geometric supervision to visual refinement','GEAR-NAV  /  METHOD RECAP')
s.header('gv_0415','gv_0416','gv_0417')
s.text('gv_0419',34,116,203,22,'TRAINING',10,MUTED,font=SANS,caption=True)
s.map(34,151,203,0,oracle=True)
s.text('gv_0420',34,301,203,29,'Energy oracle',20,bold=True)
s.text('gv_0421',34,333,203,42,'Query local corrections',13,MUTED,font=SANS)
s.rect('gv_0422',289,169,143,96,ROLE['learned'][0],ROLE['learned'][1],r=4)
s.text('gv_0423',295,184,131,30,'GEAR-Nav',23,bold=True,align='CENTER')
s.text('gv_0424',296,223,129,32,'Correction field',14,font=SANS,align='CENTER')
s.text('gv_0425',277,301,166,44,'Aggregate labels at\nmodel-visited paths',14,MUTED,font=SANS,align='CENTER')
s.text('gv_0427',484,116,203,22,'DEPLOYMENT',10,MUTED,font=SANS,caption=True)
s.image(None,FIGS/'video_slides_20261103/assets/rgb.jpg',484,151,203,114.1875)
s.text('gv_0428',484,301,203,29,'Visual refinement',20,bold=True)
s.text('gv_0429',484,333,203,42,'RGB + goal + candidate path',13,MUTED,font=SANS)
s.line(None,246,217,280,217,arrow=True)
s.line(None,441,217,475,217,arrow=True)
s.text('gv_0430',34,363,652,23,'Training geometry supplies the supervision; the learned field refines paths at deployment.',12,MUTED,font=SANS,align='CENTER',caption=True)

s=new(13,'GEAR-Nav','CLOSING',True)
s.rect('gv_0431',34,390,652,.65,'#343C42')
s.text('gv_0432',34,60,650,62,'GEAR-Nav',46,bold=True)
s.text('gv_0433',34,148,650,96,'Action-free spatial trajectory refinement\nvia energy-based aggregation',27)
s.rect('gv_0434',37,277,40,2,ACCENT)
s.text('gv_0435',34,309,650,59,'Geometric supervision during training.\nVision-conditioned refinement at deployment.',19,'#BBC3C8',font=SANS)

NARRATION=[
    'GEAR-Nav learns navigation from local geometric corrections. At deployment, it refines a candidate path from vision and a navigation goal.',
    'In-the-wild video provides diverse navigation scenes, but no robot actions or target paths. We use reconstructed geometry to teach how a candidate path should change.',
    'During training, geometric energy measures goal-directed progress, clearance around the robot footprint, and motion regularity. Its local descent direction provides supervision.',
    'The energy oracle supplies a projection-aware correction at the current candidate path. GEAR learns to predict this correction from the image, goal, and path.',
    'Each model update changes the next candidate path. We query new correction labels at these visited paths and retain earlier rounds in a shared replay dataset.',
    'At deployment, visual and goal context condition the waypoint expert. It predicts a correction, applies a bounded path update, and repeats. No ESDF or energy query is required.',
    'This checkpoint example shows the initial path and learned states at six and fourteen updates. The displayed distance field is a reference; it is not queried by the model.',
    'The first scenario approaches a person beyond an intervening chair. These separate recordings show how GEAR-Nav and OmniVLA navigate the cluttered space.',
    'The second scenario approaches a blue chair while a person moves through the lounge. The continuous recordings keep the encounter and destination visible.',
    'Outdoors, the destination is a scooter beyond the pedestrians. The comparison shows representative GEAR-Nav, OmniVLA, and NaVILA recordings from separate trials.',
    'Additional recordings show GEAR-Nav navigating the indoor, lounge, and outdoor settings.',
    'Geometry supplies local correction labels during training. Aggregation covers model-visited paths. At deployment, the learned field repeatedly refines a path from visual inputs.',
    'GEAR-Nav: action-free spatial trajectory refinement via energy-based aggregation.'
]
for i,s in enumerate(S):
    plan=copy.deepcopy(PLAN[i]);plan.update(title=s.title,narration=NARRATION[i],construction='Edit existing native slide in place',exemplar_slide_id=s.id)
    # Keep original production intervals and source boundaries; fix stale counts.
    if i==6:
        plan['editing_notes']='00:55–01:05. Reveal initial, six-update, and fourteen-update panels. Initial and final paths come from the original model-only capture. The sixth state is the verified same-checkpoint continuation resumed from saved depth 3; its receipt reports a 0.04256 m max difference at depth 7 from the original batch. These are qualitative checkpoint states, not an exact single uninterrupted trace or the paper’s fixed 12-step evaluation. Do not infer benchmark or safety metrics. ESDF is a visualization reference only.'
        plan['sources']=['figs/pipeline/assets/scene_data.npz','figs/model/plots/sixth_iteration.npz','figs/model/plots/sixth_iteration.json']
    if i==0:plan['editing_notes']='00:00–00:08. Play all three original muted videos at 1× in the deck. Opening sources use seconds 3–11. The title follows the project naming instruction; the manuscript currently uses a different expanded title. No author identity or unverified release URL is inserted.'
    if i==10:plan['editing_notes']='02:25–02:45. Use the additional-deployment fallback. The deck plays all original clips at 1×. Final-video edit targets are 2× indoor, 2× lounge, and 3× outdoor. Available simulation clips use privileged exact goals and are omitted from benchmark evidence.'
    if i==12:plan['editing_notes']='02:55–03:00. Hold the project title and scope. Add a project URL only after release and anonymity requirements are settled.'
    plan['native_video_policy']='Original DRIVE videos retained, muted, autoplay, 1×; final-video acceleration is a production instruction only.'
    plan['element_mapping']=[]
    for e in s.old['elements']:
        action='keep/edit' if e['id'] in s.used else 'delete'
        reason=('retain native video source and playback' if e['kind']=='video' else 'reuse native element for its narrative role') if action!='delete' else 'remove redundant decoration/text, or replace old ESDF viewport with the shared calibrated reference'
        plan['element_mapping'].append({'object_id':e['id'],'type':e['kind'],'action':action,'reason':reason})
    assert all(e['id'] in s.used for e in s.old['elements'] if e['kind']=='video')
    s.plan=plan

def base_size(e):
    a=[]
    for k in ('width','height'):
        d=e['size'][k];a.append(d['magnitude']/(12700 if d['unit']=='EMU' else 1))
    return a

def geometry(e,bw,bh):
    if e['kind']=='line':
        dx=e['x2']-e['x1'];dy=e['y2']-e['y1']
        return dict(scaleX=(dx+dy)/(2*bw),scaleY=(dx+dy)/(2*bh),shearX=(dx-dy)/(2*bh),shearY=(dy-dx)/(2*bw),translateX=e['x1'],translateY=e['y1'],unit='PT')
    return dict(scaleX=e['w']/bw,scaleY=e['h']/bh,shearX=0,shearY=0,translateX=e['x'],translateY=e['y'],unit='PT')

def mutate(e):
    k=e['kind'];oid=e['id'];req=[]
    if oid in NATIVE:
        bw,bh=base_size(NATIVE[oid]);req.append({'updatePageElementTransform':{'objectId':oid,'applyMode':'ABSOLUTE','transform':geometry(e,bw,bh)}})
    else:
        # New objects use a canonical 1-pt diagonal or the exact media bounds.
        bw,bh=(1,1) if k=='line' else (e['w'],e['h'])
        prop={'pageObjectId':e['page'],'size':{'width':{'magnitude':bw,'unit':'PT'},'height':{'magnitude':bh,'unit':'PT'}},'transform':geometry(e,bw,bh)}
        if k=='line':req.append({'createLine':{'objectId':oid,'lineCategory':'STRAIGHT','elementProperties':prop}})
        elif k=='image':return [{'createImage':{'objectId':oid,'url':e['asset'],'elementProperties':prop}}]
        else:req.append({'createShape':{'objectId':oid,'shapeType':{'text':'TEXT_BOX','rect':'ROUND_RECTANGLE' if e.get('r') else 'RECTANGLE','ellipse':'ELLIPSE','star':'STAR_5'}[k],'elementProperties':prop}})
    if k in ('image','video'):return req
    if k=='line':
        req.append({'updateLineProperties':{'objectId':oid,'lineProperties':{'lineFill':{'solidFill':{'color':{'rgbColor':rgb(e['color'])}}},'weight':{'magnitude':e['width'],'unit':'PT'},'startArrow':'NONE','endArrow':'FILL_ARROW' if e['arrow'] else 'NONE','dashStyle':'DASH' if e['dash'] else 'SOLID'},'fields':'lineFill,weight,startArrow,endArrow,dashStyle'}})
    elif k=='text':
        if oid in NATIVE:req.append({'deleteText':{'objectId':oid,'textRange':{'type':'ALL'}}})
        req.extend([
            {'updateShapeProperties':{'objectId':oid,'shapeProperties':{'outline':{'propertyState':'NOT_RENDERED'},'shapeBackgroundFill':{'propertyState':'NOT_RENDERED'},'contentAlignment':'TOP'},'fields':'outline,shapeBackgroundFill,contentAlignment'}},
            {'insertText':{'objectId':oid,'text':e['text'],'insertionIndex':0}},
            {'updateTextStyle':{'objectId':oid,'textRange':{'type':'ALL'},'style':{'fontFamily':e['font'],'fontSize':{'magnitude':e['size'],'unit':'PT'},'foregroundColor':{'opaqueColor':{'rgbColor':rgb(e['color'])}},'bold':e['bold'],'italic':False},'fields':'fontFamily,fontSize,foregroundColor,bold,italic'}},
            {'updateParagraphStyle':{'objectId':oid,'textRange':{'type':'ALL'},'style':{'alignment':e['align'],'lineSpacing':106,'spaceAbove':{'magnitude':0,'unit':'PT'},'spaceBelow':{'magnitude':0,'unit':'PT'}},'fields':'alignment,lineSpacing,spaceAbove,spaceBelow'}}])
    else:
        fill={'propertyState':'NOT_RENDERED'} if e['fill']=='none' else {'solidFill':{'color':{'rgbColor':rgb(e['fill'])},'alpha':1}}
        outline={'propertyState':'NOT_RENDERED'} if not e.get('stroke') else {'outlineFill':{'solidFill':{'color':{'rgbColor':rgb(e['stroke'])}}},'weight':{'magnitude':.8,'unit':'PT'},'propertyState':'RENDERED'}
        req.append({'updateShapeProperties':{'objectId':oid,'shapeProperties':{'shapeBackgroundFill':fill,'outline':outline},'fields':'shapeBackgroundFill,outline'}})
    if oid=='gv_0076':
        for i,c in enumerate(e['text']):
            if c=='q':req.append({'updateTextStyle':{'objectId':oid,'textRange':{'type':'FIXED_RANGE','startIndex':i,'endIndex':i+1},'style':{'baselineOffset':'SUBSCRIPT'},'fields':'baselineOffset'}})
    return req

def preview(s):
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1440" height="810" viewBox="0 0 720 405"><defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="{INK}"/></marker></defs><rect width="720" height="405" fill="{s.bg}"/>']
    for e in s.elements:
        k=e['kind']
        if k in ('image','video'):
            f=Path(e['asset']);b64=base64.b64encode(f.read_bytes()).decode();mime='image/png' if f.suffix=='.png' else 'image/jpeg'
            parts.append(f'<image x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" xlink:href="data:{mime};base64,{b64}" preserveAspectRatio="xMidYMid meet"/>')
        elif k=='text':
            anchor={'START':'start','CENTER':'middle','END':'end'}[e['align']]
            x=e['x']+3.6 if anchor=='start' else e['x']+e['w']/2 if anchor=='middle' else e['x']+e['w']-3.6
            for i,line in enumerate(e['text'].split('\n')):
                y=e['y']+3.6+e['size']*.93+i*e['size']*1.12
                font='Liberation Serif' if e['font']==SERIF else 'Liberation Sans'
                parts.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{e["size"]}" font-weight="{700 if e["bold"] else 400}" fill="{e["color"]}" text-anchor="{anchor}">{html.escape(line)}</text>')
        elif k=='line':parts.append(f'<line x1="{e["x1"]}" y1="{e["y1"]}" x2="{e["x2"]}" y2="{e["y2"]}" stroke="{e["color"]}" stroke-width="{e["width"]}"'+(' stroke-dasharray="4 3"' if e['dash'] else '')+(' marker-end="url(#a)"' if e['arrow'] else '')+'/>')
        elif k=='ellipse':parts.append(f'<ellipse cx="{e["x"]+e["w"]/2}" cy="{e["y"]+e["h"]/2}" rx="{e["w"]/2}" ry="{e["h"]/2}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}" stroke-width=".8"/>')
        elif k=='star':
            pts=[]
            for j in range(10):
                a=-math.pi/2+j*math.pi/5;r=e['w']/2*(1 if j%2==0 else .42);pts.append(f'{e["x"]+e["w"]/2+r*math.cos(a)},{e["y"]+e["h"]/2+r*math.sin(a)}')
            parts.append(f'<polygon points="{" ".join(pts)}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}" stroke-width=".8"/>')
        else:parts.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" rx="{e.get("r",0)}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}" stroke-width=".8"/>')
    parts.append('</svg>')
    folder=HERE/'proof';folder.mkdir(exist_ok=True)
    (folder/f'slide-{s.n:02}.svg').write_text(''.join(parts))
    subprocess.run(['rsvg-convert','-o',str(folder/f'slide-{s.n:02}.png'),str(folder/f'slide-{s.n:02}.svg')],check=True)

requests=[]; images=[]; plans=[]
for s in S:
    requests.append({'updatePageProperties':{'objectId':s.id,'pageProperties':{'pageBackgroundFill':{'solidFill':{'color':{'rgbColor':rgb(s.bg)},'alpha':1}}},'fields':'pageBackgroundFill'}})
    for e in BEFORE['slides'][s.n-1]['pageElements']:
        if e['objectId'] not in s.used:requests.append({'deleteObject':{'objectId':e['objectId']}})
    for e in s.elements:
        req=mutate(e)
        if e['kind']=='image' and e['id'] not in NATIVE:images+=req
        else:requests+=req
    # Restore drawing order after inserting new raster references.
    # The actual z-order mutation is emitted separately and applied after images.
    note_id=BEFORE['slides'][s.n-1]['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
    p=s.plan
    def stamp(t):return f'{int(t)//60:02}:{int(t)%60:02}'
    note=f'TARGET VIDEO TIMING: {stamp(p["start"])}–{stamp(p["end"])} ({p["duration_seconds"]} seconds)\n\nNARRATION\n{p["narration"]}\n\nEDIT CUES\n{p["editing_notes"]}\n\nPLAYBACK IN THIS DECK\n{p["native_video_policy"]}\n\nPAPER / FIGURE SOURCES\n'+ '\n'.join(p['sources'])+'\n\nEVIDENCE BOUNDARY\nNo unverified performance percentages. Baselines are representative separate trials. Goal labels describe the scene, not exact prompt transcriptions. ESDF is never an inference input. Action-free describes navigation adaptation; the VLA backbone is pretrained.\n'
    assert 'undefined' not in note
    requests.extend([{'deleteText':{'objectId':note_id,'textRange':{'type':'ALL'}}},{'insertText':{'objectId':note_id,'text':note,'insertionIndex':0}}])
    plans.append(p);preview(s)

zorder=[]
for s in S:
    for e in s.elements:zorder.append({'updatePageElementsZOrder':{'pageElementObjectIds':[e['id']],'operation':'BRING_TO_FRONT'}})
for name,value in [('requests',requests),('image-requests',images),('zorder-requests',zorder),('slide-plan',plans),('canvas',[dict(id=s.id,bg=s.bg,elements=s.elements) for s in S])]:
    (HERE/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
sources=['pipeline/assets/scene_data.npz','pipeline/assets/rgb.jpg','model/plots/sixth_iteration.npz','model/plots/sixth_iteration.json','figure_style.py']
prov=dict(presentation_id=BEFORE['presentationId'],source_revision=BEFORE['revisionId'],slide_count=13,
          new_inference=False,native_videos_retained=13,refinement_depths=[0,6,14],
          sixth_state='Same-checkpoint continuation from saved depth 3; see receipt',
          esdf_bounds=BOUNDS,esdf_range_m=[-3,3],
          sources_sha256={p:hashlib.sha256((FIGS/p).read_bytes()).hexdigest() for p in sources})
(HERE/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
print(json.dumps(dict(slides=len(S),requests=len(requests),image_requests=len(images),zorder_requests=len(zorder)),indent=2))
