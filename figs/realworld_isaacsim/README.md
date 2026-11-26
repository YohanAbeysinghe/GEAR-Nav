# Combined real-world and navigation figure

The current paper uses the [single-column version](single_column/README.md),
with all six scenes and labels sized at 7.14 pt. The original full-width
master and its existing Figma copy are documented below.

[PDF](gear_realworld_isaacsim.pdf) · [preview](gear_realworld_isaacsim.png)
· [editable SVG master](gear_realworld_isaacsim.svg)
· [prepared Figma import](figma_import.svg)

The figure uses an aligned three-column grid with a larger real-world row
and a shallow navigation row. GEAR-Nav appears first in a pale-orange legend
highlight; its orange routes are drawn last and slightly thicker than the
baseline curves. Gold stars consistently mark all six goals. Numerical
evaluations remain in the existing paper table.

The export is 7.00 × 4.62 inches before an external caption and float spacing.
Labels are at least 7.68 pt at this width. It is intended for full text width.

## Scientific scope and preserved sources

Real-world photographs and route control points come from
`../realworld_paths/annotations.json`. All existing route coordinates,
failure endpoints, and goal locations are preserved exactly. The lower
foreground is cropped more tightly in this new composition to emphasize
navigation; the original real-world masters and the paper figure are unchanged.
Every route control point remains within its new image viewport.

The real-world baseline curves are schematic transfers from VEGA's qualitative
comparison. GEAR-Nav routes summarize selected recordings; none of these
curves is presented as a calibrated track. The navigation photos and manually
marked target people come from the previously approved scene strip and its
recorded instructions. They illustrate separate runs, and do not establish
a relationship to the current aggregate evaluation values.

`caption.tex` records this scope. `provenance.json` contains source hashes,
display crops, and verification that the paper and original masters did not
change. No measurements, statistical claims, or navigation paths are added.

## Editing and delivery

Only the six photographs are raster. Labels, curves, arrowheads, stars,
crosses, and section bands remain editable SVG elements.

```sh
.venv/bin/python figs/realworld_isaacsim/build.py
```

All files remain local in the ignored `figs/` directory. Do not force-add them
to Git. Nothing has been copied into or inserted into Overleaf.

The combined figure is now placed and visually verified in the
[GEAR-Realworld-Issacsim file](https://www.figma.com/design/3RjwsUydxXrFOknU4HhcTy/GEAR-Realworld-Issacsim?node-id=3-8),
page `0:1`, preserving frame `3:8` and its position `(200, 0)`.
The 2100 × 1386 canvas contains 14 editable STIX Two Text labels, six
photographs, and 60 vector nodes. The existing real-world-only content was
replaced by the complete combined layout.

[Cloud preview](figma_sync/figma_preview.png) and
[delivery record](figma_sync/delivery.json) document the final passing visual
check. A frame-resize correction restored the approved geometry after the
initial import; the second screenshot is the final verified version.
No further Figma calls were made after that visual check passed.
