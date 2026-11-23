# GEAR-Nav figures for Canva

## Open a figure

1. Unzip `GEAR-Nav-Canva.zip` on your computer.
2. In a desktop browser, drag the desired `.pptx` from **Canva import** onto the Canva homepage. Each file opens as a separate design with the proportions of its original figure. [Canva’s PowerPoint import guide](https://www.canva.com/help/powerpoint-import/)
3. Open the imported design and double-click a label to edit its text. Select a trajectory, waypoint, panel, or photograph to move or recolor the drawing or replace the image. The matching PNG in **Previews** shows the reference layout.

| File | Figure |
| --- | --- |
| 01-Pipeline | Inputs, energy-based dataset aggregation, full-dataset training, and the energy oracle |
| 02-Original-Model | Original full-width model and iterative refinement |
| 03-Paper-Model | Compact model diagram used in the paper |
| 04-Teaser | Four scenes with camera views, ESDF maps, and the GEAR-Nav trajectory key |
| 05-Supplementary | Expanded architecture, supervision, and refinement at iterations 0, 6, and 14 |
| 06-Real-World-and-Isaac-Sim | Three physical scenarios and three simulation environments |

## Edit individual elements

**Labels and shapes.** The PowerPoint files contain text boxes, native shapes, vector paths, and embedded pictures. Select a photo or distance map as a single picture. Its overlaid trajectories and waypoint markers can be selected separately. The files were rendered and checked locally. Canva’s importer can substitute a font or regroup drawing elements.

**Equations.** Each formula is a single movable vector drawing. To change a symbol or expression, copy its LaTeX from the corresponding `.tex` file in **Equation sources**. Each expression is labeled with the equation’s name in the PowerPoint selection pane.

**Fonts.** The labels use STIX Two Text. Regular and Bold are included with their license in **Fonts**. If Canva substitutes the typeface, choose STIX Two Text in the font picker or upload the included fonts if your account supports custom fonts. [Canva’s font upload requirements](https://www.canva.com/help/upload-formats-requirements/) · [STIX font project](https://github.com/stipub/stixfonts/tree/v2.13b171)

**Curve control points and source images.** Open a drawing from **Editable SVG** in Inkscape to change individual curve control points. Each SVG contains its images, labels, and vector layers. **Images** also provides the separate picture assets and the teaser’s depth masks. **Vector PDF** provides a second import format and a print-quality reference. [Canva’s PDF import guide](https://www.canva.com/help/import-and-edit-pdfs-canva/)

`manifest.json` records the source files, original Figma frame links, saved layout adjustments, object counts, and local verification results.
