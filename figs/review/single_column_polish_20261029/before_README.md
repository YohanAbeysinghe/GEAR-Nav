# GEAR-Nav manuscript

Set **main.tex** as the main document in Overleaf.

The default build is the arXiv version: the paper and references,
followed by Supplementary Material. The supplement includes
`fig/gear_supplementary.pdf` and its caption from `supplementary.tex`.

The main paper uses `fig/gear_model_simple.pdf` as the one-column correction-model
and refinement figure (`fig:overview`). Its caption identifies the recorded
iterates 0, 1, and 14. The expanded architecture remains in the supplement.

The current model figure is available as a
[publication PDF](fig/gear_model_simple.pdf).

All figure filenames use the `gear_` prefix. The main paper uses the full
[six-scene comparison](fig/gear_realworld_isaacsim.pdf) in one column. Its
caption distinguishes recorded GEAR-Nav routes, reference-derived schematic
baseline overlays, and illustrative simulation views. The original
real-world-only asset remains available as `fig/gear_realworld.pdf`.
Editable masters, previews, and figure-generation scripts remain in the
workspace's local, ignored `figs/` directory.

For the RA-L submission, change `\includesupplementarytrue` to
`\includesupplementaryfalse` in the preamble of `main.tex`. This omits the
supplement and produces the paper alone. Restore `true` for arXiv.

Compile twice with pdfLaTeX to resolve figure and section references.

The simulation and real-world tables contain the OmniVLA, TIC-VLA, and
NaVILA results reported in VEGA. GEAR-Nav simulation values are supplied
separately; the GEAR-Nav real-world entries remain pending.
See [baseline result provenance](BASELINE_RESULTS.md) for source tables,
scenario coverage, units, and evaluation settings.
