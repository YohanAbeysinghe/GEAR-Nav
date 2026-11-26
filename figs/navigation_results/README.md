# Two figures for the GEAR-Nav results section

## Navigation outcomes

The [current paper table](https://github.com/YohanAbeysinghe/Overleaf---Action-free-Spatial-Trajectory-Refinement-via-Energy-based-Aggregation/blob/6de9539/sections/5_Results.tex) and [numeric export](aggregate_results.csv) report 92, 89 and 86 goal reaches over 100 GEAR-Nav trials per scenario. Of these, 87, 80 and 79 reached the goal without collision. The three baseline rows per scenario are from VEGA's Isaac Sim evaluation (50 trials per baseline and scenario). On the separate Vision 60 routes in Table I, GEAR-Nav reached the goal without contact in 16/20, 16/20 and 20/20 trials.

## How far does one refined plan get?

**Suggested caption.** Each frame–goal pair contributes the endpoint of its sampled initial path and the endpoint after 14 learned updates. The dashed line shows the smallest geometrically possible endpoint error given the 15 m maximum path length. The right panel shows the change for each pair when inference continues from 14 to 30 updates on the same image and goal. Positive values indicate that the endpoint moved closer. [Figure PDF](goal_progress.pdf) · [Editable SVG](goal_progress.svg)

The evaluation covers 300 sampled metric goals across eight clips excluded from the 89-clip training split. The seed was 0. The deployed configuration uses the raw parameters from training step 57,500 and 14 model-only updates. Endpoint error is the Euclidean distance in meters from the last predicted waypoint to the original goal in the robot frame. All depths for a given pair share one observed robot pose. Several conditions come from each clip.

| Quantity | Measured value |
| --- | ---: |
| Median progress at initialization / 14 updates | 2.43 / 9.66 m |
| Endpoints within 0.5 m at 14 updates | 83 / 300 |
| Median endpoint error at initialization | 8.87 m |
| Median endpoint error at 14 updates | 1.26 m |
| Pairs with a closer endpoint at 14 updates than at initialization | 287 / 300 |
| Median path length, initial / 14 updates | 2.60 / 9.81 m |
| Median endpoint error at 14 updates for goals within the 15 m maximum horizon | 0.58 m (198 pairs) |
| Median goal distance gained from the robot origin at 14 updates for goals beyond the horizon | 10.24 m (102 pairs) |
| Median paired reduction in error from 14 to 30 updates | 0.030 m |
| Endpoints closer / farther at 30 updates than at 14 | 164 / 136 |

The short initializer leaves room for a large reduction in goal distance through path extension. The figure measures this local planning behavior. Physical obstacle clearance and closed-loop success require separate measurements.

`endpoints.csv` contains the clip, frame, sampled-goal index, original goal coordinate, endpoints at 0, 14, 20 and 30 updates, and arc lengths for the initial and deployed paths. The initializer is deterministic for a given seed and frame–goal identity. Extraction matches each archived prior to the model record by dataset index and checks the logical identity, exact goal coordinates, clip split and prior settings.

| Source archive | SHA-256 |
| --- | --- |
| `eval/final_paths.npz`, baseline prior only | `8b5247f4b5c125aa42a4a99f7bb2cabad092256cb6461e269fc97fba55edc33f` |
| `eval/best_model/model_paths_checkpoint57500.npz` | `3cbcdebfbfb227c221e5d2626567fe0e9d7e49bb7e2128453c4e6b8af00c867e` |

## A pedestrian passes during the approach to the scooter

**Suggested caption.** Four frames from one continuous external-camera recording show the Scene 3 run. A pedestrian approaches and passes the robot on the walkway. The robot continues toward the scooter. Times are measured from the start of the recording. [Figure PDF](pedestrian_pass.pdf) · [Editable SVG](pedestrian_pass.svg)

The source is `figs/realworld_exp/Scene 3/ASTAR/IMG_4546.MOV`. The four frames use the same crop. The SVG embeds the photographs, source hash, decoded timestamps, frame indices and crop coordinates. This selected sequence illustrates one interaction. Quantifying clearance or final goal distance would require calibrated measurements.

## Regeneration

Run from the GEAR-Nav repository root. The checked-in CSV and SVG suffice for both paper figures.

```sh
.venv/bin/python figs/navigation_results/goal_progress.py
.venv/bin/python figs/navigation_results/pedestrian_pass.py
```

To rebuild the CSV and refresh the embedded photographs from the original evaluation archives and movie, run

```sh
.venv/bin/python figs/navigation_results/goal_progress.py --extract .
.venv/bin/python figs/navigation_results/pedestrian_pass.py --extract
```
