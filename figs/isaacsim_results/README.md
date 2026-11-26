# Navigation results
The paper's Table II is the source for [the results CSV](aggregate_results.csv) and the [figure](isaacsim_results.pdf). The GEAR-Nav trial counts come from the Ablation planning tab of the [results workbook](https://docs.google.com/spreadsheets/d/130sqiF9Ug4SrJjKQfMb6_QQlN1YzSRCv_nFpcKe46r8/edit#gid=41032604).

| Scenario | Goal reached | Collision | Goal reached without collision | Mean minimum clearance |
| --- | ---: | ---: | ---: | ---: |
| 1 | 92/100 | 6/100 | 87/100 | 0.89 m |
| 2 | 89/100 | 10/100 | 80/100 | 0.56 m |
| 3 | 86/100 | 12/100 | 79/100 | 1.71 m |

The reference rows reproduce the three baselines from VEGA's Isaac Sim evaluation (50 trials per method per scenario). The recorded scene views illustrate separate runs. The [oracle-goal diagnostic](oracle_goal_diagnostic/README.md) retains the results for its own protocol.

From the repository root, run `.venv/bin/python figs/isaacsim_results/prepare.py` followed by `.venv/bin/python figs/isaacsim_results/render.py` to refresh the CSV, provenance, and figures from the paper.
