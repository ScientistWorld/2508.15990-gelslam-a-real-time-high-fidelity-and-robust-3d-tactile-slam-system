# Hardening following REVIEW.md

The combined job `384d3d42-aab` completed successfully. Historical before-values and fixes are recorded in [the preceding report](redteam/hardening/results/HARDENING_iteration11.md); the current iteration supersedes its open filesystem-access issue, scalar cache, and wall-clock timeouts. The completed 96-episode audit is preserved in [measurements](eval/test/hardening_results/audit96_measurements.md). A final enlargement to 384 episodes is pending because that audit did not resolve aggregate headroom beyond paired uncertainty.

Changes applied together:

- Enforce one-core affinity and one numerical-library thread. Replace the 900-second wall-clock timeout with a 7200 CPU-second budget, including private subprocess search, with no elapsed-time deadline. CPU and wall measurements are evaluator-owned diagnostics, not ranked metrics.
- Run arbitrary user-supplied commands under a filesystem policy that denies hidden evaluator files, repository history and scoring files, while permitting public source/data, the supplied input, and writes to the current output. This uses [Linux Landlock](https://www.kernel.org/doc/html/v6.6/userspace-api/landlock.html); unsupported hosts fail closed.
- Remove every scalar-result cache read. Every scored metric comes from raw poses and loop records. Ignore method summary claims entirely. Tighten false-loop gating to each experiment; reject malformed, non-finite, impossible or duplicate relations and oversized output files. Duplicate spam now fails rather than tying the reference.
- Expand the hidden test to 96 independent episodes, with 128-bit private seeds refreshed after the old configurations were exposed. Keep answers and all regeneration keys only under `eval/test/`. Expand public development episodes from 8 to 24 with the same parameter ranges and measurement.
- Compare the reference, dense and hybrid improvements, a revisit-registration-only dense variant, a weaker ablation, brute force, and the changed shortcuts on identical observations. Whole-episode paired bootstrap intervals quantify headroom. The final reference and fixed baseline then rerun end to end alone; their official output files become the only stored baseline.

No paper training or tracking procedure was changed in the reference. Both experiment weights and all metric coefficients stay unchanged. Paper-reported numbers under `_paper_results` and `_paper_context` stay unchanged. Reconstruction and real-time throughput remain outside this scaled tracking contract.

Run: `bash redteam/hardening/audit.sh`. Scientific computation runs only in a submitted job.

The first combined job was cancelled after six scheduler preemptions repeatedly restarted its completed calculations. The resubmission adds atomic private raw-output checkpoints, keyed by source, runtime, method artifacts and episode configuration. Recovery revalidates and rescores raw poses/relations against freshly rendered truth, and restores no metric or success verdict. Normal no-argument evaluation uses no checkpoint cache. Separate checkpoint namespaces preserve the independent final reference run. Scientific settings are unchanged.

Completed checks: all filesystem, child-CPU, invalid-output, failure-matrix and raw-rescoring contracts passed. The independent reference and frozen baseline exactly matched the paired cohort (maximum difference 0 across every scored metric). Reference seeds 0 and 1 also matched exactly. The reference beats the baseline on both experiments: 0.5540 deg / 0.05170 mm versus 3.1564 deg / 0.69988 mm in continuous contact, and 1.6913 deg / 0.22309 mm versus 9.0191 deg / 2.27361 mm after contact loss. All 13 invalid or prohibited shortcut entries receive the full worst-value matrix; the three identity-fallback shortcuts lose substantially.

The new `hybrid_dense_loops` variant improves all eight error metrics, with gain +0.03922 in the full audit cohort (+0.22089 among honest methods), but its paired whole-episode bootstrap 95% interval is [-0.00566, +0.23545]. The next job expands the same parameter distribution to 384 independent episodes, without changing the reference, coefficients or experiment weights. The 96 unchanged inputs reuse private raw predictions only after source-provenance checks; every metric is recomputed from those predictions and freshly rendered truth. Remaining inputs execute each method afresh. The final reference uses its separate independent namespace.

The NormalFlow-only exhaustive search loses (-0.78886). Exhaustive two-stage matching still gains +0.02188 by retaining all keyframes. The test does not yet establish the coverage set's efficiency advantage; this remains an explicit limitation, not a closed shortcut. No claim that the hardening is complete is made by these interim measurements.

Job `888d31de-3d2` was cancelled after ten scheduler preemptions and about five
hours of repeated recovery. Its incomplete output is not a measurement. Raw
predictions remain available under private evaluator storage. The recovery job
(`bash scripts/resume_scale.sh`) now completes missing inference first, skips
observation generation when all needed predictions exist, and obtains exactly
the same poses through the original contact solve without sensor simulation.
It checks bitwise equality against the full renderer for every texture and both
contact regimes before transferring source-verified raw predictions. Both old
source snapshots are retained privately, and reviewed SHA-256 hashes lock the
migration to these operational changes. Mathematical scoring functions and the
full renderer are unchanged. Optional evaluator-owned truth checkpoints stay
under `eval/test/resume/`, keyed by runtime, source and episode configuration;
methods can neither read nor write them. They contain answers, never scored
values or method-provided verdicts. Normal no-argument evaluation uses no resume
or truth checkpoints. Completed audit phases also survive preemption. The
384-episode paired result and independent official scores are still pending.
