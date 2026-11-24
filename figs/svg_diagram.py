"""Small editable SVG primitives shared by the local publication figures.

Only camera pixels and sampled ESDF backgrounds are rasterized. Paths, labels,
module boundaries, token rows, and connectors remain separate SVG objects.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from functools import lru_cache
from io import BytesIO
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from figure_style import (COLORS, ESDF_CMAP, ESDF_NORM, INK, MUTED, ROLE, ROLE_LABELS,
                          OUTLINE_SURFACE, SVG_FONT_FAMILY, WAYPOINT_FILL,
                          ROLE_BORDER_WIDTH, REFINED_PATH_WIDTH, REFINED_PATH_OUTLINE_WIDTH,
                          FIGURE_RULE_COLOR, FIGURE_RULE_WIDTH)

import matplotlib
matplotlib.use('Agg')
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
import numpy as np
from PIL import Image, ImageFont
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
INKSCAPE = 'http://www.inkscape.org/namespaces/inkscape'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)
ET.register_namespace('inkscape', INKSCAPE)
matplotlib.rcParams.update({'mathtext.fontset': 'stix', 'savefig.transparent': True})


def export_pdf(sources, output, width_mm, height_mm):
    """Preserve vectors while normalizing old rsvg's integer-point page sizes."""
    env={**os.environ, 'FONTCONFIG_FILE':str(HERE/'fontconfig.conf')}
    with tempfile.TemporaryDirectory(prefix='astar-vector-pdf-') as temporary:
        intermediate=Path(temporary)/'render.pdf'
        subprocess.run(['rsvg-convert','-d','72','-p','72','-f','pdf','-o',str(intermediate),
                        *map(str,sources)],check=True,env=env)
        subprocess.run(['gs','-q','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite',
                        '-dCompatibilityLevel=1.5','-dAutoRotatePages=/None',
                        '-dFIXEDMEDIA','-dPDFFitPage','-dEmbedAllFonts=true',
                        f'-dDEVICEWIDTHPOINTS={width_mm/25.4*72:.9f}',
                        f'-dDEVICEHEIGHTPOINTS={height_mm/25.4*72:.9f}',
                        f'-sOutputFile={output}',str(intermediate)],check=True,env=env)


@lru_cache(maxsize=32)
def measure_font(size, bold=False):
    filename = 'LiberationSerif-Bold.ttf' if bold else 'LiberationSerif-Regular.ttf'
    return ImageFont.truetype('/usr/share/fonts/liberation-serif/' + filename, round(size))


