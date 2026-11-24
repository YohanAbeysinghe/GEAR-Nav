"""Shared ASTAR figure style, sampled from the supplied VEGA figure assets."""
import os
from pathlib import Path
import tempfile

# Keep the standalone render command usable on hosts with read-only home caches.
os.environ['MPLCONFIGDIR'] = str(Path(tempfile.gettempdir())/'astar_figure_matplotlib')
from matplotlib import colormaps
from matplotlib.colors import ListedColormap, Normalize
import numpy as np

FONT = 'STIX Two Text'
SVG_FONT_FAMILY = FONT + ', STIXGeneral, Liberation Serif, Times New Roman, serif'
INK = '#1A1A1A'
MUTED = '#555555'
ROLE = {
    'input': ('#E6EFFD', '#7F9CC6'),
    'goal': ('#E2EFE1', '#92BA7A'),
    'energy': ('#FFE09A', '#A87518'),
    'replay': ('#EAE2EE', '#A587B2'),
    'learned': ('#FADDDC', '#C1706C'),
    'neutral': ('#F2F2F2', '#777777'),
}
# Most role colors sit halfway between the pale and original palettes.
# Energy/oracle highlights use richer amber for clear separation on paper.
# A slightly deeper neutral gray separates frozen modules from the white page.
ROLE_BORDER_WIDTH = 2.4
STAGE_BORDER_WIDTH = 2.6
ENERGY_HEADER_FILL = '#FFF0CC'
ENERGY_FRAME_BORDER_WIDTH = 3.6
FIGURE_RULE_COLOR = '#8C929A'
FIGURE_RULE_WIDTH = 2.6
REFINED_PATH_WIDTH = 5.2
REFINED_PATH_OUTLINE_WIDTH = 8.2
# Colors encode scientific role; flame/snowflake symbols encode parameter status.
ROLE_LABELS = {
    'input': 'Inputs / Paths', 'goal': 'Goals', 'energy': 'Energy / Oracle',
    'replay': 'Replay', 'learned': 'ASTAR', 'neutral': 'Backbone / Fixed Ops',
}
# White surfaces keep broad energy panels light; gold is reserved for emphasis.
OUTLINE_SURFACE = '#FFFFFF'
LOSS_STYLE = ('#FBE7E5', ROLE['learned'][1])
COLORS = {0: '#888888', 1: '#D88938', 3: '#D88938', 6: '#D88938', 7: '#E66F21', 14: '#F34B0B'}
# The requested middle-panel label is retained independently of its path source.
MODEL_REFINEMENT_DEPTHS = (0, 6, 14)
MODEL_REFINEMENT_LABEL_DEPTHS = (0, 6, 14)
WAYPOINT_FILL = '#FFC52F'
GOAL_FILL = '#FFC52F'
ESDF_CMAP = colormaps['coolwarm']
ESDF_NORM = Normalize(vmin=-3.0, vmax=3.0, clip=True)

# Teaser-specific emphasis retains the shared coolwarm scale and orange/yellow
# final path. Other figures continue to use the original palette above.
TEASER_STAGE_COLORS = {
    'initial': '#717C89', 'early': '#2C7FB8',
    'intermediate': '#7956A6', 'refined': '#F34B0B',
}
TEASER_CAMERA_PATH_WIDTH_M = {
    'initial': .075, 'early': .075, 'intermediate': .075, 'refined': .105,
}
TEASER_CAMERA_HALO_EXTRA_M = .04
TEASER_ESDF_WHITE_BLEND = .16
_teaser_rgba = ESDF_CMAP(np.linspace(0., 1., 256))
_teaser_rgba[:, :3] = (1-TEASER_ESDF_WHITE_BLEND)*_teaser_rgba[:, :3]+TEASER_ESDF_WHITE_BLEND
TEASER_ESDF_CMAP = ListedColormap(_teaser_rgba, name='coolwarm_white16')
TEASER_ESDF_CONTOUR_COLOR = '#4F5865'
TEASER_ESDF_CONTOUR_WIDTH = 1.1
