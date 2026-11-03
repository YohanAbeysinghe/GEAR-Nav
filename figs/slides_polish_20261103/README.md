# GEAR-Nav supplementary slides: polished revision

The [existing native deck](https://docs.google.com/presentation/d/1LUUqhMl4_GE6BG1YvRhg6KFbFrBVj-uHkU6u_nem1O0/edit)
was revised in place on November 3, 2026. It contains 13 editable slides
following the existing three-minute video plan.

The revision uses short research statements, serif headings, restrained
accents, the paper's scientific role colors, larger scene images, and larger
portrait videos. Method diagrams and recorded waypoint paths remain native
editable elements. The recap shows the training-to-deployment relationship
through a real scene and energy-oracle visualization. Opening and closing
titles follow the expansion requested in the project's instructions.

## Review artifacts

- `preview.pdf`: final Google Slides export; videos appear as poster frames.
- `preview.png`: contact sheet of every final slide.
- `polish_deck.py`: local composition and native-mutation generator.
- `canvas.json`: final intended element geometry, text, and media mapping.
- `slide-plan.json`: timing, narration, edit cues, evidence boundaries, and
  explicit keep/edit/delete mappings for the original slide elements.
- `provenance.json`: source hashes and recorded-model context.
- `delivery.json`: final native readback and visual verification receipt.
- `assets/esdf-reference.png`: calibrated reference viewport and zero contour.

Generated working snapshots, requests, per-slide SVG/PNG proofs, and both
PDF review rounds remain local in this directory. The tracked review files
are explicit exceptions to the workspace's broad `figs/` ignore rule. Raw
connector snapshots with expiring image URLs are not committed.

## Scientific provenance

The ESDF and original paths come from `figs/pipeline/assets/scene_data.npz`.
The intermediate state now uses the authentic saved sixth update from
`figs/model/plots/sixth_iteration.npz`, rather than a first-update path labelled
as update 6. Its receipt identifies a same-checkpoint continuation from depth
3 and a 0.04256 m maximum depth-7 difference from the original capture batch.
The panels are qualitative checkpoint states. ESDF is a display reference,
not an inference input. No inference was run during this revision.

The 13 original native video instances retain their exact source IDs,
autoplay, mute, and interval settings. They play at 1×. Final-video speed
changes, staged reveals, narration, and timed slide advances are production
instructions in the notes. These slides are not a rendered three-minute film.

## Verification and local use

The output issue checker found zero issues. All 13 slides were reviewed from
the first export; one consolidated pass fixed label wrapping, mathematical
subscripts, and footer spacing. All 13 final exported slides passed visual
review. Native readback confirmed slide order, the unchanged video objects,
their 9:16 aspect ratios, and complete speaker notes without missing cue text.
Interactive playback was not tested in the Slides UI.

From the original workspace, `.venv/bin/python figs/slides_polish_20261103/polish_deck.py`
rebuilds local requests and proofs using the original `raw-template.json`,
`figs/video_slides_20261103/` sources, saved scene arrays, and shared figure
style. It performs no remote writes. The generated requests target the
original snapshot; do not blindly replay them against the already revised
deck. The final native deck and exported PDF are the visual reference.