class Diagram:
    def __init__(self, width, height, title, description, width_mm=None):
        self.width, self.height = width, height
        self.minimum_text_size = 34 if width == 2100 and width_mm is None else 0
        width_mm = 178 * width / 2100 if width_mm is None else width_mm
        self.root = ET.Element(f'{{{SVG}}}svg', {
            'width': f'{width_mm:.6f}mm', 'height': f'{width_mm*height/width:.6f}mm',
            'viewBox': f'0 0 {width} {height}',
        })
        ET.SubElement(self.root, f'{{{SVG}}}title').text = title
        ET.SubElement(self.root, f'{{{SVG}}}desc').text = description
        self.parent = self.root
        self.equations = {}
        self.label_bounds = []
        self._count = 0
        self.rect(0, 0, width, height, stroke='none', radius=0)

    def el(self, tag, **attrs):
        return ET.SubElement(self.parent, f'{{{SVG}}}{tag}', {k.replace('_', '-'): str(v) for k, v in attrs.items()})

    @contextmanager
    def layer(self, label, ident):
        previous = self.parent
        self.parent = ET.SubElement(self.root, f'{{{SVG}}}g', {
            'id': ident, f'{{{INKSCAPE}}}groupmode': 'layer', f'{{{INKSCAPE}}}label': label,
        })
        try:
            yield
        finally:
            self.parent = previous

    def rect(self, x, y, w, h, fill='white', stroke='#AAAAAA', radius=10, sw=2):
        return self.el('rect', x=x, y=y, width=w, height=h, rx=radius, fill=fill, stroke=stroke, stroke_width=sw)

    def role_box(self, x, y, w, h, role, radius=8, sw=ROLE_BORDER_WIDTH, surface='filled'):
        assert surface in {'filled','outline'}
        fill,border=ROLE[role]
        node = self.rect(x,y,w,h,fill if surface=='filled' else OUTLINE_SURFACE,border,radius=radius,sw=sw)
        node.set('data-role', role)
        node.set('data-surface',surface)
        return node

    def role_key(self, y):
        """One shared categorical key, distinct from the quantitative ESDF key."""
        with self.layer('Color roles shared by both figures', 'color-roles'):
            for x, role in zip((210, 535, 765, 1145, 1395, 1625), ROLE):
                self.role_box(x, y, 30, 23, role, radius=3, sw=1.4)
                self.text(x+43, y+24, ROLE_LABELS[role], 30)
            rule = self.line([(40, y+39), (self.width-40, y+39)],
                             FIGURE_RULE_COLOR, FIGURE_RULE_WIDTH)
            rule.set('data-kind', 'figure-bottom-rule')

    def text(self, x, y, label, size=34, bold=False, anchor='start', color=INK, max_width=None):
        # At the IEEE paper's seven-inch text width, 34 design units are 8.16 pt.
        # Proof-sheet annotations use a different canvas and retain their sizes.
        size = max(size, self.minimum_text_size)
        width = measure_font(size, bold).getlength(label)
        if max_width is not None and width > max_width:
            raise ValueError(f'Text exceeds {max_width}px ({width:.1f}px): {label}')
        left = x - (width if anchor == 'end' else width / 2 if anchor == 'middle' else 0)
        # Use actual glyph ink bounds rather than a full em box: the latter
        # falsely reports overlaps on ordinary multi-line text.
        ink = measure_font(size, bold).getbbox(label, anchor='ls')
        bounds = [left + ink[0], y + ink[1], left + ink[2], y + ink[3]]
        if bounds[0] < -1 or bounds[2] > self.width + 1 or bounds[1] < -1 or bounds[3] > self.height + 1:
            raise ValueError(f'Text extends outside the canvas: {label}')
        self.label_bounds.append({'text': label, 'bounds': bounds, 'font_size': size})
        node = self.el('text', x=x, y=y, font_family=SVG_FONT_FAMILY, font_size=size,
                       font_weight='bold' if bold else 'normal', text_anchor=anchor, fill=color)
        node.text = label
        return node

    def lines(self, x, y, labels, size=34, gap=40, **kwargs):
        for index, label in enumerate(labels):
            self.text(x, y + gap * index, label, size, **kwargs)

    def line(self, points, color=INK, width=3, dash=None):
        attrs = dict(points=' '.join(f'{x:.9g},{y:.9g}' for x, y in points), fill='none',
                     stroke=color, stroke_width=width, stroke_linecap='round', stroke_linejoin='round')
        if dash:
            attrs['stroke_dasharray'] = dash
        return self.el('polyline', **attrs)

    def arrow(self, points, color=INK, width=3, dash=None, head=12):
        node = self.line(points, color, width, dash)
        (px, py), (x, y) = points[-2:]
        angle = math.atan2(y-py, x-px)
        dx, dy = head*math.cos(angle), head*math.sin(angle)
        nx, ny = -head*.42*math.sin(angle), head*.42*math.cos(angle)
        self.el('polygon', points=f'{x},{y} {x-dx+nx},{y-dy+ny} {x-dx-nx},{y-dy-ny}', fill=color)
        return node

    def circle(self, x, y, r, fill='white', stroke=INK, sw=2):
        return self.el('circle', cx=x, cy=y, r=r, fill=fill, stroke=stroke, stroke_width=sw)

    def star(self, x, y, r=12):
        points=[]
        for index in range(10):
            angle=-math.pi/2+index*math.pi/5
            radius=r if index % 2 == 0 else r*.43
            points.append(f'{x+radius*math.cos(angle)},{y+radius*math.sin(angle)}')
        self.el('polygon', points=' '.join(points), fill=WAYPOINT_FILL, stroke=INK, stroke_width=1.7)

    def badge(self, x, y, trainable=False, r=15):
        """VEGA-inspired flame/snowflake status icons, entirely editable vectors."""
        parent=self.parent
        self.parent=self.el('g',transform=f'translate({x-r},{y-r}) scale({2*r/32})',
                            **{'data-parameter-status':'trainable' if trainable else 'frozen',
                               'data-status-symbol':'flame' if trainable else 'snowflake'})
        if trainable:
            self.el('path',d='M17 1 C18 8 11 11 12 17 C8 15 7 11 8 8 '
                    'C3 13 1 18 3 24 C6 33 26 33 29 24 C32 16 26 11 25 5 '
                    'C25 12 20 14 22 20 C15 17 22 9 17 1 Z',
                    fill='#F05A24',stroke='#BD351F',stroke_width=1.1,stroke_linejoin='round')
            self.el('path',d='M17 13 C18 18 11 20 12 24 C12 27 14 29 18 29 '
                    'C24 29 25 24 23 20 C22 24 18 23 19 20 C20 17 18 15 17 13 Z',
                    fill='#FFD23F')
        else:
            commands=[]
            for index in range(6):
                angle=index*math.pi/3
                def p(dx,dy):
                    return f'{16+dx*math.cos(angle)-dy*math.sin(angle):.5f},{16+dx*math.sin(angle)+dy*math.cos(angle):.5f}'
                commands.extend([f'M{p(0,0)} L{p(0,-13)}',
                                 f'M{p(-4.5,-10)} L{p(0,-6)} L{p(4.5,-10)}'])
            for color,width in [('#397C98',3.8),('#B3E7F5',2.2)]:
                self.el('path',d=' '.join(commands),fill='none',stroke=color,
                        stroke_width=width,stroke_linecap='round',stroke_linejoin='round')
        node=self.parent
        self.parent=parent
        return node

    def image(self, image, x, y, w, h, fit='xMidYMid meet'):
        if isinstance(image, (str, Path)):
            raw=Path(image).read_bytes()
            mime='image/jpeg' if Path(image).suffix.lower() in ('.jpg', '.jpeg') else 'image/png'
        else:
            stream=BytesIO()
            image.save(stream, format='PNG')
            raw, mime=stream.getvalue(), 'image/png'
        return self.el('image', x=x, y=y, width=w, height=h, preserveAspectRatio=fit,
                       **{f'{{{XLINK}}}href':f'data:{mime};base64,'+base64.b64encode(raw).decode()})

    def formula(self, x, y, w, h, expression, name, *, font_size=None):
        """Place vector math; an explicit font size keeps related equations uniform."""
        self.equations[name] = expression
        stream=BytesIO()
        math_to_image(expression, stream, prop=FontProperties(family='STIXGeneral', size=34), format='svg', color=INK)
        node=ET.fromstring(stream.getvalue())
        if font_size is not None:
            bounds = [float(value) for value in node.get('viewBox').split()]
            actual_w, actual_h = bounds[2] * font_size / 34, bounds[3] * font_size / 34
            if actual_w > w or actual_h > h:
                raise ValueError(f'Equation exceeds its box at {font_size} units: {name} ({actual_w:.1f} × {actual_h:.1f})')
            node.set('data-equation-box', json.dumps([x, y, w, h]))
            node.set('data-equation-font-size', str(font_size))
            x, y = x + (w-actual_w)/2, y + (h-actual_h)/2
            w, h = actual_w, actual_h
        node.set('x', str(x)); node.set('y', str(y)); node.set('width', str(w)); node.set('height', str(h))
        node.set('preserveAspectRatio', 'xMidYMid meet')
        node.set('id', name)
        ids={n.get('id'):f'{name}_{n.get("id")}' for n in node.iter() if n.get('id')}
        for n in node.iter():
            for key, value in list(n.attrib.items()):
                if key=='id':
                    n.set(key, ids[value])
                else:
                    for old, new in ids.items():
                        value=value.replace(f'url(#{old})', f'url(#{new})')
                        if value==f'#{old}':value=f'#{new}'
                    n.set(key, value)
        self.parent.append(node)

    def tokens(self, x, y, w, role='input', count=5, label=None, ellipsis=True):
        parent=self.parent
        self.parent=self.el('g',**{'data-kind':'token-strip','data-drawn-token-count':count})
        fill, border = ROLE[role]
        self.rect(x, y, w, 42, 'white', border, 4, 1.8)
        token=27
        for index in range(count):
            self.rect(x+12+index*39, y+7, token, token, fill, border, 2, 1.5)
        if label:
            self.text(x+w-12, y+32, label, 30, anchor='end')
        elif ellipsis:
            self.text(x+w-18, y+30, '…', 32, anchor='end')
        group=self.parent
        self.parent=parent
        return group

    def export(self, svg, png_width=2520):
        svg=Path(svg)
        ET.indent(self.root, space='  ')
        ET.ElementTree(self.root).write(svg, encoding='utf-8', xml_declaration=True)
        env={**os.environ, 'FONTCONFIG_FILE':str(HERE/'fontconfig.conf')}
        width_mm=float(self.root.get('width').removesuffix('mm'))
        height_mm=float(self.root.get('height').removesuffix('mm'))
        export_pdf([svg],svg.with_suffix('.pdf'),width_mm,height_mm)
        subprocess.run(['rsvg-convert','-w',str(png_width),'-o',str(svg.with_suffix('.png')),str(svg)],check=True,env=env)
        if self.equations:
            (svg.parent/'equations.json').write_text(json.dumps(self.equations, indent=2)+'\n')


