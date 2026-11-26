"""Generate editable Slides requests and local proofs for a 180-second film."""
from pathlib import Path
import base64
import html
import json
import math

import subprocess
from PIL import Image

HERE=Path(__file__).resolve().parent
ASSETS=HERE/'assets'
W,H=720,405
FONT='Times New Roman'
INK='#171A20'; MUTED='#58616C'; ORANGE='#E76029'; DARK='#101419'
PALE={'input':'#E6EFFD','goal':'#E2EFE1','energy':'#FFE09A','replay':'#EAE2EE','learned':'#FADDDC','neutral':'#F2F2F2'}
REC=json.loads((HERE/'recorded_paths.json').read_text())
MEDIA={v['key']:v for v in json.loads((HERE/'media_manifest.json').read_text())}
COUNTER=0


def rgb(c):
    return {k:int(c[i:i+2],16)/255 for k,i in [('red',1),('green',3),('blue',5)]}


def props(page,x,y,w,h):
    return {'pageObjectId':page,'size':{'width':{'magnitude':w,'unit':'PT'},'height':{'magnitude':h,'unit':'PT'}},
            'transform':{'scaleX':1,'scaleY':1,'translateX':x,'translateY':y,'unit':'PT'}}


class Slide:
    def __init__(self,num,start,end,title,dark=False):
        self.id='p' if num==1 else f'gear_video_{num:02}'
        self.num=num;self.start=start;self.end=end;self.title=title
        self.bg=DARK if dark else '#FCFCFB';self.dark=dark;self.elements=[]
        self.narration='';self.edit='';self.sources=[]
        if num not in (1,13):
            self.text(30,12,600,16,'GEAR-NAV  /  SUPPLEMENTARY VIDEO',9.5,ORANGE,True,caption=True)
            self.text(30,34,670,45,title,28,'#FFFFFF' if dark else INK,True)
        self.rect(30,393,660,1,'#343B44' if dark else '#D9DDE1')

    def add(self,kind,**kwargs):
        global COUNTER
        COUNTER+=1;kwargs.update(kind=kind,id=f'gv_{COUNTER:04}',page=self.id)
        self.elements.append(kwargs);return kwargs['id']

    def text(self,x,y,w,h,value,size=16,color=INK,bold=False,align='START',caption=False):
        h=max(h,math.ceil(len(value.split('\n'))*size*1.15+8))
        return self.add('text',x=x,y=y,w=w,h=h,text=value,size=size,color=color,bold=bold,align=align,caption=caption)

    def rect(self,x,y,w,h,fill,stroke=None,r=0):
        return self.add('rect',x=x,y=y,w=w,h=h,fill=fill,stroke=stroke,r=r)

    def line(self,x1,y1,x2,y2,color=INK,width=1.5,arrow=False,dash=False):
        return self.add('line',x1=x1,y1=y1,x2=x2,y2=y2,color=color,width=width,arrow=arrow,dash=dash)

    def image(self,key,x,y,w,h):
        return self.add('image',asset=key,x=x,y=y,w=w,h=h)

    def video(self,key,x,y,w,h,start=0,end=None):
        return self.add('video',asset=key,x=x,y=y,w=w,h=h,start=start,end=end)

    def box(self,x,y,w,h,fill,title,subtitle=None):
        self.rect(x,y,w,h,fill,r=7)
        self.text(x+8,y+9,w-16,27,title,18,INK,True,align='CENTER')
        if subtitle:self.text(x+8,y+39,w-16,h-41,subtitle,13,INK,align='CENTER')

    def map(self,x,y,w,h,depth=0,prior=False,oracle=False):
        # Fit the exact same metric rectangle at one aspect ratio on every slide.
        ratio=(REC['bounds'][1]-REC['bounds'][0])/(REC['bounds'][3]-REC['bounds'][2])
        h=min(h,w/ratio);w=h*ratio
        self.image('esdf',x,y,w,h)
        self.rect(x,y,w,h,'none','#A7ADB5')
        lo,hi,bottom,top=REC['bounds']
        def pt(v):return x+(v[0]-lo)/(hi-lo)*w,y+(top-v[1])/(top-bottom)*h
        def path(values,color,dash=False,points=True):
            if not dash:
                for a,b in zip(values,values[1:]):self.line(*pt(a),*pt(b),'#FFFFFF',3.7)
            for a,b in zip(values,values[1:]):self.line(*pt(a),*pt(b),color,2.2 if not dash else 1.4,dash=dash)
            if points:
                for p in values:
                    a,b=pt(p);self.add('ellipse',x=a-1.65,y=b-1.65,w=3.3,h=3.3,fill='#FFC52F',stroke=color)
        if prior and depth!=0:path(REC['paths']['0'],'#727B85',True,False)
        values=REC['paths'][str(depth)]
        path(values,ORANGE if depth else '#727B85',depth==0)
        if oracle:
            for i in (3,6,9,12,15):
                p=values[i];d=REC['oracle_direction'][i]
                q=[p[j]+.65*d[j] for j in (0,1)]
                self.line(*pt(p),*pt(q),ORANGE,1.7,arrow=True)
        a,b=pt(REC['goal']);self.add('star',x=a-5,y=b-5,w=10,h=10,fill='#FFC52F',stroke=INK)
        a,b=pt([0,0]);self.add('ellipse',x=a-3,y=b-3,w=6,h=6,fill='#FFFFFF',stroke=INK)


