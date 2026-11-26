# Six-scene figure for one paper column

[PDF](gear_realworld_isaacsim.pdf) · [preview](gear_realworld_isaacsim.png)
· [editable SVG](gear_realworld_isaacsim.svg)

The complete six-scene figure is composed at **3.4 × 2.75 inches**, with
labels and method legend at **7.14 pt** or larger. The previous full-width
export shrank to approximately 3.7 pt when included in one column.

The three real-world photographs show 70% of their original image height,
restoring more robot body and scene context than the earlier 50% crops.
The Isaac Sim images already show their complete 16:9 frames. All 12 source
route segments, control points, nine reference failure endpoints, and three
real-world goal locations are retained. Orange GEAR-Nav paths are emphasized
with a slightly thicker stroke and a bold legend entry. The four method
labels share a single compact row. The caption explains the stars and crosses,
avoiding two additional entries in the legend.

All three simulation photographs retain their full 16:9 framing and the same
goal annotations. These are illustrative separate oracle-goal recordings,
not matched to the aggregate evaluation values. Baseline real-world routes
remain schematic reference transfers, not new measured tracks.

Only the photographs are raster; labels, paths, stars, crosses, and arrows are
editable SVG elements. Source hashes, image crops, marker counts, and output
hashes are in `provenance.json`.

```sh
.venv/bin/python figs/realworld_isaacsim/single_column/build.py
```

The paper uses this PDF as `fig/gear_realworld_isaacsim.pdf`. The original
full-width local master and its existing Figma copy remain separate artifacts.
No Figma update was requested for this revision. All local source assets remain
under ignored `/figs/` and must not be force-added to Git.
