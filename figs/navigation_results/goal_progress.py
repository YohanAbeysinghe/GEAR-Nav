"""Plot paired single-plan endpoint errors from the saved evaluation paths."""

import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import COLORS, FONT, INK, MUTED, TEASER_STAGE_COLORS

CACHE = HERE / "endpoints.csv"
DEPTHS = (0, 14, 20, 30)
HORIZON_M = 15  # 15 segments, each bounded by one meter at this checkpoint.


def extract(root):
    """Join the model-independent prior and learned paths by frame and sampled goal."""
    evaluation = root / "eval"
    config = json.loads((evaluation / "evaluation_config.json").read_text())
    with (evaluation / "examples.jsonl").open() as source:
        records = (json.loads(line) for line in source)
        prior_ids = {r["dataset_index"]: r for r in records if r["mode"] == "prior" and r["depth"] == 0}

    model_file = evaluation / "best_model/model_paths_checkpoint57500.npz"
    with np.load(model_file) as model, np.load(evaluation / "final_paths.npz") as baseline:
        meta = json.loads(str(model["metadata_json"]))
        if (meta["checkpoint"], meta["parameter_source"], meta["mode"], meta["trained_depth"]) != (
            57500, "raw", "model_only", 14
        ):
            raise ValueError("Unexpected model or inference configuration")
        checkpoint_name = Path(meta["checkpoint_root"]).name
        training = json.loads((root / "checkpoints" / checkpoint_name / "monitoring/configuration.json").read_text())
        prior_settings = [k for k in training if k.startswith("prior_")]
        prior_settings.extend(("action_horizon", "action_dim", "max_step_length_m", "path_detour_factor"))
        if (meta["seed"] != config["seed"] or meta["seed"] != 0 or
                any(training[k] != config["training_values"][k] for k in prior_settings)):
            raise ValueError("The two evaluations used different initializers")
        if (training["action_horizon"] - 1) * training["max_step_length_m"] != HORIZON_M:
            raise ValueError("The checkpoint uses a different path-length cap")

        def split(name):
            lines = (root / f"configs/splits/{name}_clip_ids.txt").read_text().splitlines()
            return {line.strip() for line in lines if line.strip() and not line.startswith("#")}

        clips = set(model["clip_ids"])
        if clips != split("eval") or clips & split("train"):
            raise ValueError("Unexpected train/evaluation clip membership")
        priors = {r["dataset_index"]: baseline[r["array_key"]] for r in json.loads(str(baseline["metadata_json"]))
                  if r["mode"] == "prior" and r["checkpoint"] == "baseline"}
        indices = model["dataset_indices"].tolist()
        if len(indices) != 300 or len(set(indices)) != len(indices) or set(indices) != set(priors) or set(indices) != set(prior_ids):
            raise ValueError("Expected one matched prior per evaluation condition")
        paths = {0: np.stack([priors[i] for i in indices])}
        paths.update({depth: model[f"paths_{depth}"] for depth in DEPTHS[1:]})
        for values in paths.values():
            if values.shape != (len(indices), 16, 2) or not np.isfinite(values).all():
                raise ValueError("Missing or invalid saved waypoints")
        keys = zip(model["clip_ids"].tolist(), model["sample_ids"].tolist(), model["goal_indices"].tolist())
        goals = model["goals"]
        rows = []
        for j, (i, (clip, frame, goal)) in enumerate(zip(indices, keys, strict=True)):
            r = prior_ids[i]
            if ((clip, frame, goal, "sampled") != (r["clip_id"], r["sample_id"], r["goal_index"], r["goal_kind"])
                    or not np.array_equal(goals[j], [r["goal_x_m"], r["goal_y_m"]])):
                raise ValueError(f"Frame or goal mismatch for dataset index {i}")
            row = dict(clip_id=clip, frame_id=frame, sampled_goal=goal,
                       goal_x_m=float(goals[j, 0]), goal_y_m=float(goals[j, 1]))
            for depth, all_paths in paths.items():
                path = all_paths[j].astype(float)
                row[f"end_{depth}_x_m"], row[f"end_{depth}_y_m"] = path[-1]
                if depth in (0, 14):
                    row[f"length_{depth}_m"] = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
            rows.append(row)
    with CACHE.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render():
    with CACHE.open() as source:
        rows = list(csv.DictReader(source))

    def xy(prefix):
        return np.array([[float(r[f"{prefix}_x_m"]), float(r[f"{prefix}_y_m"])] for r in rows])

    goals = xy("goal")
    distance = np.linalg.norm(goals, axis=1)
    error = {k: np.linalg.norm(xy(f"end_{k}") - goals, axis=1) for k in DEPTHS}
    gain = error[14] - error[30]
    prior = TEASER_STAGE_COLORS["initial"]
    learned = COLORS[14]
    plt.rcParams.update({
        "font.family": "serif", "font.serif": [FONT, "STIXGeneral", "Liberation Serif"],
        "font.size": 8.5, "axes.labelcolor": INK, "text.color": INK,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.65, "xtick.color": INK, "ytick.color": INK,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "svg.fonttype": "none", "pdf.fonttype": 42,
        "svg.hashsalt": "gear-nav-endpoints",
    })
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.08, 2.74), gridspec_kw={"width_ratios": [1.14, 1]})
    fig.subplots_adjust(left=.075, right=.981, top=.86, bottom=.185, wspace=.31)
    for axis in (left, right):
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(length=3, width=.6)
        axis.grid(axis="y", color="#e5e6e7", linewidth=.55)
        axis.set_axisbelow(True)

    left.set_title("(a)  Goal error by target distance", loc="left", fontweight="bold", fontsize=10)
    left.scatter(distance, error[0], s=8, facecolors="none", edgecolors=prior, linewidths=.55,
                 alpha=.80, label="Initial path")
    left.scatter(distance, error[14], s=8, c=learned, linewidths=0, alpha=.75, label="14 updates")
    limit = 28
    left.plot([0, HORIZON_M, limit], [0, 0, limit - HORIZON_M], "--", linewidth=.95,
              color="#334957", label="Lower bound from 15 m horizon")
    left.set(xlim=(0, limit), ylim=(-.6, 26), xlabel="Robot-to-goal distance (m)", ylabel="Endpoint-to-goal distance (m)",
             xticks=np.arange(0, 26, 5), yticks=np.arange(0, 26, 5))
    left.legend(loc="upper left", frameon=False, fontsize=7.7, labelspacing=.40, handlelength=1.65,
                handletextpad=.45, borderaxespad=.30, markerscale=1.55)

    right.set_title("(b)  Change from 14 to 30 updates", loc="left", fontweight="bold", fontsize=10)
    width = .1
    extent = np.ceil(abs(gain).max() / width) * width
    edges = np.arange(-round(extent / width), round(extent / width) + 1) * width
    counts, _ = np.histogram(gain, bins=edges)
    right.bar(edges[:-1], counts, width=width, align="edge", color=[prior if v < 0 else learned for v in edges[:-1]],
              edgecolor="white", linewidth=.50)
    right.axvline(0, color=INK, linewidth=.8)
    right.set(xlim=(-extent, extent), ylim=(0, counts.max() * 1.26), xlabel="Reduction in endpoint-to-goal distance (m)",
              ylabel="Frame–goal pairs", xticks=[-1, -.5, 0, .5, 1])
    right.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    for x, label in [(0.25, f"{(gain < 0).sum()} farther"), (0.75, f"{(gain > 0).sum()} closer")]:
        right.text(x, .96, label, transform=right.transAxes, ha="center", va="top", fontsize=8.5)
    for extension, metadata in (("svg", {"Date": None}), ("pdf", {"CreationDate": None}), ("png", {})):
        fig.savefig(HERE / f"goal_progress.{extension}", dpi=260, metadata=metadata)
    svg = HERE / "goal_progress.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(f"{len(rows)} paired examples, {len(set(r['clip_id'] for r in rows))} evaluation clips")
    for depth in DEPTHS:
        print(f"{depth:2d} updates: median endpoint error {np.median(error[depth]):.4f} m")
    print(f"{(error[14] < error[0]).sum()} closer at 14 than at initialization")
    print(f"Median paired reduction at 30 versus 14: {np.median(gain):.4f} m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", metavar="WORKSPACE", type=Path,
                        help="refresh endpoints.csv from the archived evaluations before plotting")
    args = parser.parse_args()
    if args.extract:
        extract(args.extract)
    render()
