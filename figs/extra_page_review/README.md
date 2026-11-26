# Choosing the extra page

[Two-page review PDF](page_options.pdf) · [Option A figure](illustrative_update/illustrative_update.pdf) · [Editable SVG](illustrative_update/illustrative_update.svg) · [PNG preview](illustrative_update/illustrative_update.png)

## Option A — One waypoint correction at a bollard

The frame, sampled navigation goal and signed distance field are recorded. The candidate, the proposed oracle update and the proposed GEAR update are all hand-drawn. On the open approach they point in similar directions. Beside the nearest bollard they send the same waypoint to opposite sides of the mapped footprint boundary. The two proposed paths end at exactly the same location.

Panels (a) and (b) locate the goal and the candidate in one Amsterdam canal-side scene. Panel (c) enlarges the rectangle on the ESDF. The two arrows leaving each yellow waypoint use the same metric scale. At Q, ESDF interpolation at the teal and orange arrowheads gives footprint clearances of +0.48 m and −0.26 m. Panel (d) compares directions. The angles of 14° at P, 69° at Q and 35° for the whole path describe the drawing. The whole-path angle compares the two vectors formed by concatenating the 15 movable waypoint displacements. Its value depends on both their directions and their relative magnitudes.

For a measured version in the held-out evaluation, start with the same intermediate path from a recorded model rollout and apply one oracle update and one model update from that path. Each recorded frame–goal pair would contribute one whole-path angle. Count zero-length updates separately. Figure 1 already illustrates successive refinement. This proposed comparison examines whether a learned update recovers the geometric correction at the path the model visits.

### Sources and editing

- The original camera JPEG and lossless ESDF crop come from held-out clip `Amsterdam_3`, frame `000657` at 1:04:40. The gold star is sampled goal 1 from that frame's metadata. Its marker on the image uses a recorded ground return within 2 cm of the goal in the navigation plane. A separate point on the visible bollard supplies the map annotation. [Scene record and source hashes](illustrative_update/scene.json)
- The colored field displays the recorded ESDF minus the 0.50 m robot radius. The dotted contour is zero footprint clearance. The map treats unobserved space as occupied. Camera right points to the right of both map panels and forward points up. [Lossless map crop](illustrative_update/esdf_crop.npz)
- Each sketch consists of 16 hand-specified positions or displacements in meters. Both proposals start from the same candidate, preserve the fixed origin, and use the same endpoint displacement. [Edit the drawing](illustrative_update/artwork.json)
- From the repository root, run `.venv/bin/python figs/extra_page_review/illustrative_update/render.py` to regenerate the figure from the included inputs. To recapture the original scene, append `--capture ../data`. Build the review document with `latexmk -pdf page_options.tex` from `figs/extra_page_review`.

The earlier equal-endpoint-error study compares an actual model prediction with a constructed straight path. Its two scene drafts and the matched-clearance measurements are a separate review of Option A's earlier design. [Earlier scene drafts and provenance](test_frames/README.md)

## Option B — A pedestrian passes the physical robot

Four timestamps from one continuous external-camera recording of the scooter trial show the pedestrian approaching and passing before the robot nears its goal. The outcomes distinguish contact or intervention from other unsuccessful trials across all three hardware routes. [Video-frame provenance and source](../navigation_results/README.md)
