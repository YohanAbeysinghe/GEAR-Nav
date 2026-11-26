"""First manuscript drafts for the two selected camera and ESDF observations."""

import sys

from render import CASES, OUT, ROOT, load_case, style

from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

sys.path.insert(0, str(ROOT.parent / "VLA_DataGeneration" / "utils"))
from pointcloud_utils import (camera_to_base_transform, fit_ground_plane_ransac,
                              select_ground_plane_candidates)

STRAIGHT = "#263342"
ORANGE = style.COLORS[14]
HALO = [patheffects.Stroke(linewidth=2.5, foreground="white"), patheffects.Normal()]
STEMS = ["spain_plaza", "amsterdam_street"]


def camera_panel(ax, clip_dir, rec, config, paths):
    with Image.open(clip_dir / rec["image_path"]) as rgb:
        size = np.array(rgb.size)
        rgb.thumbnail((1000, 700), Image.Resampling.LANCZOS)
        ax.imshow(rgb, extent=(-.5, size[0]-.5, size[1]-.5, -.5))
    with np.load(clip_dir / rec["pointcloud_path"]) as cloud:
        np.testing.assert_array_equal(size, cloud["full_image_size"])
        points = cloud["points_map"].astype(float)
        intrinsics = cloud["intrinsics"]
        depth = cloud["depth_map"]
        valid = cloud["mask"] & np.isfinite(points).all(axis=2) & (depth > 0)
    rotation, translation = camera_to_base_transform(config["camera_height_m"])
    correction = np.array(rec["esdf_ground_alignment"]["correction_rotation_matrix"])
    # Refit the omitted floor offset using the source generator and its nominal base frame.
    points[~valid] = np.nan
    fit = fit_ground_plane_ransac(select_ground_plane_candidates(points @ rotation.T + translation),
                                  rng=np.random.default_rng(20261027))
    if fit is None:
        raise ValueError(f"No floor fit for {rec['clip_id']} {rec['sample_id']}")
    normal = correction @ fit["normal"]
    offset = fit["offset"] + (fit["normal"] - normal) @ translation
    transform = correction @ rotation
    for obj in rec["object_goals"]:
        if obj.get("goal_xyz_camera_m") is not None and obj.get("goal_xyz_m") is not None:
            np.testing.assert_allclose(transform @ obj["goal_xyz_camera_m"] + translation,
                                       obj["goal_xyz_m"], atol=.001)
    def normalized_pixels(camera):
        return camera[:, :2] / camera[:, 2:3] * np.diag(intrinsics)[:2] + intrinsics[:2, 2]

    height, width = depth.shape
    row, col = np.nonzero(valid)
    np.testing.assert_allclose(normalized_pixels(points[valid]) * [width, height] - .5,
                               np.stack([col, row], axis=1), atol=.001)
    for path, color, linestyle in zip(paths, (STRAIGHT, ORANGE), ("--", "-"), strict=True):
        fractions = np.linspace(0, 1, 80, endpoint=False)
        dense = path[:-1, None, :] + np.diff(path, axis=0)[:, None, :] * fractions[None, :, None]
        xy = np.vstack([dense.reshape(-1, 2), path[-1]])
        xyz = np.column_stack([xy, -(xy @ normal[:2] + offset) / normal[2]])
        camera = (xyz - translation) @ transform
        front = camera[:, 2] > .15
        uv = np.full_like(xy, np.nan)
        uv[front] = normalized_pixels(camera[front])
        indices = np.flatnonzero(front & ((uv >= 0) & (uv < 1)).all(axis=1))
        col, row = (uv[indices] * [width, height]).astype(int).T
        z = camera[indices, 2]
        supported = valid[row, col] & (z <= depth[row, col] + .12 + .03*z)
        visible = np.zeros(len(xy), dtype=bool)
        visible[indices[supported]] = True
        uv[~visible] = np.nan
        pix = uv * size - .5
        ax.plot(*pix.T, lw=1.05, color=color, ls=linestyle, path_effects=HALO)
        print(rec["clip_id"], color, f"{visible.sum()}/{len(visible)} projected samples visible")
    ax.set(xlim=(-.5, size[0]-.5), ylim=(size[1]-.5, -.5))
    ax.axis("off")


