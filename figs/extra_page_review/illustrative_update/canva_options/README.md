# Qualitative waypoint corrections

Pages 1–3 of [5 Qualitative in Canva](https://www.canva.com/design/DAHcCMlYgkE/edit) use one recorded Amsterdam frame and its matching ESDF. Page 4 holds the initial draft. [Side-by-side preview](comparison.jpg) · [Three-page print PDF](qualitative_options.pdf)

| Page | Editable master | What to look for |
| --- | --- | --- |
| 1 | [Shared waypoint](shared_waypoint.svg) | Two corrections start at the same yellow waypoint beside the foreground bollard. |
| 2 | [Matched paths](matched_paths.svg) | The orange and dashed teal proposals use identical map crops, candidate paths, and scales. |
| 3 | [Two waypoints](two_waypoints.svg) | The two directions nearly coincide on approach and separate near the bollard. |

The camera and distance samples come from held-out clip `Amsterdam_3`, frame `000657`. The open ring marks the same recorded bollard surface in the two views. Map colors show signed distance minus the 0.50 m footprint radius, interpolated for display on one blue-to-red scale over −1.1 to +1.1 m. The candidate, proposals and corrections are hand-drawn. [Capture and source hashes](../scene.json) · [Candidate and oracle drawing](../artwork.json) · [GEAR drawing](gear_sketch.json)

The [Canva import](qualitative_canva.pptx) keeps each photo, field, and annotation as a separate element. Each serif label is a movable graphic to preserve STIX Two Text on import. Wording can be edited directly in the SVGs or the [Canva copy with text boxes](https://www.canva.com/d/-53oyNAi0lnE_I6).

Run `.venv/bin/python figs/extra_page_review/illustrative_update/canva_options/render.py` from the repository root to rebuild the SVGs, preview, and print PDF. Add `--canva` to rebuild the layered PowerPoint using the [existing figure exporter](../../../realworld_isaacsim/styled/build_canva.py) and its `python-pptx` and `skia-pathops` dependencies.
