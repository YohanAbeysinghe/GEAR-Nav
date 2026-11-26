# ASTAR 57500 oracle-goal diagnostic: 100 trials per scene

This directory extends the existing 50-trial experiment without modifying or
rerunning it. The cumulative evaluation is:

- Base results: episodes 1--50 in `../astar_57500_oracle_goal/results/`.
- Extension results: episodes 51--100 in `results/` here.
- Total: 100 trials per scene, 300 metric trials across three scenes.
- Qualitative pass: 15 successful, collision-free third-person reruns per scene
  (45 videos total), selected only after all metric trials are complete.

This remains an oracle-goal upper-bound diagnostic. It is not a valid
language-only result: every policy request receives the evaluation system's exact goal
transformed into the robot frame. The checkpoint is step 57500, raw parameters,
with 14 refinement rounds and the goal-biased prior.

## Controlled trial extension

`src/generate_configs.py` preserves episodes 1--50 exactly and creates episodes
51--100. Geometry, instructions, goals, controller settings, people, and routes
remain fixed. Only the primary moving person's `initial_idle` varies. The new
50 values use a deterministic shuffled quarter-offset grid over 0.2--1.5 s and
do not overlap the original timing values.

Generation details, hashes, seed, and the exact timing sequence are stored in
`configs/config_generation.json`. The execution manifest contains only episodes
51--100, so resuming this experiment cannot duplicate the original 50 trials.

## Metric run (episodes 51--100 only)

Prepare and validate locally:

```bash
cd /fs/nexus-projects/REAL2SIM3/project-VEGA/ASTAR
/fs/nexus-projects/REAL2SIM3/project-VEGA/VEGA/.conda/envs/vega/bin/python \
  SimResults/astar_57500_oracle_goal_100/src/prepare.py
```

Start the isolated policy server (port 19842):

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:l40s:1 --cpus-per-task=6 --mem=48G \
  --time=16:00:00 \
  --output=SimResults/astar_57500_oracle_goal_100/logs/policy_%j.log \
  SimResults/astar_57500_oracle_goal_100/slurm/policy.sh
```

After the policy log prints `READY`, submit the 150-trial extension:

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:rtx2080ti:1 --nodelist=legacygpu15 \
  --cpus-per-task=4 --mem=32G --time=12:00:00 \
  --output=SimResults/astar_57500_oracle_goal_100/logs/evaluate_%j.log \
  SimResults/astar_57500_oracle_goal_100/slurm/evaluate.sh
```

The dispatcher runs one episode per subprocess and resumes from valid result
JSON files. The cumulative base-plus-extension report is written to
`report/cumulative_summary.json`.

## Third-person success recordings

The selector requires 100 valid metric results in every scene and at least 15
collision-free successes per scene. It chooses 15 timing-distributed successes,
not simply the first 15 episode IDs. Submit after the cumulative report says
`"complete": true`:

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:rtx2080ti:1 --nodelist=legacygpu15 \
  --cpus-per-task=4 --mem=32G --time=12:00:00 \
  --output=SimResults/astar_57500_oracle_goal_100/logs/third_person_%j.log \
  SimResults/astar_57500_oracle_goal_100/slurm/third_person_successes.sh
```

The recording job is resumable. For each selected episode it stores:

- result and metric JSON plus episode log;
- waypoint/path prediction JSON files and policy cadence telemetry;
- front-camera and third-person frames;
- robot-state evidence snapshots;
- a third-person MP4 and playback metadata JSON.

Locations:

- Selection provenance: `third_person_successes/selection.json`
- Rerun results and paths: `third_person_successes/results/scenario*/`
- Videos: `third_person_successes/videos/scenario*/`

The qualitative reruns are fresh demonstration runs and remain excluded from
the 300 metric-trial statistics.
