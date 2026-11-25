# Real-world navigation and Isaac Sim environments

[![Three real-world navigation scenarios above the hospital lobby, hospital corridor and warehouse in Isaac Sim.](gear_realworld_isaacsim.png)](gear_realworld_isaacsim.svg)

[Editable SVG](gear_realworld_isaacsim.svg) · [Single-column PDF](gear_realworld_isaacsim.pdf) · [Editable PowerPoint for Canva](gear_realworld_isaacsim.pptx)

The figure fits a 3.4-inch paper column. It uses 9 pt STIX Two Text headings, 7.44 pt scene captions, and a 7.2 pt shared legend. GEAR-Nav has a solid orange route. The blue dots, magenta dashes, and violet lines distinguish the three baselines.

In panel (a), GEAR-Nav routes summarize selected recordings. The baseline routes are schematic adaptations of VEGA’s qualitative comparison. Crosses mark reference failures. Panel (b) shows three separate illustrative oracle-goal runs. Gold stars mark the goals in both panels.

The source is `Editable SVG/06-Real-World-and-Isaac-Sim.svg` in the local figure kit. Each photograph and its annotations move together. The SVG metadata records the source checksum and font license. The PowerPoint contains six photographs, 14 editable labels, and 56 vector shapes. [Source kit](../../canva/GEAR-Nav-Canva.zip)

Build the SVG, PDF, and PNG from the repository root. Add `--pptx` to generate the PowerPoint with the existing Canva exporter and its dependencies. [Exporter](../../canva/editable_pptx.py) · [Dependencies](../../canva/build_kit.py)

```sh
.venv/bin/python figs/realworld_isaacsim/styled/build.py
```