class RecordedScene:
    """Read-only access to the committed qualitative capture."""
    def __init__(self):
        with np.load(HERE/'pipeline/assets/scene_data.npz') as data:
            self.esdf=data['esdf'].copy()
            self.goal=data['goal'].copy()
            self.paths={depth:data[f'path_{depth}'].copy() for depth in (0,1,3,7,14)}
            self.direction=data['oracle_direction'].copy()
        self.rgb=HERE/'pipeline/assets/rgb.jpg'
        # Supplement the immutable original capture with an actual sixth iterate.
        supplement = HERE/'model/plots/sixth_iteration.npz'
        if supplement.exists():
            with np.load(supplement) as data:
                self.paths[6] = data['path_6'].copy()

    def draw(self, diagram, x, y, w, h, depth=0, background=True, oracle=False, scale_bar=False, goal=True,
             reference_prior=False, all_waypoints=False, path_outline=False):
        # The same metric aspect ratio is used for all panels of a given size.
        xlo,xhi=-.15,5.8
        ymid=-.5
        yspan=(xhi-xlo)*h/w
        ylo,yhi=ymid-yspan/2,ymid+yspan/2
        def pt(point):
            return (x+(point[0]-xlo)/(xhi-xlo)*w, y+h-(point[1]-ylo)/(yhi-ylo)*h)
        if background:
            rows=(np.arange(round(h))[::-1]+.5)/h*(yhi-ylo)+ylo
            cols=(np.arange(round(w))+.5)/w*(xhi-xlo)+xlo
            xx,yy=np.meshgrid(cols,rows)
            field=map_coordinates(self.esdf, [(yy+10)/.02-.5,xx/.02-.5], order=1, mode='nearest')
            raster=Image.fromarray(np.uint8(ESDF_CMAP(ESDF_NORM(field))*255))
            diagram.image(raster,x,y,w,h)
        else:
            diagram.rect(x,y,w,h,'white','none',0)
        diagram.rect(x,y,w,h,'none','#AAAAAA' if background else 'none',0,1.4)
        if reference_prior and depth>0:
            reference=diagram.line([pt(point) for point in self.paths[0]],COLORS[0],2.7,'8,6')
            reference.set('opacity','0.65')
            reference.set('data-kind','recorded-prior-reference')
            reference.set('data-capture-depth','0')
            reference.set('data-metric-bounds',json.dumps([xlo,xhi,ylo,yhi]))
            reference.set('data-display-viewport',json.dumps([x,y,w,h]))
        path_node = self._polyline(diagram, self.paths[depth], pt, depth, oracle, all_waypoints,path_outline)
        path_node.set('data-kind', 'recorded-path')
        path_node.set('data-capture-depth', str(depth))
        path_node.set('data-metric-bounds', json.dumps([xlo,xhi,ylo,yhi]))
        path_node.set('data-display-viewport', json.dumps([x,y,w,h]))
        if oracle:
            for index in (3,6,9,12,15):
                before=self.paths[0][index]
                after=before+.65*self.direction[index]
                arrow = diagram.arrow([pt(before),pt(after)],COLORS[14],2.6,head=9)
                arrow.set('data-kind','oracle-direction')
                arrow.set('data-waypoint-index',str(index))
                arrow.set('data-visual-scale-m','0.65')
        diagram.circle(*pt([0,0]),5.6,'white',INK,2)
        if goal:
            diagram.star(*pt(self.goal),12)
        if scale_bar:
            px,py=pt([.15,ylo])
            ex,_=pt([1.15,ylo])
            diagram.line([(px,y+h+22),(ex,y+h+22)],width=2.8)
            diagram.text(ex+12,y+h+32,'1 m',30)
        return [xlo,xhi,ylo,yhi]

    def path_glyph(self, diagram, x, y, w, h, all_waypoints=False):
        """A spatial input glyph using the unchanged recorded prior, without ESDF."""
        path=self.paths[0]
        lo,hi=path.min(axis=0),path.max(axis=0)
        scale=min((w-16)/(hi[0]-lo[0]),(h-16)/(hi[1]-lo[1]))
        center=(lo+hi)/2
        xlo,xhi=center[0]-w/2/scale,center[0]+w/2/scale
        ylo,yhi=center[1]-h/2/scale,center[1]+h/2/scale
        def pt(point):
            return x+w/2+(point[0]-center[0])*scale,y+h/2-(point[1]-center[1])*scale
        node=self._polyline(diagram,path,pt,0,False,all_waypoints)
        node.set('data-kind','recorded-input-glyph')
        node.set('data-capture-depth','0')
        node.set('data-metric-bounds',json.dumps([xlo,xhi,ylo,yhi]))
        node.set('data-display-viewport',json.dumps([x,y,w,h]))
        diagram.circle(*pt(path[0]),5.6,'white',INK,2)

    @staticmethod
    def color_key(diagram, x, y, w=170):
        """Compact vector key for the shared signed-distance normalization."""
        parent = diagram.parent
        diagram.parent = diagram.el('g', **{'data-kind': 'esdf-color-key',
            'data-range-m': '[-3, 3]', 'data-quantity': 'signed-obstacle-distance'})
        for index in range(64):
            rgb=ESDF_CMAP(index/63)[:3]
            fill='#'+''.join(f'{round(channel*255):02x}' for channel in rgb)
            diagram.rect(x+w*index/64,y,w/64+.1,14,fill,'none',0)
        diagram.rect(x,y,w,14,'none','#AAAAAA',0,1)
        for fraction,label in [(0,'−3'),(.5,'0'),(1,'+3')]:
            px=x+fraction*w
            diagram.line([(px,y+14),(px,y+20)],MUTED,1.5)
            diagram.text(px,y+49,label,30,anchor='middle',color=MUTED)
        diagram.parent = parent

    @staticmethod
    def _polyline(diagram, path, pt, depth, oracle, all_waypoints=False, path_outline=False):
        display_points=[pt(point) for point in path]
        if path_outline and depth>0:
            halo=diagram.line(display_points,'white',REFINED_PATH_OUTLINE_WIDTH)
            halo.set('data-kind','recorded-path-outline')
            halo.set('data-capture-depth',str(depth))
        node = diagram.line(display_points,COLORS[depth],REFINED_PATH_WIDTH if depth else 3.5,
                            '8,6' if depth==0 else None)
        if depth>0 or oracle or all_waypoints:
            stride=1 if all_waypoints else 2
            for index in range(0,len(path),stride):
                marker=diagram.circle(*pt(path[index]),3.4 if all_waypoints else 4.7,
                                      WAYPOINT_FILL if depth else COLORS[0],COLORS[depth],1.6)
                marker.set('data-kind','recorded-waypoint')
                marker.set('data-capture-depth',str(depth))
                marker.set('data-waypoint-index',str(index))
        return node
