# ASTAR 57500 oracle-goal upper-bound diagnostic

This experiment uses the exact frozen navigation scenario goal at inference time.
It is a diagnostic upper bound, **not** a valid RGB-language-only benchmark result.

The checkpoint, scenes, controller, policy cadence, and speed limits match the
completed language-only ASTAR run. The change is that each request's world goal
is transformed into the current robot FLU frame and passed to the original
coordinate-conditioned `AstarPolicy.infer()` implementation. This restores the
goal waypoint, goal-biased starting prior, and goal-aware path decoder.

## Storage

- Experiment source/configuration: this directory.
- Full episode outputs: `results/scenario1`, `results/scenario2`, and `results/scenario3`.
- Pilot episode outputs: `pilot_results/scenario1`, `pilot_results/scenario2`, and `pilot_results/scenario3`.
- Policy requests and URL: `runtime/`.
- Slurm logs: `logs/`.
- Aggregate report: `report/`.

The shared benchmark runner requires result paths below `vega-dynanav/results`.
`src/prepare.py` creates six non-destructive compatibility symlinks whose real
targets are the result directories above.

## Prepare

From the ASTAR repository:

```bash
.venv/bin/python SimResults/astar_57500_oracle_goal/src/prepare.py
```

## Start the model server

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:l40s:1 --cpus-per-task=6 --mem=48G \
  --time=12:00:00 \
  --output=SimResults/astar_57500_oracle_goal/logs/policy_%j.log \
  SimResults/astar_57500_oracle_goal/slurm/policy.sh
```

Wait until the policy log contains `READY`.

## Run one pilot from each scenario first

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:rtx2080ti:1 --nodelist=legacygpu15 \
  --cpus-per-task=4 --mem=32G --time=02:00:00 \
  --output=SimResults/astar_57500_oracle_goal/logs/pilot_%j.log \
  SimResults/astar_57500_oracle_goal/slurm/pilot.sh
```

Inspect `validation/pilot_results.json`. The pilot validates integration and
coordinate transforms; its performance must not be used to select scenes.

## Run all 150 trials

Keep the policy server alive and submit:

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:rtx2080ti:1 --nodelist=legacygpu15 \
  --cpus-per-task=4 --mem=32G --time=08:00:00 \
  --output=SimResults/astar_57500_oracle_goal/logs/evaluate_%j.log \
  SimResults/astar_57500_oracle_goal/slurm/evaluate.sh
```

The evaluation is resumable. If the eight-hour allocation ends before all 150
episodes complete, submit the same evaluation command again. Existing valid
episodes are retained and skipped.

The final summary is written to `report/COMPARISON_REPORT.md` and all underlying
episode JSON and prediction traces remain under this experiment's `results/`.

## Requirement for the full video evaluation

The dedicated 150-episode **video** evaluation must capture the rear
third-person camera as well as the robot camera. Explicitly set
`VEGA_DISABLE_THIRD_PERSON=0` (and keep `VEGA_RENDER_ON_SENSOR_ONLY=0`) for that
run, retain the `prediction_*_third_person.jpg` frames, and export the
third-person MP4s with `final_scene_videos_20260921/export_video.py
--third-person`. Do not assume the metrics-only evaluation has third-person
frames: its capture settings must be checked before submission.

For the preferred smaller qualitative set, wait until the metrics run contains
at least five collision-free successes in every scene, keep the oracle policy
server alive, and submit:

```bash
sbatch -p scavenger -A scavenger \
  --gres=gpu:rtx2080ti:1 --nodelist=legacygpu15 \
  --cpus-per-task=4 --mem=32G --time=04:00:00 \
  --output=SimResults/astar_57500_oracle_goal/logs/third_person_%j.log \
  SimResults/astar_57500_oracle_goal/slurm/third_person_successes.sh
```

This selects five validated collision-free successes per scene, reruns only
those 15 episodes under separate run IDs with third-person capture enabled, and
writes the MP4s beneath `third_person_successes/videos/`. It never overwrites
the 150-episode metrics results.