S=[]
def new(start,end,title,dark=False):
    s=Slide(len(S)+1,start,end,title,dark);S.append(s);return s

s=new(0,8,'GEAR-Nav',True)
s.text(32,35,330,25,'SUPPLEMENTARY VIDEO',11,ORANGE,True,caption=True)
s.text(30,86,350,65,'GEAR-Nav',48,'#FFFFFF',True)
s.text(32,160,335,90,'Learning to refine\nnavigation paths',29,'#FFFFFF',True)
s.text(33,279,325,55,'Energy-derived supervision.\nModel-only trajectory refinement.',17,'#CFD4DA')
for key,x in [('gear_s1',393),('gear_s2',493),('gear_s3',593)]:s.video(key,x,93,91,161.78,3,11)
s.text(391,271,300,45,'Indoor and outdoor robot navigation',14,'#CFD4DA',align='CENTER')
s.narration='GEAR-Nav learns to refine navigation paths from geometric energy, then applies those corrections using visual observations and goal conditioning.'
s.edit='00:00–00:08. Start all three muted clips together. Keep the title visible. Clip playback is 1.5× indoors and 2× outdoors; see source manifest. No claim of equal run duration.'

s=new(8,20,'Can geometry teach navigation without target paths?')
s.text(32,104,300,120,'Scenes support many goals.\nA traversal supplies\nonly one route.',24,INK,True)
s.image('rgb',369,98,318,178.875)
s.text(372,282,310,32,'Egocentric RGB observation',13,MUTED,align='CENTER',caption=True)
s.rect(34,280,282,68,PALE['energy'],r=6)
s.text(45,287,260,54,'Learn how a candidate path\nshould change.',20,INK,True)
s.text(35,355,650,26,'Navigation adaptation uses no demonstrated or planner-generated target trajectories.',14,MUTED)
s.narration='A scene can support many destinations, but a traversal shows only one route. We ask whether geometric objectives can instead teach a visual policy how to improve a candidate path.'
s.edit='00:08–00:20. Reveal the scene, then the question. The action-free claim concerns navigation adaptation, not the pretrained VLA backbone.'
s.sources=['GEAR-Nav Overleaf/main.tex: Introduction and Action-Free Navigation Conditions','figs/pipeline/assets/rgb.jpg']

