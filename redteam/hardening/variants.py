#!/usr/bin/env python3
"""Honest method variants used to check that the hardened test rewards better science.

Each variant is a complete tactile tracker with the gym's entry-point contract:
    python -m redteam.hardening.variants --variant NAME --input EP.npz --output DIR

Variants (all deterministic):
  reference_seed1      paper method, RANSAC seed 1 (seed spread check)
  reference_seed2      paper method, RANSAC seed 2 (seed spread check)
  loop_ccs_070         loop verification at CCS 0.70 (the paper's less conservative reconstruction setting)
  nf_kf                tracking module only, no loop closure (paper ablation NF-KF; weaker)
  only_sift            loops accepted on SIFT alone (paper ablation GS-OnlySIFT; weaker)
  only_nf_exhaustive   NormalFlow against every earlier keyframe, no SIFT, no coverage set
                       (paper ablation GS-OnlyNF; the brute force the two-stage design avoids)
  exhaustive_two_stage SIFT + NormalFlow against every earlier keyframe (no coverage pruning)
  session_chain        new tracking sessions are anchored at the last estimated pose instead
                       of the identity (stronger relocalisation prior)
  session_chain_dense  session_chain + NormalFlow on 6000 samples and loop CCS 0.80
  hybrid_local_loops   session_chain + loop CCS 0.80 + geometric loop proposals: up to 6 coverage
                       keyframes whose footprint overlaps the new keyframe under the current pose
                       estimate are also verified with NormalFlow initialised from that estimate
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from method.gelslam_sim.gelslam import GelSLAM, inv_se3, run_gelslam
from method.gelslam_sim.run import load_episode, write_outputs


class SessionChainGelSLAM(GelSLAM):
    """Anchor each new session's prior at the last frame's estimated pose."""

    def new_session_pose(self) -> np.ndarray:
        if self.prev_fid is None or self.prev_fid not in self.parent:
            return np.eye(4)
        return self.kf_pose[self.parent[self.prev_fid]] @ self.rel[self.prev_fid]


class HybridGelSLAM(SessionChainGelSLAM):
    """Two-stage SIFT proposals plus pose-estimate (geometric) proposals."""

    min_overlap_weight = 1500.0
    max_geometric_proposals = 6

    def _detect_loops(self, tar: int) -> list[int]:
        matched = super()._detect_loops(tar)
        done = set(matched)
        tar_kf = self.kfs[tar]
        scored = []
        for ref in self.candidate_keyframes(tar):
            if ref in done:
                continue
            weight = self._overlap_weight(tar, ref)
            if weight >= self.min_overlap_weight:
                scored.append((weight, ref))
        for _, ref in sorted(scored, reverse=True)[: self.max_geometric_proposals]:
            ref_kf = self.kfs[ref]
            init = inv_se3(self.kf_pose[tar]) @ self.kf_pose[ref]
            tar_T_ref = self._register(ref_kf.frame, tar_kf.frame, init, self.loop_ccs, self.loop_scr)
            self.n_candidates += 1
            if tar_T_ref is None:
                continue
            ref_T_tar = inv_se3(tar_T_ref)
            self.edges.append((ref, tar, ref_T_tar))
            matched.append(ref)
            self.loops.append({"i": int(ref_kf.fid), "j": int(tar_kf.fid), "T_ij": ref_T_tar.tolist(),
                               "sift_inliers": 0})
        return matched


def build(variant: str, mm_per_pixel: float) -> GelSLAM:
    if variant == "reference_seed1":
        return GelSLAM(mm_per_pixel, seed=1)
    if variant == "reference_seed2":
        return GelSLAM(mm_per_pixel, seed=2)
    if variant == "loop_ccs_070":
        return GelSLAM(mm_per_pixel, loop_ccs=0.70)
    if variant == "nf_kf":
        return GelSLAM(mm_per_pixel, loop_mode="none")
    if variant == "only_sift":
        return GelSLAM(mm_per_pixel, loop_mode="only_sift")
    if variant == "only_nf_exhaustive":
        return GelSLAM(mm_per_pixel, loop_mode="only_nf", use_coverage=False)
    if variant == "exhaustive_two_stage":
        return GelSLAM(mm_per_pixel, use_coverage=False)
    if variant == "session_chain":
        return SessionChainGelSLAM(mm_per_pixel)
    if variant == "session_chain_dense":
        return SessionChainGelSLAM(mm_per_pixel, n_samples=6000, loop_ccs=0.80)
    if variant == "hybrid_local_loops":
        return HybridGelSLAM(mm_per_pixel, loop_ccs=0.80)
    raise ValueError(variant)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gradients, heights, contacts, mm_per_pixel = load_episode(Path(args.input))
    start = time.process_time()
    slam = build(args.variant, mm_per_pixel)
    poses, loops, stats = run_gelslam(gradients, heights, contacts, mm_per_pixel, slam=slam)
    stats["variant"] = args.variant
    stats["cpu_seconds"] = round(time.process_time() - start, 3)
    write_outputs(Path(args.output), poses, loops, stats)


if __name__ == "__main__":
    main()
