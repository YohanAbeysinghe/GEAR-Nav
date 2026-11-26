Navigation comparison: 150/150 valid trials complete.

Updated: 2026-10-20T16:24:25.783737+00:00

| Scene | Method | Valid trials | Goal reached | Actual contact | Goal progress | FOV human clearance |
|---|---|---:|---:|---:|---:|---:|
| scenario1 | astar57500_oracle_goal | 50/50 | 50/50 (100.0%) | 0/50 (0.0%) | 83.1% | 1.050 m |
| scenario2 | astar57500_oracle_goal | 50/50 | 49/50 (98.0%) | 1/50 (2.0%) | 78.5% | 0.449 m |
| scenario3 | astar57500_oracle_goal | 50/50 | 50/50 (100.0%) | 0/50 (0.0%) | 79.9% | 0.861 m |

Custom navigation scenarios, not official benchmark scores. Goal success and actual PhysX contact are independent. Goal success uses the fixed 1.5 m threshold. Clearance averages all valid completed trials: collision trials contribute zero, and contact-free trials contribute their minimum FOV human gap. N/A means no trials or missing contact-free FOV measurements. Clearance is signed: a negative value indicates conservative 2D footprint overlap, while collision comes separately from actual PhysX contacts. Partial groups are provisional. See README.txt for metric definitions and manifest.json for checkpoint and controller details.

Scene selection: Scenes were selected using VEGA-only development screening, including unsuccessful warehouse candidates retained separately. Scene3 replaces the hospital with a warehouse and an off-axis blue-shirt person goal. Reported comparison trials are fresh paired timings with frozen geometry; scores are conditional on this scene selection.
Screening episodes are excluded. All fresh comparison outcomes are retained, including failures.
