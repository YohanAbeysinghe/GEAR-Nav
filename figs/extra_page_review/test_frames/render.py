"""Render two held-out observations and their equal-endpoint-error path comparisons."""

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

OUT = Path(__file__).resolve().parent
FIGS = OUT.parents[1]
ROOT = FIGS.parent
sys.path.insert(0, str(FIGS))
import figure_style as style

# Expected minima are from the 278-pair forward_clearance.csv evaluation.
CASES = [
    ("Spain_1", "000924", 0, "A   Daylight plaza", (-0.320107, 0.192253)),
    ("Amsterdam_1", "000884", 7, "B   Amsterdam street", (0.265533, -0.364772)),
]


def minimum(path, field, config):
    fractions = np.arange(1, 21) / 20
    samples = path[:-1, None] + np.diff(path, axis=0)[:, None] * fractions[None, :, None]
    points = samples.reshape(-1, 2)
    points = points[points[:, 0] >= 2]
    origin = [config["x_range_m"][0], config["y_range_m"][0]]
    cells = (points - origin) / config["resolution_m"] - 0.5
    scores = map_coordinates(field, cells[:, ::-1].T, order=1, mode="constant", cval=np.nan)
    assert scores.size and np.isfinite(scores).all()
    index = np.argmin(scores)
    return float(scores[index]), points[index]


def plot_case(fig, column, archive, case):
    clip, frame, goal_id, title, expected = case
    clip_dir = ROOT.parent / "data" / clip
    with (clip_dir / "metadata.jsonl").open() as records:
        rec = next(r for r in map(json.loads, records) if r["sample_id"] == frame)
    config = json.loads((clip_dir / "manifest.json").read_text())["esdf_config"]
    field = np.load(clip_dir / rec["path_generation"]["esdf_path_used"]) - config["robot_radius_m"]

    (idx,) = np.flatnonzero((archive["clip_ids"] == clip) & (archive["sample_ids"] == frame)
                            & (archive["goal_indices"] == goal_id))
    learned = archive["paths_14"][idx].astype(float)
    goal = archive["goals"][idx].astype(float)
    np.testing.assert_allclose(goal, rec["sampled_goals"][goal_id]["goal_xy_m"])
    error = np.linalg.norm(learned[-1] - goal)
    straight = np.linspace(np.zeros(2), goal * (1 - error / np.linalg.norm(goal)), len(learned))
    np.testing.assert_allclose(np.linalg.norm(straight[-1] - goal), error)
    minima = [minimum(path, field, config) for path in (straight, learned)]
    np.testing.assert_allclose([v for v, point in minima], expected, atol=2e-5)

    left = 0.085 + column * 0.49
    fig.text(left, .962, title, weight="bold", size=13)
    minutes, seconds = divmod(int(rec["timestamp_sec"]), 60)
    fig.text(left, .925, f"{clip}  ·  {minutes//60}:{minutes%60:02d}:{seconds:02d}  ·  frame {frame}  ·  goal {goal_id}", size=8.6)
    photo = fig.add_axes([left, .595, .395, .317])
    with Image.open(clip_dir / rec["image_path"]) as im:
        im.thumbnail((1000, 700), Image.Resampling.LANCZOS)
        photo.imshow(im)
    photo.axis("off")

    ax = fig.add_axes([left, .185, .395, .401])
    # Raster columns run from camera right to left in increasing robot-frame y.
    # Flipping the display axis puts positive lateral displacement on camera left.
    extent = [*config["y_range_m"], *config["x_range_m"]]
    raster = ax.imshow(field.T, extent=extent, origin="lower", cmap=style.TEASER_ESDF_CMAP,
                       vmin=-1, vmax=1, interpolation="nearest", rasterized=True)
    ax.set(xlim=(4, -6), ylim=(0, 11.25), xticks=[4, 2, 0, -2, -4, -6], yticks=[0, 2, 4, 6, 8, 10])
    ax.axhspan(0, 2, color="white", alpha=.67, lw=0)
    ax.axhline(2, color="#555", lw=.8, ls=":")
    halo = [pe.Stroke(linewidth=3.3, foreground="white"), pe.Normal()]
    ax.plot(learned[:, 1], learned[:, 0], color=style.COLORS[14], lw=2, path_effects=halo)
    ax.plot(straight[:, 1], straight[:, 0], color="#263342", ls="--", lw=1.25, path_effects=halo)
    _, xy = min(minima, key=lambda pair: pair[0])
    ax.plot(xy[1], xy[0], "kx", ms=7, mew=1.5, path_effects=halo)
    ax.set_xlabel("Lateral position (m)")
    if column == 0:
        ax.set_ylabel("Forward distance (m)")
    ax.tick_params(labelsize=8, length=2)
    fig.text(left+.1975, .095, f"Minimum clearance:   Straight {minima[0][0]:+.2f} m    GEAR {minima[1][0]:+.2f} m",
             ha="center", size=9.4)
    return raster


def main():
    plt.rcParams.update({"font.family": "serif", "font.serif": [style.FONT, "STIXGeneral"],
                         "font.size": 9, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "svg.hashsalt": "gear-test-frames"})
    fig = plt.figure(figsize=(7.45, 5.9))
    with np.load(ROOT / "eval/best_model/model_paths_checkpoint57500.npz") as archive:
        assert int(archive["checkpoint"]) == 57500 and str(archive["mode"]) == "model_only"
        splits = ROOT / "configs/splits"
        eval_clips = (splits / "eval_clip_ids.txt").read_text().split()
        train_clips = (splits / "train_clip_ids.txt").read_text().split()
        for column, case in enumerate(CASES):
            assert case[0] in eval_clips and case[0] not in train_clips
            raster = plot_case(fig, column, archive, case)

    keys = [Line2D([], [], ls="--", color="#263342", label="Matched straight path"),
            Line2D([], [], color=style.COLORS[14], label="GEAR-Nav"),
            Line2D([], [], ls="none", marker="x", color="black", label="Negative minimum")]
    fig.legend(handles=keys, loc="center left", bbox_to_anchor=(.045, .049), ncol=3,
               frameon=False, handlelength=1.25, columnspacing=1.0, fontsize=8.3)
    bar = fig.colorbar(raster, cax=fig.add_axes([.74, .046, .18, .012]), orientation="horizontal",
                       ticks=[-1, 0, 1], extend="both")
    bar.ax.tick_params(length=2, pad=1, labelsize=7)
    bar.ax.set_title("Footprint clearance (m)", fontsize=8, pad=3)
    for ext, metadata in [("svg", {"Date": None}), ("pdf", {"CreationDate": None}), ("png", {})]:
        fig.savefig(OUT / f"camera_and_clearance.{ext}", dpi=180, metadata=metadata)
    plt.close(fig)


if __name__ == "__main__":
    main()
