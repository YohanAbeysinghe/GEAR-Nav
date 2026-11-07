# GEAR-Nav slides: VEGA-style refinement, November 7, 2026

**Latest slide 4 revision:** the dense training pipeline has been replaced by
a focused dataset aggregation loop: generate paths, get corrections, retain
old and new examples, and retrain. See [the verified preview and source](slide4_simplified/README.md).
The follow-up supersedes slide 4 in the earlier full-deck artifacts below.

**Latest slide 3 revision:** the user requested a simpler explanation after
the full-deck refinement. The complex energy-oracle panel has been replaced
with five editable energy cards. See [the verified preview and source](slide3_simplified/README.md).
The full-deck `preview.pdf`, `preview.jpg`, and `canvas.json` below document the
earlier refinement; the slide 3 follow-up supersedes that slide only.

The existing [native Google Slides deck](https://docs.google.com/presentation/d/1LUUqhMl4_GE6BG1YvRhg6KFbFrBVj-uHkU6u_nem1O0)
was edited in place. All 13 slides use a consistent dark canvas, gray title
band, white Arial headings, restrained orange emphasis, and the existing
scientific figure palette. The reference is the supplied
[VEGA presentation](https://docs.google.com/presentation/d/1dxzUvLMAlESOssgjBO9p__LvFgcIW6hNHQ40TzGQlls).

The energy-oracle and training-pipeline panels occupy separate full-width
slides. The architecture slide uses the current paper's model diagram,
with an adjacent explanation of conditioning, correction prediction, and
bounded iterative updates. These assets are rendered from the local paper
PDFs, derived from the established diagram masters; no Figma calls were made.
Narrative text, labels, aggregation blocks, and recorded paths remain native
editable Slides objects. Paper diagram panels are embedded as high-resolution
images and retain their source typography.

## Deliverables

- `preview.pdf`: final native export, with video poster frames.
- `preview.jpg`: contact sheet of all final slides.
- `canvas.json`: intended element geometry and local media references.
- `slide-plan.json`: narrative, reference exemplars, and explicit existing-element mappings.
- `provenance.json`: source hashes and the baseline-label decision.
- `delivery.json`: final native revision, video inventory, and validation record.
- `final-issues.json`: zero issues from the Slides output checker.
- `assets/`: the three diagram panels and two newly used baseline poster images.
- `refine_deck.py`, `repair_deck.py`, `prepare_assets.py`: local construction and repair scripts.

## Video attribution and behavior

All 13 original native video objects retain their exact Drive source IDs,
intervals, autoplay, and mute settings. Two native Drive videos were added
to the indoor comparison so it shows GEAR-Nav, OmniVLA, NaVILA, and TIC-VLA.
The added clips use VEGA slide `p2`'s exact source IDs and intervals:

| Method label | Drive video ID | Source name | Interval |
| --- | --- | --- | --- |
| NaVILA | `1SwtuXQgXN-oztTsK9iVlgyUCvEywbsMm` | IMG_3134.MOV | 6–36 s |
| TIC-VLA | `1tnb1Fm5BEpfdefOssROZBGLqcb78qA1A` | IMG_3132.MOV | 2–33.213 s |

The older local download manifest places these filenames under OmniVLA.
The user explicitly resolved that conflict on November 7: **use the labels
shown in VEGA**. That decision is documented in the slide notes and provenance;
the historical manifest is unchanged. Local poster source sizes match the
Drive metadata (63,289,883 and 66,309,682 bytes, respectively).

Videos retain their full 9:16 frames and play at 1×. Comparisons are labeled
as separate representative trials. Video rendering and configuration were
verified through native readback and PDF posters; interactive playback in
the Google Slides UI was not tested. This remains a slide deck, not a rendered
three-minute film. Existing video-production timing is retained as historical
notes, alongside revised narration and source notes.

## Scientific scope

Content follows `GEAR-Nav Overleaf/main.tex` as read on November 7.
Training geometry supplies local, projection-aware correction targets;
deployment uses the learned field without ESDF or analytic energy queries.
The replay progression in the pipeline figure is schematic. Slide 7 retains
the previously verified checkpoint states at 0, 6, and 14 updates, including
the same-checkpoint continuation provenance for the sixth state. These are
qualitative illustrations, separate from the paper's twelve-step evaluation.
No new inference was run and no unverified benchmark measurements were added.

## Validation and rebuild boundaries

All 13 final exported slides were visually inspected. One consolidated repair
pass corrected image scales after Google's replacement operation changed the
intrinsic image dimensions, removed inherited bullets from rewritten prose,
fixed one wrapped label, widened page numbers, and added the confirmed baseline
clips. Native readback verifies 15 video instances, unchanged original video
properties, proportional image/video dimensions, and complete speaker notes.

`prepare_assets.py` uses local paper PDFs and existing recordings.
`refine_deck.py` uses the prior committed composition and the local pre-edit
connector snapshot. `repair_deck.py` derives normalized image transforms from
the first native readback. These scripts emit plans/proofs and do not write to
Google Slides. Their mutations target this session's snapshots; do not replay
them blindly against the already updated deck. Read the deck anew before
another edit. Raw connector snapshots, temporary requests, per-slide renders,
and expiring media URLs remain local and are not committed.
