# GEAR-Nav pipeline figure proposals

Five layouts for the RA-L pipeline figure, all drawn with a schematic passage, candidate paths, and oracle directions. Click a figure to open its editable SVG.

[Compare on one sheet](five-pipelines.png) · [View one concept per page in the PDF](five-pipelines.pdf)

[![01. Same scene, two candidates with different local corrections](01-two-paths.png)](01-two-paths.svg)

[![02. Five energy terms located on one candidate path](02-energy-terms.png)](02-energy-terms.svg)

[![03. How two training rounds build the replay set](03-two-rounds.png)](03-two-rounds.svg)

[![04. Training with geometric targets and model-only deployment](04-training-deployment.png)](04-training-deployment.svg)

[![05. Anatomy of one retained training example](05-replay-example.png)](05-replay-example.svg)

To regenerate the SVGs, PNGs and PDF from the repository root, run `.venv/bin/python figs/pipeline_proposals/draw.py`. The generator uses Pillow, `rsvg-convert` and `pdfunite`.
