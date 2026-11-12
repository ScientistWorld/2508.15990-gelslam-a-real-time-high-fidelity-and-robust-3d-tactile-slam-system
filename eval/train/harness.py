"""Run every registered method on rendered tactile episodes and score the outputs.

A method is any directory under checkpoints/ holding a predict.json:

    {"name": "my_method",
     "command": ["python", "-m", "my_pkg.run", "--input", "{input}", "--output", "{output}"]}

The command is run once per episode from the workspace root. {input} is an
.npz file with the observations only (gradients, heights, contact_masks,
mm_per_pixel); {output} is an empty directory where the method must write
poses.npy (N x 4 x 4 sensor poses, mm) and may write loops.json. Any other
directory under checkpoints/ that holds model or prediction artifacts but no
predict.json is scored as a failed method, because it cannot be run on
held-out inputs.

Every scored number is recomputed here from poses.npy and loops.json. A method
that crashes, times out, writes malformed or impossible values, or accepts too
many false loop constraints receives the worst value of every metric in every
experiment.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.spatial.transform import Rotation

EXPERIMENTS = {
    "long_horizon_tracking": False,  # value: episode has simulated contact loss
    "relocalization_after_contact_loss": True,
}
METRICS = ("rotation_mae_deg", "translation_mae_mm", "rotation_p95_deg", "translation_p95_mm", "false_loop_excess")
ROT_CAP_DEG = 90.0
TRANS_CAP_MM = 30.0
WORST = {
    "rotation_mae_deg": ROT_CAP_DEG,
    "translation_mae_mm": TRANS_CAP_MM,
    "rotation_p95_deg": ROT_CAP_DEG,
    "translation_p95_mm": TRANS_CAP_MM,
    "false_loop_excess": 0.98,
}
MAX_ABS_TRANSLATION_MM = 1000.0
ORTHO_TOL = 1e-3
LOOP_TRANS_TOL_MM = 1.0
LOOP_ROT_TOL_DEG = 5.0
FALSE_LOOP_GATE = 0.10
FALSE_LOOP_ALLOWANCE = 0.02  # verification tolerance; only false relations beyond 2% are scored
MAX_LOOP_RECORDS = 50000
EPISODE_TIMEOUT_S = 900  # per episode on one CPU core (the reference needs < 20 s)
RESERVED_NAMES = {"normalflow"}
ARTIFACT_SUFFIXES = {".npy", ".npz", ".json", ".pt", ".pth", ".pkl", ".pickle", ".ckpt", ".safetensors"}


class MethodFailure(Exception):
    pass


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _sanitize(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("._")
    return (cleaned or "method")[:80]


def discover_methods(checkpoints: Path) -> list[dict]:
    methods: list[dict] = []
    registered: list[Path] = []
    if checkpoints.is_dir():
        for spec_path in sorted(checkpoints.rglob("predict.json")):
            directory = spec_path.parent
            entry = {"dir": directory, "name": directory.relative_to(checkpoints).as_posix(), "command": None, "error": None}
            try:
                spec = json.loads(spec_path.read_text())
                command = spec.get("command")
                if not isinstance(command, list) or not command or not all(isinstance(a, str) for a in command):
                    raise ValueError("'command' must be a non-empty list of strings")
                if not any("{input}" in a for a in command) or not any("{output}" in a for a in command):
                    raise ValueError("'command' must contain the {input} and {output} placeholders")
                if isinstance(spec.get("name"), str) and spec["name"].strip():
                    entry["name"] = spec["name"].strip()
                entry["command"] = command
            except Exception as exc:  # noqa: BLE001 - any malformed spec is a failed method
                entry["error"] = f"invalid predict.json: {exc}"
            methods.append(entry)
            registered.append(directory)
        orphans: list[Path] = []
        for path in sorted(checkpoints.rglob("*")):
            if not path.is_file() or path.name.startswith(".") or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in ARTIFACT_SUFFIXES:
                continue
            directory = path.parent
            if any(_within(directory, r) for r in registered) or directory in orphans:
                continue
            orphans.append(directory)
            methods.append({
                "dir": directory,
                "name": directory.relative_to(checkpoints).as_posix(),
                "command": None,
                "error": "artifacts without predict.json: the method cannot be run on held-out inputs",
            })
    seen: set[str] = set()
    for method in methods:
        name = _sanitize(method["name"])
        if name in RESERVED_NAMES:
            name = f"{name}_candidate"
        base, k = name, 2
        while name in seen:
            name = f"{base}__{k}"
            k += 1
        seen.add(name)
        method["name"] = name
    return methods


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------

def run_command(method: dict, input_path: Path, out_dir: Path, root: Path, log_path: Path) -> float:
    command = [a.replace("{input}", str(input_path)).replace("{output}", str(out_dir)) for a in method["command"]]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    start = time.monotonic()
    with open(log_path, "ab") as log:
        log.write(f"\n$ {' '.join(command)}\n".encode())
        log.flush()
        try:
            proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as exc:
            raise MethodFailure(f"could not start command: {exc}") from exc
        try:
            returncode = proc.wait(timeout=EPISODE_TIMEOUT_S)
        except subprocess.TimeoutExpired as exc:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
            raise MethodFailure(f"timed out after {EPISODE_TIMEOUT_S} s") from exc
    if returncode != 0:
        raise MethodFailure(f"command exited with code {returncode}")
    return time.monotonic() - start


# --------------------------------------------------------------------------
# validation and scoring
# --------------------------------------------------------------------------

def rigid_inverse(transforms: np.ndarray) -> np.ndarray:
    transforms = np.asarray(transforms, dtype=np.float64)
    single = transforms.ndim == 2
    t = transforms[None] if single else transforms
    out = np.tile(np.eye(4), (len(t), 1, 1))
    rot_t = np.transpose(t[:, :3, :3], (0, 2, 1))
    out[:, :3, :3] = rot_t
    out[:, :3, 3] = -np.einsum("nij,nj->ni", rot_t, t[:, :3, 3])
    return out[0] if single else out


def _is_rigid(transforms: np.ndarray) -> bool:
    rot = transforms[..., :3, :3]
    gram = np.einsum("...ji,...jk->...ik", rot, rot)
    if np.abs(gram - np.eye(3)).max() > ORTHO_TOL:
        return False
    if (np.linalg.det(rot) < 0.5).any():
        return False
    return bool(np.abs(transforms[..., 3, :] - np.array([0.0, 0.0, 0.0, 1.0])).max() <= 1e-6)


def load_poses(out_dir: Path, n_frames: int) -> np.ndarray:
    path = out_dir / "poses.npy"
    if not path.is_file():
        raise MethodFailure("missing poses.npy")
    try:
        poses = np.load(path, allow_pickle=False)
    except Exception as exc:  # noqa: BLE001
        raise MethodFailure(f"unreadable poses.npy: {exc}") from exc
    if poses.shape != (n_frames, 4, 4):
        raise MethodFailure(f"poses.npy has shape {poses.shape}, expected {(n_frames, 4, 4)}")
    poses = poses.astype(np.float64)
    if not np.isfinite(poses).all():
        raise MethodFailure("non-finite pose values")
    if not _is_rigid(poses):
        raise MethodFailure("poses are not rigid transforms")
    if np.abs(poses[:, :3, 3]).max() > MAX_ABS_TRANSLATION_MM:
        raise MethodFailure("pose translation outside the physically possible range")
    return poses


def _euler_axes_deg(rot: np.ndarray) -> np.ndarray:
    zxy = Rotation.from_matrix(rot).as_euler("zxy", degrees=True)
    return np.stack([zxy[:, 1], zxy[:, 2], zxy[:, 0]], axis=1)


def pose_errors(pred: np.ndarray, gt: np.ndarray) -> dict:
    """Per-axis MAE (paper Table IV) and per-frame geodesic/translation errors, capped."""
    p = rigid_inverse(pred[0]) @ pred
    g = rigid_inverse(gt[0]) @ gt
    trans_axis = np.minimum(np.abs(p[:, :3, 3] - g[:, :3, 3]), TRANS_CAP_MM)
    rot_axis = np.abs((_euler_axes_deg(p[:, :3, :3]) - _euler_axes_deg(g[:, :3, :3]) + 180.0) % 360.0 - 180.0)
    rot_axis = np.minimum(rot_axis, ROT_CAP_DEG)
    rel = np.einsum("nji,njk->nik", g[:, :3, :3], p[:, :3, :3])
    geodesic = np.minimum(np.degrees(np.linalg.norm(Rotation.from_matrix(rel).as_rotvec(), axis=1)), ROT_CAP_DEG)
    trans_norm = np.minimum(np.linalg.norm(p[:, :3, 3] - g[:, :3, 3], axis=1), TRANS_CAP_MM)
    return {
        "rot_axis_mae": float(rot_axis.mean()),
        "trans_axis_mae": float(trans_axis.mean()),
        "geodesic": geodesic,
        "trans_norm": trans_norm,
    }


def _as_index(value) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean index")
    as_float = float(value)
    if not np.isfinite(as_float) or not as_float.is_integer():
        raise ValueError("non-integer index")
    return int(as_float)


def score_loops(out_dir: Path, gt: np.ndarray) -> dict:
    """Deduplicate loop records by frame pair and check each against ground truth."""
    path = out_dir / "loops.json"
    if not path.exists():
        return {"unique": 0, "false": 0}
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise MethodFailure(f"unreadable loops.json: {exc}") from exc
    records = data.get("loops", []) if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise MethodFailure("loops.json must hold a list of loop records")
    if len(records) > MAX_LOOP_RECORDS:
        raise MethodFailure(f"more than {MAX_LOOP_RECORDS} loop records")
    n = len(gt)
    seen: set[tuple[int, int]] = set()
    unique = 0
    false = 0
    for record in records:
        try:
            i = _as_index(record["i"])
            j = _as_index(record["j"])
            transform = np.asarray(record["T_ij"], dtype=np.float64)
        except Exception:  # noqa: BLE001 - malformed record counts as a false loop
            unique += 1
            false += 1
            continue
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        unique += 1
        if not (0 <= i < n and 0 <= j < n) or i == j or transform.shape != (4, 4) \
                or not np.isfinite(transform).all() or not _is_rigid(transform):
            false += 1
            continue
        if i > j:
            transform = rigid_inverse(transform)
            i, j = j, i
        true_rel = rigid_inverse(gt[i]) @ gt[j]
        err = rigid_inverse(true_rel) @ transform
        t_err = float(np.linalg.norm(err[:3, 3]))
        r_err = float(np.degrees(np.linalg.norm(Rotation.from_matrix(err[:3, :3]).as_rotvec())))
        if t_err > LOOP_TRANS_TOL_MM or r_err > LOOP_ROT_TOL_DEG:
            false += 1
    return {"unique": unique, "false": false}


def aggregate(per_episode: dict, episodes: list[dict]) -> dict:
    out = {}
    for experiment, contact_loss in EXPERIMENTS.items():
        rows = [per_episode[e["name"]] for e in episodes if bool(e["contact_loss"]) == contact_loss]
        if not rows:
            continue
        unique = sum(r["loops_unique"] for r in rows)
        false = sum(r["loops_false"] for r in rows)
        out[experiment] = {
            "rotation_mae_deg": float(np.mean([r["rot_axis_mae"] for r in rows])),
            "translation_mae_mm": float(np.mean([r["trans_axis_mae"] for r in rows])),
            "rotation_p95_deg": float(np.percentile(np.concatenate([r["geodesic"] for r in rows]), 95)),
            "translation_p95_mm": float(np.percentile(np.concatenate([r["trans_norm"] for r in rows]), 95)),
            "false_loop_excess": max(0.0, (float(false / unique) if unique else 0.0) - FALSE_LOOP_ALLOWANCE),
        }
    return out


def worst_results(episodes: list[dict]) -> dict:
    present = {bool(e["contact_loss"]) for e in episodes}
    return {exp: dict(WORST) for exp, flag in EXPERIMENTS.items() if flag in present}


def write_scores(path: Path, slice_name: str, results: dict, diagnostics: dict, metadata: dict) -> None:
    experiments: dict = {}
    for name, per_exp in results.items():
        for experiment, values in per_exp.items():
            experiments.setdefault(experiment, {"results": {}})["results"][name] = {m: float(values[m]) for m in METRICS}
    payload = {
        "_metadata": {"slice": slice_name, **metadata},
        "experiments": experiments,
        "_diagnostics": diagnostics,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, path)


def _episode_diag(row: dict) -> dict:
    return {
        "rotation_mae_deg": round(row["rot_axis_mae"], 5),
        "translation_mae_mm": round(row["trans_axis_mae"], 5),
        "unique_loops": row["loops_unique"],
        "false_loops": row["loops_false"],
        "seconds": round(row.get("seconds", 0.0), 2),
        **({"method_summary": row["method_summary"]} if row.get("method_summary") else {}),
    }


def _read_summary(out_dir: Path) -> dict | None:
    path = out_dir / "summary.json"
    try:
        if path.is_file() and path.stat().st_size < 20000:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if isinstance(v, (int, float, str, bool))}
    except Exception:  # noqa: BLE001
        return None
    return None


def _cache_file(slice_name: str, name: str, episode_name: str) -> Path | None:
    """Optional per-episode result cache (audit jobs only; unset in the default scripts)."""
    root = os.environ.get("TACTILE_EVAL_CACHE")
    if not root:
        return None
    return Path(root) / slice_name / _sanitize(name) / f"{episode_name}.json"


def _cache_load(slice_name: str, name: str, episode_name: str) -> dict | None:
    path = _cache_file(slice_name, name, episode_name)
    if path is None or not path.is_file():
        return None
    try:
        row = json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return None
    if "error" not in row:
        row["geodesic"] = np.asarray(row["geodesic"], dtype=np.float64)
        row["trans_norm"] = np.asarray(row["trans_norm"], dtype=np.float64)
    return row


def _cache_save(slice_name: str, name: str, episode_name: str, row: dict) -> None:
    path = _cache_file(slice_name, name, episode_name)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in row.items()}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload))
    os.replace(tmp, path)


def evaluate(
    slice_name: str,
    episodes: list[dict],
    render: Callable[[dict], dict],
    save_observations: Callable[[dict, Path], None],
    frozen_baseline: Callable[..., np.ndarray],
    output: Path,
    root: Path,
    keep_outputs: bool = False,
) -> dict:
    checkpoints = root / "checkpoints"
    methods = discover_methods(checkpoints)
    metadata = {
        "episodes": [{"name": e["name"], "contact_loss": bool(e["contact_loss"])} for e in episodes],
        "methods_discovered": [m["name"] for m in methods],
    }
    worst = worst_results(episodes)
    pending = {"normalflow": worst, **{m["name"]: worst for m in methods}}
    write_scores(output, slice_name, pending, {"status": "pending: every method holds its worst values until scored"}, metadata)

    states = {m["name"]: {"error": m["error"], "episodes": {}} for m in methods}
    baseline_state = {"error": None, "episodes": {}}
    # Episode inputs are ~100 MB each; container /tmp is a small tmpfs, so the
    # scratch space lives in the workspace's (gitignored) tmp/ directory.
    scratch_root = Path(os.environ.get("TACTILE_EVAL_SCRATCH", str(root / "tmp" / "eval_scratch")))
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"tactile_{slice_name}_", dir=str(scratch_root)) as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "inputs").mkdir()
        (tmp / "logs").mkdir()
        for episode in episodes:
            pending = set()
            for name, state in [("normalflow", baseline_state)] + [(m["name"], states[m["name"]]) for m in methods]:
                if state["error"] is not None:
                    continue
                cached = _cache_load(slice_name, name, episode["name"])
                if cached is None:
                    pending.add(name)
                elif "error" in cached:
                    state["error"] = cached["error"]
                else:
                    state["episodes"][episode["name"]] = cached
            if not pending:
                continue
            print(f"[{slice_name}] rendering {episode['name']}", flush=True)
            data = render(episode)
            gt = np.asarray(data["poses_mm"], dtype=np.float64)
            n_frames = len(gt)
            input_path = tmp / "inputs" / f"{episode['name']}.npz"
            save_observations(data, input_path)

            if baseline_state["error"] is None and "normalflow" in pending:
                try:
                    start = time.monotonic()
                    poses = frozen_baseline(data["gradients"], data["heights"], data["contact_masks"], data["mm_per_pixel"])
                    row = pose_errors(np.asarray(poses, dtype=np.float64), gt)
                    row.update({"loops_unique": 0, "loops_false": 0, "seconds": time.monotonic() - start})
                    baseline_state["episodes"][episode["name"]] = row
                    _cache_save(slice_name, "normalflow", episode["name"], row)
                except Exception as exc:  # noqa: BLE001
                    baseline_state["error"] = f"{episode['name']}: {exc!r}"

            for method in methods:
                state = states[method["name"]]
                if state["error"] is not None or method["name"] not in pending:
                    continue
                if keep_outputs:
                    out_dir = method["dir"] / f"{slice_name}_outputs" / episode["name"]
                else:
                    out_dir = tmp / "outputs" / method["name"] / episode["name"]
                shutil.rmtree(out_dir, ignore_errors=True)
                out_dir.mkdir(parents=True, exist_ok=True)
                print(f"[{slice_name}] {method['name']} on {episode['name']}", flush=True)
                try:
                    seconds = run_command(method, input_path, out_dir, root, tmp / "logs" / f"{method['name']}.log")
                    row = pose_errors(load_poses(out_dir, n_frames), gt)
                    loops = score_loops(out_dir, gt)
                    row.update({"loops_unique": loops["unique"], "loops_false": loops["false"], "seconds": seconds,
                                "method_summary": _read_summary(out_dir)})
                    state["episodes"][episode["name"]] = row
                    _cache_save(slice_name, method["name"], episode["name"], row)
                except MethodFailure as exc:
                    state["error"] = f"{episode['name']}: {exc}"
                except Exception as exc:  # noqa: BLE001 - never let one method stop the evaluation
                    state["error"] = f"{episode['name']}: unexpected scoring error {exc!r}"
                finally:
                    if not keep_outputs:
                        shutil.rmtree(out_dir, ignore_errors=True)
                if state["error"] is not None:
                    _cache_save(slice_name, method["name"], episode["name"], {"error": state["error"]})
                    log_file = tmp / "logs" / f"{method['name']}.log"
                    if log_file.exists():
                        tail = log_file.read_text(errors="replace")[-3000:]
                        state["log_tail"] = tail
                        print(f"[{slice_name}] {method['name']} FAILED: {state['error']}\n{tail}", flush=True)
            input_path.unlink(missing_ok=True)

    results: dict = {}
    diagnostics: dict = {}
    for name, state in [("normalflow", baseline_state)] + list(states.items()):
        diag: dict = {}
        if state["error"] is None:
            total_unique = sum(r["loops_unique"] for r in state["episodes"].values())
            total_false = sum(r["loops_false"] for r in state["episodes"].values())
            if total_unique and total_false / total_unique > FALSE_LOOP_GATE:
                state["error"] = (f"false-loop constraint failed: {total_false}/{total_unique} unique loop "
                                  f"constraints disagree with ground truth (gate {FALSE_LOOP_GATE:.0%})")
        if state["error"] is None:
            results[name] = aggregate(state["episodes"], episodes)
            diag["status"] = "scored"
        else:
            results[name] = worst_results(episodes)
            diag["status"] = "failed"
            diag["failure"] = state["error"]
            if state.get("log_tail"):
                diag["log_tail"] = state["log_tail"][-1500:]
        diag["episodes"] = {ep: _episode_diag(row) for ep, row in state["episodes"].items()}
        diagnostics[name] = diag
    write_scores(output, slice_name, results, diagnostics, metadata)
    return {"results": results, "diagnostics": diagnostics}
