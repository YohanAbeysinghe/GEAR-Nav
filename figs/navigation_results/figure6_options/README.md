# Figure 6 alternatives

Each draft is 7.08 inches wide and 2.72 inches high. The figures use burnt orange for the 14-update GEAR-Nav result, slate for the reference path or other update counts, and charcoal for labels. The combined [preview](compare.png) shows all three drafts.

| Draft | Question | Assets |
| --- | --- | --- |
| 1. Goal progress and clearance | Do learned updates improve progress and mapped clearance? | [PDF](progress_and_clearance.pdf) · [Editable SVG](progress_and_clearance.svg) |
| 2. Local planning horizon | How much can a local plan accomplish for near and distant goals? | [PDF](planning_horizon.pdf) · [Editable SVG](planning_horizon.svg) |
| 3. Refinement budget | How much additional progress comes from running more than 14 updates? | [PDF](refinement_budget.pdf) · [Editable SVG](refinement_budget.svg) |

## Caption drafts

**1. Goal progress and clearance on held-out video.** (a) Each point compares endpoint error for the same image and goal before refinement and after 14 learned updates. Points below the diagonal represent endpoints that moved closer to the goal. (b) For each condition, a straight comparison path ends at the same distance from the goal as the refined path. Clearance is scored from 2 m ahead in the 278 pairs with map coverage for both paths in that region.

**2. Refinement within and beyond the planning horizon.** The maximum path length is 15 m. (a) For the 198 goals within this distance of the robot, we report the distance remaining between the path endpoint and the goal. (b) For the 102 farther goals, we report how much closer the path endpoint is to the goal than the robot origin. Dots mark medians and lines span the middle 50% of pairs.

**3. Goal progress by refinement depth.** (a) Endpoint error at four measured update counts on the same 300 frame–goal pairs. Dots mark medians and lines span the middle 50% of pairs. (b) The paired change from 14 to 30 updates. Positive values indicate that the endpoint moved closer to the goal.

## Measurements

- The [endpoint archive](../endpoints.csv) covers 300 frame–goal pairs from eight held-out clips. The [evaluation provenance](../README.md) records the archive hashes and correspondence checks. The learned paths use the 57,500-step checkpoint. Each refinement depth uses the same image and goal.
- The [clearance cache](forward_clearance.csv) uses the same 14-update paths from the checkpoint 57,500 archive listed in the evaluation provenance. Identity, goal coordinates, and final waypoints were matched to the endpoint archive. The straight path for each case follows the ray toward the goal with the same endpoint error and segment bound as GEAR-Nav. Both paths use 16 waypoints.
- As in the paper's held-out clearance analysis, sample each segment at 20 equal increments, including its endpoint, and subtract the 0.50 m footprint radius from the bilinearly interpolated ESDF. Keep the pairs for which each path has samples at least 2 m ahead and all such samples are supported. Among 278 qualifying pairs, 124 have negative clearance for both, 35 for the straight path only, and 13 for GEAR-Nav only. The median paired improvement in minimum clearance is 0.005 m. These are offline map measurements.

Rebuild the previews from the saved measurements with `.venv/bin/python figs/navigation_results/figure6_options/render.py`.
