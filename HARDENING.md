# Hardening following REVIEW.md

Validation is pending in the single combined CPU job. Historical before-values and fixes are recorded in [the preceding report](redteam/hardening/results/HARDENING_iteration11.md); the current iteration supersedes its open filesystem-access issue, scalar cache, and wall-clock timeouts.

Changes applied together:

- Enforce one-core affinity and one numerical-library thread. Replace the 900-second wall-clock timeout with a 7200 CPU-second budget, including private subprocess search, with no elapsed-time deadline. CPU and wall measurements are evaluator-owned diagnostics, not ranked metrics.
- Run arbitrary user-supplied commands under a filesystem policy that denies hidden evaluator files, repository history and scoring files, while permitting public source/data, the supplied input, and writes to the current output. This uses [Linux Landlock](https://www.kernel.org/doc/html/v6.6/userspace-api/landlock.html); unsupported hosts fail closed.
- Remove every scalar-result cache read. Every scored metric comes from raw poses and loop records. Ignore method summary claims entirely. Tighten false-loop gating to each experiment; reject malformed, non-finite, impossible or duplicate relations and oversized output files. Duplicate spam now fails rather than tying the reference.
- Expand the hidden test to 96 independent episodes, with 128-bit private seeds refreshed after the old configurations were exposed. Keep answers and all regeneration keys only under `eval/test/`. Expand public development episodes from 8 to 24 with the same parameter ranges and measurement.
- Compare the reference, dense and hybrid improvements, a revisit-registration-only dense variant, a weaker ablation, brute force, and the changed shortcuts on identical observations. Whole-episode paired bootstrap intervals quantify headroom. The final reference and fixed baseline then rerun end to end alone; their official output files become the only stored baseline.

No paper training or tracking procedure was changed in the reference. Both experiment weights and all metric coefficients stay unchanged. Paper-reported numbers under `_paper_results` and `_paper_context` stay unchanged. Reconstruction and real-time throughput remain outside this scaled tracking contract.

Run: `bash redteam/hardening/audit.sh`. Scientific computation runs only in a submitted job.

The first combined job was cancelled after six scheduler preemptions repeatedly restarted its completed calculations. The resubmission adds atomic private raw-output checkpoints, keyed by source, runtime, method artifacts and episode configuration. Recovery revalidates and rescores raw poses/relations against freshly rendered truth, and restores no metric or success verdict. Normal no-argument evaluation uses no checkpoint cache. Separate checkpoint namespaces preserve the independent final reference run. Scientific settings are unchanged.
