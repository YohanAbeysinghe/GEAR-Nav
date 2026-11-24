"""Prepare the two small, matched scene examples used in the Canva method figures."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

DEST = Path(__file__).resolve().parent / "method_examples"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save_example(name, field, grid, limits, **arrays):
    # Retain native cells, including a cell beyond each viewport edge for interpolation.
    forward_max, left_min, left_max = limits
    res = float(grid[2])
    end = min(field.shape[1], int(np.ceil((forward_max - grid[0]) / res)) + 2)
    start = max(0, int(np.floor((left_min - grid[1]) / res)) - 2)
    stop = min(field.shape[0], int(np.ceil((left_max - grid[1]) / res)) + 2)
    local_grid = np.array([grid[0], grid[1] + start * res, res, grid[3]], np.float64)
    output = DEST / (name + ".npz")
    np.savez_compressed(output, esdf=field[start:stop, :end], grid=local_grid,
                        limits=np.array(limits, np.float64), **arrays)
    return output


def prepare(root):
    from astar.evaluation import aggregation as evaluation

    DEST.mkdir(exist_ok=True)
    figs = root / "figs"
    clips = figs / "egocentric_esdf/selected/03_Japan_5_000398"
    source = json.loads((clips / "provenance.json").read_text())
    config_path = root / "checkpoints/astar_fulltrain_depth14_from35000_20260930/monitoring/configuration.json"
    values = evaluation.load_training_config(config_path)
    kernels = evaluation.build_kernels(values, SimpleNamespace(batch_size=1),
                                       evaluation.build_energy_config(values),
                                       prior_seed=0, safety_sample_spacing_m=.02)

    def correction(path, field, goal, grid):
        metrics = {"esdf": field[None], "goal_xy": goal[None]}
        for key, value in zip(("esdf_x_min", "esdf_y_min", "esdf_resolution", "robot_radius_m"), grid):
            metrics[key] = np.array([value], dtype=np.float32)
        label, info = kernels.query_oracle(path[None], metrics)
        if float(info["oracle_acceptance_rate"]) != 1:
            raise ValueError("Expected an accepted finite correction for this recorded example.")
        return np.asarray(label)[0]

    grid_config = source["esdf_config"]
    grid = [grid_config["x_range_m"][0], grid_config["y_range_m"][0],
            grid_config["resolution_m"], grid_config["robot_radius_m"]]
    # Cross-check the query against an independently captured oracle target.
    with np.load(figs / "pipeline/assets/scene_data.npz") as control:
        predicted = correction(control["path_0"], control["esdf"], control["goal"], grid)
        np.testing.assert_allclose(predicted, control["oracle_direction"], rtol=2e-5, atol=2e-5)
    recorded = figs / "teaser/captured_paths.npz"
    with np.load(recorded) as states, np.load(clips / "esdf.npz") as geometry:
        ids = (states["clip_ids"] == "Japan_5") & (states["sample_ids"] == "000398") & (states["goal_indices"] == 3)
        row, = np.flatnonzero(ids)
        assert str(states["mode"]) == "model_only"
        current, following, goal = states["paths_2"][row], states["paths_3"][row], states["goals"][row]
        field = geometry["esdf"]
        np.testing.assert_array_equal(np.load(source["esdf_source"]), field)
        target = correction(current, field, goal, grid)
        rainy = save_example("rainy-sidewalk", field, grid, (15., -6., 6.), goal=goal,
                             path=current, next_path=following, target=target)
    photo = DEST / "rainy-sidewalk.jpg"
    assert digest(clips / "rgb.jpg") == source["rgb_source_sha256"]
    with Image.open(clips / "rgb.jpg") as im:
        im.thumbnail((640, 360), Image.Resampling.LANCZOS)
        im.save(photo, quality=92, subsampling=0)

    record = json.loads((figs / "video/provenance.json").read_text())
    ref = next(s for s in record["scenes"] if (s["clip_id"], s["sample_id"]) == ("Ottawa_1", "001351"))
    assert record["complete_condition_fingerprint_verified"]
    archive = Path(record["source_archive"])
    assert digest(archive) == record["source_sha256"]
    replay = figs / "video" / ref["local_dir"] / "replay.npz"
    with np.load(replay) as selected, np.load(archive) as full:
        depths = np.array([0, 1, 2], dtype=np.int32)
        paths = full["visited_paths"][depths, ref["batch"], ref["slot"]]
        labels = full["oracle_directions"][depths, ref["batch"], ref["slot"]]
        np.testing.assert_array_equal(selected["paths"][:3], paths)
        np.testing.assert_array_equal(selected["directions"][:3], labels)
        np.testing.assert_array_equal(np.load(ref["esdf_path"]), selected["esdf"])
        np.testing.assert_allclose(selected["goal"], ref["goal_xy_m"], atol=1e-6)
        assert digest(Path(ref["esdf_path"])) == ref["esdf_sha256"]
        # The archive logs the mean energy before and after each learned frontier step.
        rounds = json.loads(full["metadata_json"].item())["round_records"]
        np.testing.assert_array_equal([r["round"] for r in rounds], np.arange(1, len(rounds) + 1))
        np.testing.assert_allclose([r["energy_before"] for r in rounds[1:]],
                                   [r["energy_after"] for r in rounds[:-1]], rtol=1e-5)
        mean_energy = np.array([rounds[0]["energy_before"], *[r["energy_after"] for r in rounds]])
        _, batches, batch_size, _, _ = full["visited_paths"].shape
        paths_per_round = batches * batch_size
        ottawa = save_example("ottawa-replay", selected["esdf"], selected["grid"],
                              (13., -6., 6.), goal=selected["goal"], depths=depths,
                              paths=paths, targets=labels, mean_energy=mean_energy, paths_per_round=paths_per_round)

    notes = {
        "figure_2": {"scene": "Japan_5/000398", "display_name": "Rainy sidewalk",
                     "goal_kind": "sampled", "goal_index": 3, "checkpoint": 57500,
                     "source": "figs/teaser/captured_paths.npz", "source_sha256": digest(recorded),
                     "esdf_source_sha256": source["esdf_source_sha256"], "rgb_source_sha256": source["rgb_source_sha256"],
                     "config_sha256": digest(config_path), "model_only_steps": [2, 3],
                     "oracle_waypoints": [5, 8, 11, 15], "target_display_multiplier": .8,
                     "interpretation": "Illustration of the training target on a validation frame. The exact oracle is evaluated on the saved step-2 path; the plotted step-3 path is the recorded model-only update."},
        "figure_3": {"scene": "Ottawa_1/001351", "goal_kind": ref["goal_kind"], "goal_index": ref["goal_index"],
                     "source": str(archive.relative_to(root)), "source_sha256": record["source_sha256"],
                     "source_recovery": "figs/video/provenance.json", "esdf_source_sha256": ref["esdf_sha256"],
                     "batch": ref["batch"], "slot": ref["slot"], "condition_fingerprint": record["fingerprint"],
                     "energy_curve": {"metric": "mean path energy", "initial": "round 1 energy_before",
                                      "following": "energy_after for rounds 1 through 14",
                                      "paths_per_round": paths_per_round, "unit": "objective value"},
                     "depths": [0, 1, 2], "oracle_waypoints": [5, 8, 11, 15], "target_display_multiplier": .8,
                     "interpretation": "Consecutive training frontiers and oracle labels for one condition. One-based bank B_i holds the examples newly labelled at stored depth i-1."},
        "files_sha256": {p.name: digest(p) for p in (rainy, photo, ottawa)}
    }
    (DEST / "provenance.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="GEAR-Nav checkout containing the original local captures and dataset")
    prepare(parser.parse_args().workspace.resolve())