s=new(20,28,'Geometry defines how a path should improve')
s.map(38,100,252,232,0)
s.text(43,340,245,31,'Candidate path in training geometry',12,MUTED,align='CENTER',caption=True)
terms=[('Goal reaching','Approach the destination'),('Progress','Advance along the route'),('Collision','Respect the robot footprint'),('Clearance','Separate from obstacles'),('Heading','Face toward the goal'),('Smoothness','Avoid abrupt path changes')]
for i,(a,b) in enumerate(terms):
    x=323+(i%2)*185;y=102+(i//2)*74
    s.rect(x,y,173,65,PALE['energy'],r=5)
    s.text(x+7,y+7,159,24,a,17,INK,True)
    s.text(x+7,y+32,159,28,b,12.5,INK)
s.text(325,334,360,35,'E(x; g, Φ) = Σq λq Eq(x; g, Φ)',22,INK,True,align='CENTER')
s.narration='During training, reconstructed geometry defines an energy that balances goal reaching, progress, obstacle avoidance, heading, and smoothness.'
s.edit='00:20–00:28. Reveal goal/progress, then obstacle terms, then motion regularity. Energy terms are a formulation; this slide does not claim every term has a nonzero weight in every run.'
s.sources=['GEAR-Nav Overleaf/main.tex: Geometric Trajectory Energy','figs/pipeline/assets/scene_data.npz']

s=new(28,36,'Supervise corrections, not target paths')
s.map(38,105,249,229,0,oracle=True)
s.text(40,342,250,25,'Local energy-descent directions',13,MUTED,align='CENTER',caption=True)
s.box(327,112,154,64,PALE['energy'],'Energy oracle','Training geometry')
s.box(523,112,156,64,PALE['energy'],'Oracle target','Projection-aware d*')
s.line(485,144,516,144,INK,1.7,True)
s.box(327,243,154,74,PALE['learned'],'GEAR model','Image + goal + path')
s.box(523,243,156,74,PALE['learned'],'Fit corrections','Match oracle d*')
s.line(485,277,516,277,INK,1.7,True)
s.line(600,181,600,237,ORANGE,1.7,True)
s.text(330,339,350,38,'Geometry supplies labels during training.',16,MUTED,align='CENTER')
s.narration='We query a projection-aware descent direction at the current path. The VLA learns this local correction directly, rather than fitting an optimized target trajectory.'
s.edit='00:28–00:36. Reveal the oracle arrow first; then reveal the learned model and regression connection. The plotted oracle arrows are cached directions scaled for display, not final projected displacements.'
s.sources=['GEAR-Nav Overleaf/main.tex: Projection-Aware Energy Oracle','figs/model_variant_utils.py: Scene.oracle_glyph']

s=new(36,45,'Learn on the paths the model visits')
steps=[('Visited paths','Candidate states','input'),('Oracle queries','Local correction labels','energy'),('Replay dataset','Retain earlier rounds','replay'),('Train GEAR','All retained data','learned')]
for i,(a,b,c) in enumerate(steps):
    x=32+174*i
    s.box(x,119,145,93,PALE[c],a,b)
    if i<3:s.line(x+149,165,x+168,165,INK,1.7,True)
s.line(625,218,625,246,ORANGE,1.7)
s.line(625,246,105,246,ORANGE,1.7)
s.line(105,246,105,218,ORANGE,1.7,True)
s.text(195,254,390,27,'The updated model visits the next candidate paths',15,ORANGE,True,align='CENTER')
for i,label in enumerate(['Round 1','Round 2','Round 3','…','Round r']):
    s.rect(104+i*106,305,93,32,PALE['replay'],r=4)
    s.text(109+i*106,308,83,25,label,14,INK,True,align='CENTER')
s.text(66,354,590,24,'Energy checks guard collection updates during training only.',14,MUTED,align='CENTER')
s.narration='Each correction changes the path seen by the next prediction. Dataset aggregation collects oracle labels at these visited paths and retains them across training rounds.'
s.edit='00:36–00:45. Reveal the four steps left to right, the return arrow, then the replay banks. Initial paths come from the goal-biased unicycle prior. Training collection uses projected energy backtracking; deployment removes this guard.'
s.sources=['GEAR-Nav Overleaf/main.tex: Energy-Based Dataset Aggregation']

s=new(45,55,'Deployment uses the learned field alone')
s.image('rgb',35,101,207,116.4375)
s.text(39,221,199,26,'RGB observation',13,MUTED,align='CENTER',caption=True)
s.box(35,264,207,62,PALE['goal'],'Goal + current path')
s.box(292,145,163,86,PALE['learned'],'GEAR','Predict a path correction')
s.box(508,145,177,86,PALE['neutral'],'Bounded update','Apply kinematic projection')
s.line(247,158,285,179,INK,1.7,True)
s.line(247,290,285,209,INK,1.7,True)
s.line(460,189,501,189,INK,1.7,True)
s.line(596,237,596,287,ORANGE,1.7)
s.line(596,287,374,287,ORANGE,1.7)
s.line(374,287,374,238,ORANGE,1.7,True)
s.text(429,294,160,26,'Repeat refinement',15,ORANGE,True,align='CENTER')
s.rect(292,339,393,33,PALE['input'],r=4)
s.text(301,344,375,24,'No ESDF  |  No energy query  |  No energy guard',14,INK,True,align='CENTER')
s.narration='At deployment, the same learned field repeatedly corrects a candidate path. Only the image, goal, current path, and lightweight kinematic projection are required.'
s.edit='00:45–00:55. Reveal inputs, model, bounded update, then the feedback arrow. Keep training-only geometry absent. The backbone is pretrained; the recorded example uses adapter-only training.'
s.sources=['GEAR-Nav Overleaf/main.tex: Model-Only Trajectory Refinement at Inference']

s=new(55,65,'One model, repeated path corrections')
for x,depth,label in [(35,0,'Initial path'),(265,1,'After 1 update'),(495,14,'After 14 updates')]:
    s.text(x,94,190,29,label,19,INK,True,align='CENTER')
    s.map(x,132,190,175,depth,prior=True)
s.line(232,218,251,218,INK,1.7,True);s.line(462,218,481,218,INK,1.7,True)
s.line(100,335,128,335,'#727B85',1.5,dash=True);s.text(134,324,153,26,'Initial candidate',14,MUTED)
s.line(347,335,375,335,ORANGE,2.3);s.text(381,324,229,26,'Learned refinement',14,MUTED)
s.text(34,360,652,24,'Recorded model-only rollout. ESDF shown only as a visualization reference.',12,MUTED,align='CENTER',caption=True)
s.narration='This recorded example shows the initial path, the first learned update, and the path after fourteen updates. The distance field is displayed for reference and is never queried by this rollout.'
s.edit='00:55–01:05. Reveal the panels in order. Actual cached depths are 0, 1, and 14. Do not reuse the older figure’s incorrect sixth-iteration label. This selected qualitative example does not establish a safety rate or a benchmark improvement.'
s.sources=['figs/model_simple/provenance.json','figs/pipeline/assets/scene_data.npz']

def two_video_scene(start,end,title,scene,goal,behavior):
    s=new(start,end,title,True)
    s.text(34,105,245,25,'GOAL',12,'#FFC52F',True,caption=True)
    s.text(32,141,248,91,goal,28,'#FFFFFF',True)
    s.text(35,258,236,70,behavior,17,'#CFD4DA')
    for x,key,label,color in [(319,f'gear_s{scene}','GEAR-Nav',ORANGE),(519,f'omni_s{scene}','OmniVLA','#A8CAFF')]:
        s.text(x-9,81,165,26,label,19,color,True,align='CENTER')
        s.video(key,x,115,146.25,260)
    s.text(318,376,350,15,'1× playback / representative recordings from separate trials',9.5,'#B5BDC7',align='CENTER',caption=True)
    return s

s=two_video_scene(65,90,'Person goal, intervening chair',1,'Person beyond\nthe chair','Observe the route around\nthe intervening furniture.')
s.narration='The first scenario requires approaching a person beyond an intervening chair. Compare the recorded approaches, paying attention to how the robot passes the furniture.'
s.edit='01:05–01:30. Autoplay both muted excerpts. GEAR shows source 0–32.4 s at 1.5×; OmniVLA shows source 15–50 s at 1.5×. Hold the final frames to the cut. These are representative separate trials, not synchronized experiments. The label is a scene description, not a transcription of the original goal prompt. TIC-VLA is omitted because no recording identity has been verified; NaVILA scenario-1 raw footage is not verified in the supplied folder.'
s.sources=['GEAR Scene 1/IMG_4558.MOV','Baseline Scene1/OmniVLA/IMG_3131.MOV']

s=two_video_scene(90,115,'Blue-chair goal, moving person',2,'Blue chair in\nthe lounge','Keep the moving person\nand destination in view.')
s.narration='The second scenario approaches the blue chair while a person moves through the scene. The continuous excerpt keeps the encounter and the subsequent approach visible.'
s.edit='01:30–01:55. Autoplay both muted excerpts at 1.5×. GEAR source 0–29.6 s; OmniVLA source 0–34.5 s. Separate trials and lighting conditions. Do not infer exact collisions or success from an ambiguous frame. The goal label is descriptive, not a recorded command. No TIC-VLA or unverified NaVILA raw footage is substituted.'
s.sources=['GEAR Scene 2/IMG_4552.MOV','Baseline Scene2/OnmiVLA/IMG_3150.MOV']

s=new(115,145,'Scooter goal, pedestrian encounters',True)
s.text(33,76,650,25,'Goal: the scooter beyond the pedestrians',15,'#D8DDE3')
for x,key,label,color in [(80,'gear_s3','GEAR-Nav',ORANGE),(286,'omni_s3','OmniVLA','#A8CAFF'),(492,'navila_s3','NaVILA','#CCB7EC')]:
    s.text(x-10,102,167,26,label,19,color,True,align='CENTER')
    s.video(key,x,132,136.125,242)
s.text(80,376,553,19,'1× playback / representative recordings from separate trials',9.5,'#B5BDC7',align='CENTER',caption=True)
s.narration='Outdoors, the destination is the scooter beyond the pedestrians. This longer example shows the pedestrian encounters and the final GEAR approach, alongside OmniVLA and NaVILA recordings.'
s.edit='01:55–02:25. Autoplay all three muted clips at 2×. GEAR source 0–55.4 s; OmniVLA and NaVILA source 0–58 s. GEAR ends at about 27.7 s, baselines at about 29 s. Hold to the cut. Do not interpret playback or selected intervals as comparative completion times. Do not label an exact collision without review of the full source.'
s.sources=['GEAR Scene 3/IMG_4546.MOV','Baseline Scene3/OmniVLA/IMG_3188.MOV','Baseline Scene3/Navilla/IMG_3193.MOV']

s=new(145,165,'Additional GEAR-Nav deployments',True)
for x,key,label,speed in [(80,'extra_s1','Indoor',2),(286,'extra_s2','Lounge',2),(492,'extra_s3','Outdoor',3)]:
    s.text(x-9,89,160,27,label,19,'#FFFFFF',True,align='CENTER')
    s.video(key,x,123,140.625,250)
    s.text(x,375,141,19,'1× playback',10,'#B5BDC7',align='CENTER',caption=True)
s.narration='Additional recordings show the policy operating across the indoor and outdoor settings.'
s.edit='02:25–02:45. This implements the approved additional-deployments fallback. Available navigation recordings use exact goals and are not matched to the supplied comparison-table values; they are therefore not presented as RGB-language benchmark evidence. Autoplay the three additional GEAR clips, labelled 2×, 2×, and 3×. They are qualitative excerpts, not an aggregate result.'
s.sources=['GEAR Scene 1/IMG_4560.MOV','GEAR Scene 2/IMG_4554.MOV','GEAR Scene 3/IMG_4547.MOV']

s=new(165,175,'Geometry teaches a reusable correction rule')
cards=[('Energy supervision','Local directions, without\nreference trajectory labels.','energy'),('Dataset aggregation','Retain corrections along\nmodel-induced paths.','replay'),('Model-only\nrefinement','Use RGB, the goal, and\nthe current candidate.','learned')]
for i,(title,body,role) in enumerate(cards):
    x=31+229*i;s.rect(x,126,205,180,PALE[role],r=8)
    s.text(x+13,140,178,42,f'0{i+1}',31,ORANGE,True)
    s.text(x+12,194,181,55,title,20,INK,True)
    s.text(x+12,253,181,48,body,15,INK)
s.text(37,335,650,39,'Training geometry becomes a learned path-refinement policy.',20,INK,True,align='CENTER')
s.narration='GEAR combines energy-derived corrections, trajectory-space dataset aggregation, and model-only iterative refinement. Geometry supplies supervision during adaptation and is removed from the deployed refinement loop.'
s.edit='02:45–02:55. Reveal the three contributions in order. No success percentages or collision reductions are inserted: GEAR real-world entries remain pending and supplied navigation metrics require provenance verification.'
s.sources=['GEAR-Nav Overleaf/main.tex: Contributions and Methodology','GEAR-Nav Overleaf/BASELINE_RESULTS.md']

s=new(175,180,'GEAR-Nav',True)
s.text(40,43,640,40,'GEAR-Nav',29,ORANGE,True)
s.text(39,133,640,123,'Learn corrections from geometry.\nRefine paths from vision.',35,'#FFFFFF',True)
s.rect(42,289,82,3,ORANGE)
s.text(39,315,640,35,'Energy-derived supervision. Model-only deployment.',20,'#CFD4DA')
s.narration='Learn corrections from geometry. Refine paths from vision.'
s.edit='02:55–03:00. Hold the final message. Add a public project URL only when the release URL and anonymity requirements are settled; no invented URL or author identity is shown.'


def native(e):
    k=e['kind'];oid=e['id'];p=e['page'];req=[]
    if k in ('image','video'):return []
    if k=='line':
        dx=e['x2']-e['x1'];dy=e['y2']-e['y1']
        req=[{'createLine':{'objectId':oid,'lineCategory':'STRAIGHT','elementProperties':{
            'pageObjectId':p,'size':{'width':{'magnitude':1,'unit':'PT'},'height':{'magnitude':1,'unit':'PT'}},
            'transform':{'scaleX':(dx+dy)/2,'scaleY':(dx+dy)/2,'shearX':(dx-dy)/2,'shearY':(dy-dx)/2,'translateX':e['x1'],'translateY':e['y1'],'unit':'PT'}}}},
            {'updateLineProperties':{'objectId':oid,'lineProperties':{'lineFill':{'solidFill':{'color':{'rgbColor':rgb(e['color'])}}},'weight':{'magnitude':e['width'],'unit':'PT'},'endArrow':'FILL_ARROW' if e['arrow'] else 'NONE','dashStyle':'DASH' if e['dash'] else 'SOLID'},'fields':'lineFill,weight,endArrow,dashStyle'}}]
        return req
    shape={'text':'TEXT_BOX','rect':'ROUND_RECTANGLE' if e.get('r') else 'RECTANGLE','ellipse':'ELLIPSE','star':'STAR_5'}[k]
    req.append({'createShape':{'objectId':oid,'shapeType':shape,'elementProperties':props(p,e['x'],e['y'],e['w'],e['h'])}})
    if k=='text':
        req.extend([{'updateShapeProperties':{'objectId':oid,'shapeProperties':{'outline':{'propertyState':'NOT_RENDERED'},'shapeBackgroundFill':{'propertyState':'NOT_RENDERED'},'contentAlignment':'TOP'},'fields':'outline,shapeBackgroundFill,contentAlignment'}},
                    {'insertText':{'objectId':oid,'text':e['text'],'insertionIndex':0}},
                    {'updateTextStyle':{'objectId':oid,'textRange':{'type':'ALL'},'style':{'fontFamily':FONT,'fontSize':{'magnitude':e['size'],'unit':'PT'},'foregroundColor':{'opaqueColor':{'rgbColor':rgb(e['color'])}},'bold':e['bold']},'fields':'fontFamily,fontSize,foregroundColor,bold'}},
                    {'updateParagraphStyle':{'objectId':oid,'textRange':{'type':'ALL'},'style':{'alignment':e['align'],'lineSpacing':100,'spaceAbove':{'magnitude':0,'unit':'PT'},'spaceBelow':{'magnitude':0,'unit':'PT'}},'fields':'alignment,lineSpacing,spaceAbove,spaceBelow'}}])
    else:
        fill={'propertyState':'NOT_RENDERED'} if e['fill']=='none' else {'solidFill':{'color':{'rgbColor':rgb(e['fill'])},'alpha':1}}
        outline={'propertyState':'NOT_RENDERED'} if not e.get('stroke') else {'outlineFill':{'solidFill':{'color':{'rgbColor':rgb(e['stroke'])}}},'weight':{'magnitude':.7,'unit':'PT'}}
        req.append({'updateShapeProperties':{'objectId':oid,'shapeProperties':{'shapeBackgroundFill':fill,'outline':outline},'fields':'shapeBackgroundFill,outline'}})
    return req


def write_preview(slide):
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1440" height="810" viewBox="0 0 720 405"><defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{INK}"/></marker></defs><rect width="720" height="405" fill="{slide.bg}"/>']
    for e in slide.elements:
        k=e['kind']
        if k in ('image','video'):
            path=ASSETS/(e['asset']+'.jpg')
            b64=base64.b64encode(path.read_bytes()).decode()
            parts.append(f'<image x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" xlink:href="data:image/jpeg;base64,{b64}" preserveAspectRatio="xMidYMid meet"/>')
        elif k=='text':
            anchor={'START':'start','CENTER':'middle','END':'end'}[e['align']]
            x=e['x']+3.6 if anchor=='start' else e['x']+e['w']/2 if anchor=='middle' else e['x']+e['w']-3.6
            for i,line in enumerate(e['text'].split('\n')):
                y=e['y']+3.6+e['size']*.93+i*e['size']*1.12
                parts.append(f'<text x="{x}" y="{y}" font-family="Liberation Serif" font-size="{e["size"]}" font-weight="{700 if e["bold"] else 400}" fill="{e["color"]}" text-anchor="{anchor}">{html.escape(line)}</text>')
        elif k=='line':
            parts.append(f'<line x1="{e["x1"]}" y1="{e["y1"]}" x2="{e["x2"]}" y2="{e["y2"]}" stroke="{e["color"]}" stroke-width="{e["width"]}"'+(' stroke-dasharray="4 3"' if e['dash'] else '')+(' marker-end="url(#a)"' if e['arrow'] else '')+'/>')
        elif k=='ellipse':
            parts.append(f'<ellipse cx="{e["x"]+e["w"]/2}" cy="{e["y"]+e["h"]/2}" rx="{e["w"]/2}" ry="{e["h"]/2}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}"/>')
        elif k=='star':
            pts=[]
            for j in range(10):
                a=-math.pi/2+j*math.pi/5;r=e['w']/2*(1 if j%2==0 else .42)
                pts.append(f'{e["x"]+e["w"]/2+r*math.cos(a)},{e["y"]+e["h"]/2+r*math.sin(a)}')
            parts.append(f'<polygon points="{" ".join(pts)}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}" stroke-width=".7"/>')
        else:parts.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" rx="{e.get("r",0)}" fill="{e["fill"]}" stroke="{e.get("stroke") or "none"}" stroke-width=".7"/>')
    parts.append('</svg>');svg=''.join(parts)
    folder=HERE/'local_proof';folder.mkdir(exist_ok=True)
    (folder/f'slide-{slide.num:02}.svg').write_text(svg)
    subprocess.run(['rsvg-convert','-o',str(folder/f'slide-{slide.num:02}.png'),str(folder/f'slide-{slide.num:02}.svg')],check=True)


structural=[];overlay=[];images={};videos=[]
for s in S:
    if s.num>1:structural.append({'createSlide':{'objectId':s.id,'slideLayoutReference':{'layoutId':'p12'}}})
    structural.append({'updatePageProperties':{'objectId':s.id,'pageProperties':{'pageBackgroundFill':{'solidFill':{'color':{'rgbColor':rgb(s.bg)},'alpha':1}}},'fields':'pageBackgroundFill'}})
    for e in s.elements:
        if e['kind']=='image':
            images.setdefault(e['asset'],[]).append({'createImage':{'objectId':e['id'],'url':str(ASSETS/(e['asset']+'.jpg')),'elementProperties':props(s.id,e['x'],e['y'],e['w'],e['h'])}})
        elif e['kind']=='video':videos.append(e)
        elif e['kind']=='rect' and e['fill']!='none':structural.extend(native(e))
        else:overlay.extend(native(e))
    write_preview(s)

notes=[{'slide_id':s.id,'number':s.num,'start':s.start,'end':s.end,'duration_seconds':s.end-s.start,'title':s.title,
        'narration':s.narration,'editing_notes':s.edit,'sources':s.sources,
        'layout_id':'p12' if s.num>1 else 'p2',
        'construction':'new composition; supplied slide p has no local content or media'} for s in S]
assert len(S)==13 and S[-1].end==180
assert all(a.end==b.start for a,b in zip(S,S[1:]))
for name,value in [('structural_requests',structural),('overlay_requests',overlay),('image_requests',images),('video_elements',videos),('slide_plan',notes),('canvas', [{'id':s.id,'bg':s.bg,'elements':s.elements} for s in S])]:
    (HERE/f'{name}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'slides':len(S),'seconds':180,'structural_requests':len(structural),'overlay_requests':len(overlay),'image_assets':list(images),'video_instances':len(videos)},indent=2))
