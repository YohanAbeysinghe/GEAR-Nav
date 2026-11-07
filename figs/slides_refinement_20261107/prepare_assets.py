"""Render diagram panels and representative posters from established local sources."""
from pathlib import Path
import subprocess

import imageio_ffmpeg
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
ASSETS=HERE/'assets'
ASSETS.mkdir(exist_ok=True)
for name,pdf in [('pipeline-full','gear_pipeline'),('model-full','gear_model_simple')]:
    subprocess.run(['pdftoppm','-scale-to','2200','-singlefile','-png',str(ROOT/'GEAR-Nav Overleaf/fig'/f'{pdf}.pdf'),str(ASSETS/name)],check=True)
    with Image.open(ASSETS/f'{name}.png') as im:
        w,h=im.size
        if name=='pipeline-full':
            im.crop((int(.015*w),int(.044*h),int(.985*w),int(.545*h))).save(ASSETS/'pipeline-training.png')
            im.crop((int(.015*w),int(.545*h),int(.985*w),int(.995*h))).save(ASSETS/'pipeline-energy.png')
        else:
            im.crop((0,0,w,int(.635*h))).save(ASSETS/'model-architecture.png')

for filename,key,seconds,expected_bytes in [('IMG_3134.MOV','vega-navila',6,63289883),('IMG_3132.MOV','vega-ticvla',2,66309682)]:
    source=ROOT/'figs/realworld_exp/Scene 1/OmniVLA'/filename
    assert source.stat().st_size==expected_bytes
    # Preserve the 9:16 source aspect ratio. Native Slides embeds the originals.
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-ss',str(seconds),'-i',str(source),'-frames:v','1','-vf','scale=432:768',str(ASSETS/f'{key}.jpg')],check=True)