def draw_scene(fig, column, ncols, case, data):
    def axes(x, y, w, h):
        return fig.add_axes([(column+x)/ncols, y, w/ncols, h])

    def label(x, y, value, **kwargs):
        fig.text((column+x)/ncols, y, value, **kwargs)

    clip, frame, goal_id, title, _ = case
    clip_dir, rec, config, field, straight, learned, minima = data
    minutes, seconds = divmod(int(rec["timestamp_sec"]), 60)
    label(.06, .956, title[4:], weight="bold", size=13)
    label(.06, .915, f"{clip}   ·   {minutes//60}:{minutes%60:02d}:{seconds:02d}   ·   frame {frame}   ·   goal {goal_id}",
          size=7.4, color="#45505A")
    camera_panel(axes(.06, .545, .88, .355), clip_dir, rec, config, (straight, learned))
    label(.065, .514, "Local plan", size=8.7, weight="bold")

    # Select the crop in metric coordinates, preserving the same orientation in both maps.
    score, point = min(minima, key=lambda item: item[0])
    assert score < 0
    x, y = point
    label(.55, .514, f"Minimum at {x:.2f} m", size=8.7, weight="bold")
    half = 1.4
    extent = [*config["y_range_m"], *config["x_range_m"]]
    overview = axes(.082, .229, .391, .262)
    detail = axes(.56, .231, .357, .254)
    for ax in (overview, detail):
        raster = ax.imshow(field.T, extent=extent, origin="lower", cmap=style.TEASER_ESDF_CMAP,
                           vmin=-1, vmax=1, interpolation="nearest")
        ax.plot(straight[:, 1], straight[:, 0], color=STRAIGHT, lw=1, ls="--", path_effects=HALO)
        ax.plot(learned[:, 1], learned[:, 0], color=ORANGE, lw=1.3, path_effects=HALO)
        ax.plot(y, x, marker="x", color="black", markersize=5.2, mew=1.15, path_effects=HALO)
        ax.tick_params(length=1.5, pad=1, labelsize=6.2)
        for spine in ax.spines.values():
            spine.set_linewidth(.5)
    overview.set(xlim=(4, -6), ylim=(0, 12), xticks=[3, 0, -3, -6], yticks=[0, 4, 8, 12])
    overview.axhspan(0, 2, color="white", alpha=.65, lw=0)
    overview.axhline(2, ls=":", color="#484D51", lw=.7)
    overview.add_patch(Rectangle((y-half, x-half), 2*half, 2*half, fill=False, color="black", lw=.75))
    overview.set_ylabel("Forward (m)", fontsize=6.8, labelpad=1)
    detail.set(xlim=(y+half, y-half), ylim=(x-half, x+half),
               xticks=np.arange(np.ceil(y-half), np.floor(y+half)+1),
               yticks=np.arange(np.ceil(x-half), np.floor(x+half)+1))
    for ax in (overview, detail):
        ax.set_xlabel("Lateral (m)", fontsize=6.8, labelpad=1)
    label(.06, .145, "Minimum footprint clearance from 2 m forward", size=8.1)
    for xpos, (score, _), name, color in zip((.06, .51), minima, ("Straight", "GEAR-Nav"), (STRAIGHT, ORANGE)):
        label(xpos, .096, f"{name}  {score:+.2f} m", size=10, color=color, weight="bold")
    bar = fig.colorbar(raster, cax=axes(.6, .041, .29, .009), orientation="horizontal",
                       ticks=[-1, 0, 1], extend="both")
    bar.ax.set_title("Map clearance (m)", size=6.2, pad=1)
    bar.ax.tick_params(labelsize=5.8, length=1.5, pad=1)
    keys = [Line2D([], [], ls=(0, (2, 1)), color=STRAIGHT, label="Straight"),
            Line2D([], [], color=ORANGE, label="GEAR-Nav")]
    fig.legend(handles=keys, loc="center left", bbox_to_anchor=((column+.045)/ncols, .046),
               ncol=2, frameon=False, handlelength=1.3, handletextpad=.3, columnspacing=.6, fontsize=6.8)


def main():
    plt.rcParams.update({"font.family": "serif", "font.serif": [style.FONT, "STIXGeneral"],
                         "svg.fonttype": "none", "pdf.fonttype": 42, "svg.hashsalt": "gear-scene-drafts"})
    with np.load(ROOT / "eval/best_model/model_paths_checkpoint57500.npz") as archive:
        assert int(archive["checkpoint"]) == 57500 and str(archive["mode"]) == "model_only"
        inputs = [load_case(archive, case) for case in CASES]
    for columns, stem in [([0], STEMS[0]), ([1], STEMS[1]), ([0, 1], "first_drafts")]:
        fig = plt.figure(figsize=(3.54*len(columns), 4.95))
        for column, idx in enumerate(columns):
            draw_scene(fig, column, len(columns), CASES[idx], inputs[idx])
        extensions = ["pdf", "svg"] if len(columns) == 1 else ["pdf", "png"]
        for ext in extensions:
            metadata = {"svg": {"Date": None}, "pdf": {"CreationDate": None}, "png": {}}[ext]
            fig.savefig(OUT / f"{stem}.{ext}", dpi=240, metadata=metadata)
        plt.close(fig)


if __name__ == "__main__":
    main()
