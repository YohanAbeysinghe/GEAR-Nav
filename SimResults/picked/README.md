# Challenging Scene 3 qualitative reruns

This directory contains qualitative-only Scene 3 variants designed to place a
pedestrian on the robot's nominal start-to-goal line. The original benchmark
configurations and metric results are not modified.

The evaluation system's scripted-human interface uses native `GoTo` commands and does
not expose a supported per-person speed field. Challenge timing is controlled
through route geometry and `initial_idle`; the first two cases use stationary
people so their challenge does not depend on animation timing.

Three candidates are evaluated:

1. one stationary person centered on the nominal route;
2. one stationary person offset to make the freer avoidance side clear; and
3. one left-to-right crossing synchronized near the robot's arrival time.

The candidates use frozen episode IDs 46--48 respectively because the running
oracle-goal service accepts only the original Scene 3 IDs. Every frozen Scene 3
episode has the same target at `[-8.2, 8.2]`, so this changes only the human
geometry, not the policy target or robot start.

The qualitative rerun caps the robot at 0.5 m/s (with the existing 0.3 rad/s
turn-rate limit). At 1.0 m/s the policy initiated a visible turn but the
resulting 3.33 m minimum-radius arc was too wide and contacted the centerline
person; the lower speed permits a 1.67 m-radius avoidance arc. The timed
crossing's `initial_idle` is correspondingly increased to 4.5 seconds.

`manifest.json` records success, contact, clearance, cross-track deviation,
heading change, source config hash, and the generated third-person video path.
These reruns use the step-57,500 raw checkpoint, 14 refinement rounds, and the
oracle relative-waypoint goal. They are demonstrations, not additions to the
frozen benchmark denominator.
