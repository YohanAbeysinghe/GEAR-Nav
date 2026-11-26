"""Draw Option A from a recorded RGB–ESDF pair and explicitly authored paths."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
from matplotlib.colors import Normalize
from matplotlib.patches import Arc
from matplotlib.patches import FancyArrowPatch
from matplotlib.patches import Rectangle
import matplotlib.patheffects as effects
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
FIGS = HERE.parents[1]
ROOT = FIGS.parent
sys.path.insert(0, str(FIGS))
import figure_style as style  # noqa: E402

INK = "#21282C"
MUTED = "#46545A"
ORACLE = "#006F75"
GEAR = "#D64A10"
GOLD = style.WAYPOINT_FILL
OUTLINE = "#62686E"
RULE = "#CCD0CD"
FONT = "STIXGeneral"
SANS = "DejaVu Sans"
HALO = [effects.Stroke(linewidth=2.8, foreground="white"), effects.Normal()]
OVERVIEW = (-3.4, 4.6, 0.0, 11.4)  # right min, right max, forward min, forward max
DETAIL = (-0.48, 2.28, 4.18, 6.66)
NORM = Normalize(-1, 1, clip=True)


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(data_root):
    clip, frame, goal_id = "Amsterdam_3", "000657", 1
    for split, expected in [("eval", True), ("train", False)]:
        members = (ROOT / f"configs/splits/{split}_clip_ids.txt").read_text().split()
        assert (clip in members) == expected
    folder = data_root / clip
    with (folder / "metadata.jsonl").open() as rows:
        record = next(r for r in map(json.loads, rows) if r["sample_id"] == frame)
    config = read_json(folder / "manifest.json")["esdf_config"]
    paths = {
        name: folder / relative
        for name, relative in {
            "rgb": record["image_path"],
            "esdf": record["path_generation"]["esdf_path_used"],
            "point_map": record["pointcloud_path"],
        }.items()
    }
    grid = np.load(paths["esdf"], allow_pickle=False)
    resolution = config["resolution_m"]
    assert grid.shape == (1000, 1250) and resolution == 0.02
    # Keep the source cells losslessly. The display axes run right and forward.
    full_edges = (config["y_range_m"][0], config["x_range_m"][0])
    rmin, rmax, fmin, fmax = OVERVIEW
    j0, j1 = np.rint((np.array([-rmax, -rmin]) - full_edges[0]) / resolution).astype(int)
    i0, i1 = np.rint((np.array([fmin, fmax]) - full_edges[1]) / resolution).astype(int)
    displayed = grid[j0:j1, i0:i1].T[:, ::-1]
    np.savez_compressed(HERE / "esdf_crop.npz", signed_distance_m=displayed)
    shutil.copyfile(paths["rgb"], HERE / "camera.jpg")

    goal_xy = np.asarray(record["sampled_goals"][goal_id]["goal_xy_m"])
    with np.load(paths["point_map"], allow_pickle=False) as cloud:
        points = cloud["points_map"]
        valid = cloud["mask"] & np.isfinite(points).all(axis=2)
        rotation = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
        correction = np.array(record["esdf_ground_alignment"]["correction_rotation_matrix"])
        transform = correction @ rotation
        translation = np.array([0.0, 0.0, config["camera_height_m"]])
        h, w = valid.shape
        base = points[valid] @ transform.T + translation
        # Anchor the goal label at the nearest recorded ground return in XY.
        floor = np.abs(base[:, 2]) < 0.30
        nearby = np.flatnonzero(floor)
        nearest = nearby[np.argmin(np.linalg.norm(base[floor, :2] - goal_xy, axis=1))]
        goal_match = float(np.linalg.norm(base[nearest, :2] - goal_xy))
        assert goal_match < 0.025
        goal_rc = np.column_stack(np.where(valid))[nearest]
        # This source point lies on the visible shaft of the foreground bollard.
        post_rc = np.array([207, 226])
        assert valid[tuple(post_rc)]
        post_xyz = points[tuple(post_rc)] @ transform.T + translation
        assert 0.15 < post_xyz[2] < 0.85

        def image_uv(rc):
            return ((np.asarray(rc)[::-1] + 0.5) / [w, h]).tolist()

        uv_depth = np.stack([points[tuple(goal_rc)], points[tuple(post_rc)]])
        projected = uv_depth[:, :2] / uv_depth[:, 2:] * np.diag(cloud["intrinsics"])[:2] + cloud["intrinsics"][:2, 2]
        np.testing.assert_allclose(projected, [image_uv(goal_rc), image_uv(post_rc)], atol=2e-5)
        image_size = cloud["full_image_size"].tolist()
        with Image.open(paths["rgb"]) as photo:
            assert list(photo.size) == image_size
    write_json(
        HERE / "scene.json",
        dict(
            clip=clip,
            frame=frame,
            timestamp_s=record["timestamp_sec"],
            video=record["video_source"],
            sampled_goal_index=goal_id,
            goal_forward_left_m=goal_xy.tolist(),
            goal_image_uv=image_uv(goal_rc),
            goal_ground_return_xy_error_m=goal_match,
            bollard_image_uv=image_uv(post_rc),
            bollard_surface_forward_left_up_m=post_xyz.tolist(),
            rgb_size_wh=image_size,
            esdf_extent_right_forward_m=list(OVERVIEW),
            esdf_resolution_m=resolution,
            footprint_radius_m=config["robot_radius_m"],
            unknown_is_occupied=config["unknown_is_occupied"],
            source_paths={k: str(p.relative_to(data_root)) for k, p in paths.items()},
            source_sha256={k: sha(p) for k, p in paths.items()},
            esdf_crop_sha256=sha(HERE / "esdf_crop.npz"),
            esdf_crop_rows_cols=[j0.item(), j1.item(), i0.item(), i1.item()],
        ),
    )


def angle(u, v):
    u, v = u.ravel(), v.ravel()
    return np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1)))


def draw_arrow(ax, start, end, color):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=9.8,
        shrinkA=0,
        shrinkB=0,
        linewidth=1.7,
        color=color,
        joinstyle="round",
        capstyle="round",
        zorder=7,
        clip_on=True,
    )
    arrow.set_path_effects([effects.Stroke(linewidth=3.0, foreground="white"), effects.Normal()])
    ax.add_patch(arrow)


def render():
    scene = read_json(HERE / "scene.json")
    assert sha(HERE / "camera.jpg") == scene["source_sha256"]["rgb"]
    assert sha(HERE / "esdf_crop.npz") == scene["esdf_crop_sha256"]
    art = read_json(HERE / "artwork.json")
    path, oracle, gear = (np.array(art[k]) for k in ("candidate", "oracle_displacement", "gear_displacement"))
    p, q = art["highlight_waypoints"]
    assert path.shape == oracle.shape == gear.shape == (16, 2)
    for coords in (path, path + oracle, path + gear):
        assert np.all(coords[0] == 0) and np.max(np.linalg.norm(np.diff(coords, axis=0), axis=1)) < 1.0
    np.testing.assert_array_equal(oracle[-1], gear[-1])
    with np.load(HERE / "esdf_crop.npz", allow_pickle=False) as archive:
        field = archive["signed_distance_m"]
    rmin, rmax, fmin, fmax = scene["esdf_extent_right_forward_m"]
    res = scene["esdf_resolution_m"]
    radius = scene["footprint_radius_m"]
    rcoords = rmin + (np.arange(field.shape[1]) + 0.5) * res
    fcoords = fmin + (np.arange(field.shape[0]) + 0.5) * res
    np.testing.assert_allclose([rcoords[-1] + res / 2, fcoords[-1] + res / 2], [rmax, fmax])

    def clearance(points):
        ij = (points - [rmin, fmin]) / res - 0.5
        return map_coordinates(field, ij[:, ::-1].T, order=1, mode="constant", cval=np.nan) - radius

    q_clearance = clearance(np.stack([path[q] + oracle[q], path[q] + gear[q]]))
    assert q_clearance[0] > 0 > q_clearance[1]
    whole = angle(oracle[1:], gear[1:])
    post_x, post_y, _ = scene["bollard_surface_forward_left_up_m"]
    assert abs(clearance(np.array([[-post_y, post_x]])).item() + radius) < 0.12

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": [style.FONT, FONT, "Liberation Serif"],
            "font.size": 8,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "gear-illustrative-correction",
        }
    )
    width, height = 7.08, 5.64
    fig = plt.figure(figsize=(width, height), facecolor="white")

    def box(x, y, w, h, **opts):
        # Inches from the top-left, consistent with the print layout.
        return fig.add_axes([x / width, 1 - (y + h) / height, w / width, h / height], **opts)

    def text(x, y, value, **kwargs):
        return fig.text(x / width, 1 - y / height, value, va="top", **kwargs)

    def rule(x1, x2, y):
        fig.add_artist(
            plt.Line2D(
                [x1 / width, x2 / width], [1 - y / height] * 2, transform=fig.transFigure, color=RULE, linewidth=0.55
            )
        )

    def heading(x, y, letter, title):
        text(x, y, f"({letter})  {title}", size=10.1, weight="bold")

    def zoom_map(ax, limits, rticks, fticks):
        raster = ax.imshow(
            field - radius,
            origin="lower",
            extent=(rmin, rmax, fmin, fmax),
            interpolation="nearest",
            cmap=style.TEASER_ESDF_CMAP,
            norm=NORM,
        )
        contour = ax.contour(
            rcoords,
            fcoords,
            field,
            levels=[radius],
            colors=[OUTLINE],
            linestyles=[(0, (2, 1.8))],
            linewidths=0.75,
            zorder=3,
        )
        contour.set_gid(f"zero-footprint-clearance-{ax.get_label()}")
        ax.set(xlim=limits[:2], ylim=limits[2:], xticks=rticks, yticks=fticks, aspect="equal")
        for spine in ax.spines.values():
            spine.set_linewidth(0.48)
            spine.set_color("#656C6C")
        ax.tick_params(labelsize=6.8, length=2, pad=1.8)
        ax.set_xlabel("Camera right (m)", fontsize=7.3, labelpad=1)
        ax.set_ylabel("Forward (m)", fontsize=7.3, labelpad=2)
        return raster

    def pathline(ax, vertices, color, width, linestyle, name):
        (line,) = ax.plot(
            *vertices.T,
            color=color,
            lw=width,
            ls=linestyle,
            zorder=4,
            solid_capstyle="round",
            dash_capstyle="round",
            gid=name,
        )
        line.set_path_effects([effects.Stroke(linewidth=width + 1.25, foreground="white"), effects.Normal()])

    def dot(ax, point, size=19):
        ax.scatter(*point, s=size, facecolor=GOLD, edgecolor=INK, lw=0.65, zorder=8)

    text(0.08, 0.035, "Which way should this waypoint move?", fontsize=15.2, weight="bold")
    text(0.09, 0.32, "ILLUSTRATIVE", family=SANS, size=7.0, weight="bold", color="#815922")
    text(1.06, 0.30, "Recorded camera frame and ESDF. All paths and arrows are hand-drawn.", size=9.1, color=MUTED)
    rule(0.08, 7.0, 0.53)
    heading(0.08, 0.63, "a", "Camera view and goal")
    heading(3.79, 0.63, "b", "The candidate on the ESDF")
    photo = box(0.08, 0.89, 3.37, 1.90)
    with Image.open(HERE / "camera.jpg") as im:
        im.thumbnail((1200, 675), Image.Resampling.LANCZOS)
        photo.imshow(im, extent=(0, 1, 1, 0), aspect="auto")
    goal_uv = scene["goal_image_uv"]
    photo.scatter(*goal_uv, marker="*", s=99, facecolor=GOLD, edgecolor="#23282B", lw=0.9, zorder=4)
    post_uv = scene["bollard_image_uv"]
    photo.annotate(
        "Bollard",
        xy=post_uv,
        xytext=(0.37, 0.84),
        color="white",
        size=7.8,
        bbox=dict(boxstyle="round,pad=.16", facecolor="#26343B", edgecolor="none", alpha=0.92),
        arrowprops=dict(arrowstyle="-", color="white", lw=0.8, shrinkA=2, shrinkB=1),
    )
    photo.set(xlim=(0, 1), ylim=(1, 0))
    photo.axis("off")
    text(0.09, 2.84, "Amsterdam canal-side walkway  ·  Frame 000657", size=7.8, color=MUTED)

    overview = box(4.06, 0.88, 1.55, 1.95, label="overview")
    raster = zoom_map(overview, OVERVIEW, [-2, 0, 2, 4], [0, 2, 4, 6, 8, 10])
    pathline(overview, path, INK, 1.2, "-", "authored-candidate-overview")
    overview.scatter(*path.T, s=4.5, facecolor="white", edgecolor=INK, lw=0.4, zorder=5)
    gforward, gleft = scene["goal_forward_left_m"]
    overview.scatter(-gleft, gforward, marker="*", s=65, facecolor=GOLD, edgecolor=INK, lw=0.75, zorder=8)
    xlo, xhi, ylo, yhi = DETAIL
    overview.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo, fill=False, lw=1, zorder=5, ec=INK))
    for idx in (p, q):
        dot(overview, path[idx], size=13)
    text(5.78, 0.94, "Map key", size=8.9, weight="bold")
    key = box(5.77, 1.14, 1.23, 1.0)
    key.set(xlim=(0, 1), ylim=(0, 1))
    key.axis("off")
    key.scatter(0.09, 0.89, marker="*", s=55, facecolor=GOLD, edgecolor=INK, lw=0.7)
    key.plot([0.01, 0.17], [0.65, 0.65], color=INK, lw=1.3)
    key.plot([0.01, 0.17], [0.41, 0.41], color=OUTLINE, ls=(0, (2, 1.8)), lw=1.1)
    key.add_patch(Rectangle((0.025, 0.13), 0.13, 0.10, fill=False, lw=0.8, ec=INK))
    for yy, val in [(0.89, "Fixed goal"), (0.65, "Candidate"), (0.41, "Zero clearance"), (0.18, "Detail in (c)")]:
        key.text(0.24, yy, val, va="center", size=7.5)
    cb = fig.colorbar(
        raster, cax=box(5.79, 2.38, 1.10, 0.075), orientation="horizontal", ticks=[-1, 0, 1], extend="both"
    )
    cb.ax.tick_params(labelsize=6.5, pad=1, length=2)
    cb.ax.set_title("Footprint clearance (m)", fontsize=7.4, loc="left", pad=3)
    cb.outline.set_linewidth(0.45)
    text(5.79, 2.67, "ESDF − 0.50 m radius", size=6.9, color=MUTED)
    rule(0.08, 7.0, 3.15)
    heading(0.08, 3.24, "c", "Two updates from the same waypoints")
    heading(3.79, 3.24, "d", "How much do the directions differ?")
    detail = box(0.35, 3.56, 2.02, 1.77, label="detail")
    zoom_map(detail, DETAIL, [0, 1, 2], [4.5, 5.5, 6.5])
    pathline(detail, path + oracle, ORACLE, 1.05, (0, (3, 2)), "illustrated-oracle-proposal")
    pathline(detail, path + gear, GEAR, 1.05, "-", "illustrated-gear-proposal")
    pathline(detail, path, INK, 0.88, "-", "authored-current-path-detail")
    for idx in (p, q):
        for delta, color in [(oracle, ORACLE), (gear, GEAR)]:
            draw_arrow(detail, path[idx], path[idx] + delta[idx], color)
        dot(detail, path[idx], size=17)
    for idx, tag, off in [(p, "P", (-11, -3)), (q, "Q", (-11, 1))]:
        detail.annotate(
            tag,
            path[idx],
            xytext=off,
            textcoords="offset points",
            size=8,
            weight="bold",
            ha="center",
            va="center",
            zorder=10,
            path_effects=HALO,
        )
    detail.scatter(-post_y, post_x, s=9, color=INK, edgecolor="white", lw=0.45, zorder=8)
    detail.annotate(
        "Bollard",
        (-post_y, post_x),
        (-0.38, 5.57),
        ha="left",
        va="center",
        size=6.5,
        zorder=10,
        path_effects=HALO,
        arrowprops=dict(arrowstyle="-", lw=0.65, color=INK, shrinkA=1, shrinkB=2),
    )
    text(2.47, 3.67, "Clearance at Q", size=8.6, weight="bold")
    text(2.47, 3.90, "At the arrow tips", size=7.3, color=MUTED)
    for yy, color, name, reading in [
        (4.17, ORACLE, "Oracle sketch", q_clearance[0]),
        (4.76, GEAR, "GEAR sketch", q_clearance[1]),
    ]:
        k = box(2.47, yy, 0.96, 0.16)
        k.set(xlim=(0, 1), ylim=(0, 1))
        k.axis("off")
        k.annotate(
            "",
            (0.26, 0.5),
            (0, 0.5),
            arrowprops=dict(arrowstyle="-|>", lw=1.6, color=color, shrinkA=0, shrinkB=0, mutation_scale=8),
        )
        k.text(0.35, 0.50, name, va="center", size=8.3)
        value = f"{reading:+.2f} m".replace("-", "−")
        text(2.47, yy + 0.19, value, size=10, weight="bold", color=color)

    def direction_glyph(x, idx, tag):
        # Equal-length arrows isolate direction in (d). Panel (c) uses metric lengths.
        glyph = box(x, 3.58, 0.76, 0.64, label=f"direction-{tag}")
        glyph.set(xlim=(-0.25, 1.10), ylim=(-0.15, 1.13), aspect="equal")
        glyph.axis("off")
        angles = []
        for delta, color in [(oracle[idx], ORACLE), (gear[idx], GEAR)]:
            unit = delta / np.linalg.norm(delta)
            draw_arrow(glyph, (0, 0), unit, color)
            angles.append(np.degrees(np.arctan2(unit[1], unit[0])))
        glyph.add_patch(Arc((0, 0), 0.68, 0.68, theta1=min(angles), theta2=max(angles), color=INK, lw=0.7, zorder=9))
        dot(glyph, (0, 0), size=11)

    text(3.81, 3.47, "Equal-length arrows show direction.", size=7.0, color=MUTED)
    direction_glyph(3.97, p, "P")
    direction_glyph(5.53, q, "Q")
    text(3.81, 4.24, f"P   Approach  ·  {angle(oracle[p], gear[p]):.0f}°", size=8.2)
    text(5.42, 4.24, f"Q   By bollard  ·  {angle(oracle[q], gear[q]):.0f}°", size=8.2)
    text(3.81, 4.62, "All 15 movable waypoints", size=8.6, weight="bold")
    axis = box(3.84, 4.80, 2.92, 0.45)
    axis.set_xlim(-4, 184)
    axis.set_ylim(0, 1)
    axis.axis("off")
    axis.plot([0, 180], [0.36, 0.36], color="#899294", lw=1.1)
    for tt, lab in [(0, "0°"), (90, "90°"), (180, "180°")]:
        axis.plot([tt, tt], [0.27, 0.45], color=MUTED, lw=0.8)
        axis.text(tt, 0.13, lab, ha="center", va="top", size=6.8)
    axis.scatter(whole, 0.36, s=20, facecolor=INK, edgecolor="white", lw=0.7, zorder=5)
    axis.text(whole, 0.61, f"{whole:.0f}°", ha="center", size=9.1, weight="bold")
    text(3.81, 5.36, "One mark here for the drawing. In a held-out test,", size=7.5, color=MUTED)
    text(3.81, 5.49, "each recorded frame–goal pair would add one.", size=7.5, color=MUTED)
    for ext, metadata in [("svg", {"Date": None}), ("pdf", {"CreationDate": None}), ("png", {})]:
        fig.savefig(HERE / f"illustrative_update.{ext}", dpi=240, metadata=metadata)
    plt.close(fig)
    # Matplotlib emits optional trailing spaces inside SVG path commands.
    svg = HERE / "illustrative_update.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    print(
        f"Drawing: path angle {whole:.2f} deg; P {angle(oracle[p], gear[p]):.2f}, "
        f"Q {angle(oracle[q], gear[q]):.2f}; Q tip clearances {q_clearance.round(3)} m"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture",
        type=Path,
        metavar="DATA_ROOT",
        help="Refresh the lossless ESDF crop, original photograph and provenance",
    )
    args = parser.parse_args()
    if args.capture is not None:
        capture(args.capture.resolve())
    render()
