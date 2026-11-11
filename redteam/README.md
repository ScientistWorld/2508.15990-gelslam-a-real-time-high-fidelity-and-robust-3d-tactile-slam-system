# Reproducing the audit

From the gym's configured compute container at `/home/user`, run one complete trial with:

```bash
bash redteam/duplicate_loops_shortcut/run.sh
```

Each trial has a `candidate.py` and one `run.sh`. Shared candidate implementations are in `candidates.py`; the harness stages the candidate as an agent would, calls the public training script, then runs the unmodified hidden `bash scripts/evaluate_test.sh` with **no arguments**. The final test starts after the candidate process exits. The harness restores the original mutable gym files and checkpoints in a `finally` block. Do not run these computations on the login node; submit them using the gym job protocol.

The common reference and baseline are recomputed from agent-visible source if their local caches are absent. Oracle shortcuts use the shipped data and generator, never the paper, evaluator source, original test scores, or legacy checkpoint answers. The genuine variants require improve-mode `method/`; the direct-label, generator-replay, and target-replacement shortcuts do not. The snapshot in `reference_original/` is exclusively an auditor ranking anchor, not candidate input.

`batch.sh` runs all 24 trials and skips folders with an existing `outcome.json` to resume interrupted jobs. To rerun a completed trial, invoke its own `run.sh` directly. `brute_force_all_keyframes` is explicitly classified as an honest exhaustive alternative that ties the reference. Every tested shortcut has `_shortcut` in its folder and variant name, including failed shortcuts.

Successful tests preserve `scores_test.json` and `scores_train.json`; failed tests preserve their logs and outcome instead of inventing scores. `method_manifest.json` includes output hashes and loop samples. Large or regenerated artifacts under `artifacts/`, `generated/`, `_state/`, and `_cache/` are ignored. Existing manifests were collected from the actual saved outputs after the jobs completed; this adds provenance without changing scored outputs.

`python3 redteam/summarize.py` performs lightweight JSON-only analysis. It writes the full cohort, per-metric normalization scales, rank contributions and raw metrics to `summary.json`, the compact table to `results.md`, and seed/failure checks to `quality_checks.json`. It uses absolute coefficients, the declared better direction, and population standard deviation over the explicitly listed finite audit cohort. Unknown downstream handling of failed jobs and NaN metrics is not guessed.

The complete findings and limitations are in [REDTEAM.md](../REDTEAM.md).
