# Two planning decisions on held-out video

[Camera views and ESDF maps (PDF)](camera_and_clearance.pdf) · [Preview (PNG)](camera_and_clearance.png) · [Editable figure (SVG)](camera_and_clearance.svg)

| Clip | Source video time | Frame | Sampled goal index | Straight minimum | GEAR-Nav minimum | Forward position of negative minimum |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Spain_1 | [1:19:55](https://www.youtube.com/watch?v=3oe6tIoEeKg&t=4795s) | 000924 | 0 | −0.320 m | +0.192 m | 6.03 m |
| Amsterdam_1 | [1:31:35](https://www.youtube.com/watch?v=ABuu-odtMOk&t=5495s) | 000884 | 7 | +0.266 m | −0.365 m | 10.07 m |

Each column pairs a source frame with its footprint-clearance map. The straight path points toward the sampled goal and ends the same distance from it as the 14-update prediction. In the daylight plaza the straight path crosses the negative-clearance boundary on camera right. On the Amsterdam street the learned path enters a negative-clearance region near its endpoint. The dotted line marks the start of scoring at 2 m forward. Each black cross marks the lowest-clearance sample on the flagged path. The mapping configuration treats unknown space as occupied, so these measurements alone cannot identify a particular obstacle or establish a physical collision.

## Selection and reconstruction

We inspected the paired camera views and path maps for all 48 observations where exactly one path had negative clearance among the 278 scored frame–goal pairs. Of those 48, 35 flagged the straight path and 13 flagged GEAR-Nav. The two examples illustrate opposite outcomes with a visible path separation, minima on opposite sides of zero, and a negative minimum well beyond the 2 m scoring cutoff. The median paired improvement over all 278 pairs was 0.005 m.

Run `.venv/bin/python figs/extra_page_review/test_frames/render.py` from the workspace root. The renderer checks membership in the evaluation split and exclusion from the training split, loads checkpoint 57,500 model-only predictions from `eval/best_model/model_paths_checkpoint57500.npz`, matches the sampled metric goal, and resolves the image and ESDF from each frame's metadata under `../data/<clip>/`. It samples each path segment at 20 equal increments, bilinearly interpolates signed distances after subtracting the 0.50 m footprint radius, and verifies both minima against the recorded evaluation values.
