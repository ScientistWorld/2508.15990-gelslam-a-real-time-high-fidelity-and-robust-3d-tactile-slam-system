#!/usr/bin/env python3
"""Rank gains and paired per-episode comparisons for the hardening audit.

rank gain(method) = sum_exp weight_exp * sum_metric |coef| * dir * (value - reference) / std
where dir = +1 if higher_is_better else -1 and std is the population standard
deviation of that metric over the scored (non-failed) entries of the cohort.
The reference is gelslam_online. Paired statistics compare per-episode
axis-averaged MAEs of each method against the reference on the same episodes.

Usage: python redteam/hardening/rank.py OUT_PREFIX SCORES.json [SCORES.json ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "gelslam_online"


def main() -> None:
    out_prefix = Path(sys.argv[1])
    files = [Path(p) for p in sys.argv[2:]]
    ref_json = json.loads((ROOT / "scoring" / "reference.json").read_text())["experiments"]
    values: dict[str, dict] = {}
    status: dict[str, str] = {}
    episodes: dict[str, dict] = {}
    source: dict[str, str] = {}
    for path in files:
        data = json.loads(path.read_text())
        diag = data.get("_diagnostics", {})
        for exp, block in data["experiments"].items():
            for name, vals in block["results"].items():
                if name in values and exp in values[name]:
                    continue
                values.setdefault(name, {})[exp] = vals
                source.setdefault(name, path.name)
        for name, d in diag.items():
            if name not in status:
                status[name] = d.get("status", "?") + (f" ({d['failure'][:90]})" if d.get("failure") else "")
                episodes[name] = d.get("episodes", {})
    if REFERENCE not in values:
        raise SystemExit("reference entry missing")
    cohort = [n for n in values if status.get(n, "").startswith("scored")]
    stds = {}
    for exp, spec in ref_json.items():
        for metric in spec["metrics"]:
            arr = np.array([values[n][exp][metric] for n in cohort if exp in values[n]])
            stds[(exp, metric)] = float(arr.std()) if len(arr) > 1 else 0.0
    ep_kind = {}
    ref_eps = episodes.get(REFERENCE, {})
    for ep in ref_eps:
        ep_kind[ep] = "relocalization_after_contact_loss" if "contact_loss" in ep else "long_horizon_tracking"

    rows = []
    for name in values:
        gain = 0.0
        for exp, spec in ref_json.items():
            if exp not in values[name]:
                continue
            for metric, mspec in spec["metrics"].items():
                std = stds[(exp, metric)]
                if std <= 0:
                    continue
                direction = 1.0 if mspec["higher_is_better"] else -1.0
                delta = values[name][exp][metric] - values[REFERENCE][exp][metric]
                gain += spec["weight"] * abs(mspec["coefficient"]) * direction * delta / std
        paired = {}
        for exp in ref_json:
            eps = [e for e, k in ep_kind.items() if k == exp and e in episodes.get(name, {})]
            if not eps or name == REFERENCE:
                continue
            for key in ("rotation_mae_deg", "translation_mae_mm"):
                d = np.array([episodes[name][e][key] - ref_eps[e][key] for e in eps])
                paired[f"{exp}:{key}"] = {
                    "mean_diff": float(d.mean()),
                    "se": float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None,
                    "n_better": int((d < 0).sum()),
                    "n_worse": int((d > 0).sum()),
                    "n": len(d),
                }
        rows.append({"name": name, "status": status.get(name, "?"), "rank_gain": gain, "values": values[name],
                     "paired": paired, "source": source[name]})
    rows.sort(key=lambda r: -r["rank_gain"])
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(out_prefix) + ".json").write_text(json.dumps({"cohort": cohort, "stds": {f"{k[0]}:{k[1]}": v for k, v in stds.items()},
                                                           "rows": rows}, indent=1))
    lines = ["| method | status | rank gain | E1 rot MAE | E1 trans MAE | E1 rot p95 | E1 false-loop excess | E2 rot MAE | E2 trans MAE | E2 rot p95 | E2 false-loop excess |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        e1 = r["values"].get("long_horizon_tracking", {})
        e2 = r["values"].get("relocalization_after_contact_loss", {})
        fmt = lambda d, k: f"{d[k]:.4f}" if k in d else "-"
        lines.append(f"| {r['name']} | {r['status'][:60]} | {r['rank_gain']:+.3f} | {fmt(e1,'rotation_mae_deg')} | {fmt(e1,'translation_mae_mm')} | "
                     f"{fmt(e1,'rotation_p95_deg')} | {fmt(e1,'false_loop_excess')} | {fmt(e2,'rotation_mae_deg')} | {fmt(e2,'translation_mae_mm')} | "
                     f"{fmt(e2,'rotation_p95_deg')} | {fmt(e2,'false_loop_excess')} |")
    lines.append("")
    lines.append("Paired per-episode differences vs reference (negative = better): mean ± SE, better/worse episodes")
    for r in rows:
        if r["paired"]:
            parts = [f"{k.split(':')[0][:5]}-{k.split(':')[1][:3]} {v['mean_diff']:+.4f}±{(v['se'] or 0):.4f} ({v['n_better']}/{v['n_worse']})"
                     for k, v in r["paired"].items()]
            lines.append(f"- {r['name']}: " + "; ".join(parts))
    Path(str(out_prefix) + ".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
