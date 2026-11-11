"""GelSLAM tracking, loop-closure and pose-graph modules for a tactile stream.

Follows Section IV of the paper and the released implementation
(https://github.com/rpl-cmu/gelslam):

* Tracking (IV-A): every frame is registered with NormalFlow against the most
  recent keyframe, initialised from the previous frame's estimate. If CCS or
  SCR falls below threshold the previous frame becomes a keyframe; if the
  previous frame already is the keyframe, tracking is lost and a new tracking
  session starts at the current frame.
* Loop closure (IV-B): each new keyframe is compared with the active coverage
  keyframes. SIFT features of the curvature maps are matched, a planar
  transform is fitted with RANSAC, pairs with more than 8 inliers become
  candidates, and NormalFlow initialised from the SIFT transform verifies them
  with the same CCS/SCR failure detection.
* Coverage set (IV-B1): greedy, keeps keyframes that contribute more than
  0.2 mm^2 of (boundary-weighted) contact area not covered by their neighbours.
* Pose graph (IV-B3): Levenberg-Marquardt over SE(3) keyframe poses with a
  fixed covariance for every constraint; each tracking session is anchored by
  a prior until a loop merges it with an older session.

The stream is processed synchronously, so no keyframe is skipped by the loop
module (the paper's GS-Offline schedule, which Table IV shows matches
GS-Online).
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.spatial.transform import Rotation

from method.gelslam_sim.normalflow import LoseTrackError, TactileFrame, height2pointcloud, register, wide_remap

# Fixed pose-graph covariance of the released implementation (rad, mm).
SIGMA_ROT_RAD = 0.01
SIGMA_TRANS_MM = 0.1


def inv_se3(transform: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    rot = transform[:3, :3]
    out[:3, :3] = rot.T
    out[:3, 3] = -rot.T @ transform[:3, 3]
    return out


def laplacian2gray(lap: np.ndarray) -> np.ndarray:
    return (((lap + 0.7) / 1.4) * 255).astype(np.uint8)


def mask2weight(contact: np.ndarray) -> np.ndarray:
    scale = contact.shape[0] / 60.0
    weight = (np.tanh(distance_transform_edt(contact) / scale - 3) + 1) / 2.0 * contact
    return weight.astype(np.float32)


def sift_features(lap: np.ndarray, contact: np.ndarray, sift) -> tuple[np.ndarray, np.ndarray | None]:
    ys, xs = np.where(contact)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32), None
    min_x, max_x, min_y, max_y = xs.min(), xs.max(), ys.min(), ys.max()
    gray = laplacian2gray(lap)
    kps, des = sift.detectAndCompute(np.ascontiguousarray(gray[min_y:max_y + 1, min_x:max_x + 1]), None)
    if des is None or len(kps) == 0:
        return np.zeros((0, 2), dtype=np.float32), None
    erode = max(contact.shape[0] // 48, 1)
    eroded = binary_erosion(contact, structure=np.ones((erode, erode)))
    pts, keep = [], []
    for idx, kp in enumerate(kps):
        x = kp.pt[0] + min_x
        y = kp.pt[1] + min_y
        if eroded[int(y), int(x)]:
            pts.append((x, y))
            keep.append(idx)
    if not keep:
        return np.zeros((0, 2), dtype=np.float32), None
    return np.asarray(pts, dtype=np.float32), np.asarray(des[keep], dtype=np.float32)


def affine_to_transform(mat: np.ndarray, width: int, height: int, mm_per_pixel: float) -> np.ndarray:
    """Planar SIFT/RANSAC transform (pixels) -> tar_T_ref (mm), as M2T in the release."""
    tx = (mat[0, 2] + (mat[0, 0] * width / 2 + mat[0, 1] * height / 2) - width / 2) * mm_per_pixel
    ty = (mat[1, 2] + (mat[1, 0] * width / 2 + mat[1, 1] * height / 2) - height / 2) * mm_per_pixel
    scale = np.sqrt(mat[0, 0] ** 2 + mat[0, 1] ** 2)
    out = np.eye(4)
    out[0, :2] = mat[0, :2] / scale
    out[1, :2] = mat[1, :2] / scale
    out[0, 3] = tx
    out[1, 3] = ty
    return out


class Keyframe:
    def __init__(self, fid: int, frame: TactileFrame, session: int, sift):
        self.fid = fid
        self.frame = frame
        self.session = session
        self.kp, self.des = sift_features(frame.L, frame.C, sift)
        self.pc = height2pointcloud(frame.H, frame.C, frame.mm_per_pixel)
        self.W = mask2weight(frame.C)
        self.Wc = self.W[frame.C]


# --------------------------------------------------------------------------
# Pose graph optimisation (Levenberg-Marquardt, fixed covariance)
# --------------------------------------------------------------------------

def _pack(poses: np.ndarray) -> np.ndarray:
    out = np.zeros((len(poses), 6))
    out[:, :3] = poses[:, :3, 3]
    out[:, 3:] = Rotation.from_matrix(poses[:, :3, :3]).as_rotvec()
    return out


def _unpack(params: np.ndarray) -> np.ndarray:
    out = np.tile(np.eye(4), (len(params), 1, 1))
    out[:, :3, :3] = Rotation.from_rotvec(params[:, 3:]).as_matrix()
    out[:, :3, 3] = params[:, :3]
    return out


def _between_residual(xa: np.ndarray, xb: np.ndarray, meas_rot_inv, meas_t: np.ndarray,
                      sig_r: float, sig_t: float) -> np.ndarray:
    """Residual of log(Z^-1 * T_a^-1 T_b) for stacked parameter rows."""
    ra_inv = Rotation.from_rotvec(xa[:, 3:]).inv()
    rb = Rotation.from_rotvec(xb[:, 3:])
    r_ab = ra_inv * rb
    t_ab = ra_inv.apply(xb[:, :3] - xa[:, :3])
    r_err = meas_rot_inv * r_ab
    t_err = meas_rot_inv.apply(t_ab - meas_t)
    return np.hstack([t_err / sig_t, r_err.as_rotvec() / sig_r])


def _prior_residual(xk: np.ndarray, prior_rot_inv, prior_t: np.ndarray, sig_r: float, sig_t: float) -> np.ndarray:
    rk = Rotation.from_rotvec(xk[:, 3:])
    r_err = prior_rot_inv * rk
    t_err = prior_rot_inv.apply(xk[:, :3] - prior_t)
    return np.hstack([t_err / sig_t, r_err.as_rotvec() / sig_r])


def optimize_pose_graph(poses: np.ndarray, edges: list, priors: list, sig_r: float = SIGMA_ROT_RAD,
                        sig_t: float = SIGMA_TRANS_MM, max_iters: int = 30) -> np.ndarray:
    """poses: (K,4,4) start_T_k; edges: [(a, b, a_T_b)]; priors: [(k, start_T_k)]."""
    k_count = len(poses)
    if k_count == 0:
        return poses
    x = _pack(np.asarray(poses, dtype=np.float64))
    ea = np.asarray([e[0] for e in edges], dtype=np.int64)
    eb = np.asarray([e[1] for e in edges], dtype=np.int64)
    n_e = len(edges)
    if n_e:
        meas = np.asarray([e[2] for e in edges], dtype=np.float64)
        meas_rot_inv = Rotation.from_matrix(meas[:, :3, :3]).inv()
        meas_t = meas[:, :3, 3]
    pk = np.asarray([p[0] for p in priors], dtype=np.int64)
    n_p = len(priors)
    if n_p:
        pmat = np.asarray([p[1] for p in priors], dtype=np.float64)
        prior_rot_inv = Rotation.from_matrix(pmat[:, :3, :3]).inv()
        prior_t = pmat[:, :3, 3]

    def residual(params: np.ndarray) -> np.ndarray:
        parts = []
        if n_e:
            parts.append(_between_residual(params[ea], params[eb], meas_rot_inv, meas_t, sig_r, sig_t).ravel())
        if n_p:
            parts.append(_prior_residual(params[pk], prior_rot_inv, prior_t, sig_r, sig_t).ravel())
        return np.concatenate(parts) if parts else np.zeros(0)

    rows_e = np.arange(6 * n_e).reshape(n_e, 6)
    rows_p = 6 * n_e + np.arange(6 * n_p).reshape(n_p, 6)
    eps = 1e-6

    def jacobian(params: np.ndarray) -> np.ndarray:
        jac = np.zeros((6 * (n_e + n_p), 6 * k_count))
        if n_e:
            xa = params[ea]
            xb = params[eb]
            base = _between_residual(xa, xb, meas_rot_inv, meas_t, sig_r, sig_t)
            for d in range(6):
                xa_p = xa.copy()
                xa_p[:, d] += eps
                jac[rows_e, (6 * ea + d)[:, None]] = (_between_residual(xa_p, xb, meas_rot_inv, meas_t, sig_r, sig_t) - base) / eps
                xb_p = xb.copy()
                xb_p[:, d] += eps
                jac[rows_e, (6 * eb + d)[:, None]] = (_between_residual(xa, xb_p, meas_rot_inv, meas_t, sig_r, sig_t) - base) / eps
        if n_p:
            xk = params[pk]
            base = _prior_residual(xk, prior_rot_inv, prior_t, sig_r, sig_t)
            for d in range(6):
                xk_p = xk.copy()
                xk_p[:, d] += eps
                jac[rows_p, (6 * pk + d)[:, None]] = (_prior_residual(xk_p, prior_rot_inv, prior_t, sig_r, sig_t) - base) / eps
        return jac

    res = residual(x)
    cost = float(res @ res)
    lam = 1e-4
    for _ in range(max_iters):
        jac = jacobian(x)
        hess = jac.T @ jac
        grad = jac.T @ res
        diag = np.diag(hess).copy() + 1e-9
        improved = False
        rel_gain = 0.0
        step = None
        for _ in range(12):
            try:
                step = -np.linalg.solve(hess + lam * np.diag(diag), grad)
            except np.linalg.LinAlgError:
                lam *= 10.0
                continue
            x_new = x + step.reshape(k_count, 6)
            res_new = residual(x_new)
            cost_new = float(res_new @ res_new)
            if np.isfinite(cost_new) and cost_new < cost:
                rel_gain = (cost - cost_new) / max(cost, 1e-12)
                x, res, cost = x_new, res_new, cost_new
                lam = max(lam * 0.3, 1e-12)
                improved = True
                break
            lam *= 10.0
        if not improved or rel_gain < 1e-10 or (step is not None and np.abs(step).max() < 1e-10):
            break
    return _unpack(x)


# --------------------------------------------------------------------------
# GelSLAM
# --------------------------------------------------------------------------

class GelSLAM:
    def __init__(
        self,
        mm_per_pixel: float,
        track_ccs: float = 0.85,
        track_scr: float = 0.3,
        loop_ccs: float = 0.85,
        loop_scr: float = 0.3,
        min_sift_inliers: int = 9,
        n_samples: int = 3000,
        coverage_area_mm2: float = 0.2,
        loop_mode: str = "two_stage",
        use_coverage: bool = True,
        seed: int = 0,
    ):
        if loop_mode not in {"two_stage", "only_sift", "only_nf", "none"}:
            raise ValueError(loop_mode)
        self.ppmm = float(mm_per_pixel)
        self.track_ccs = track_ccs
        self.track_scr = track_scr
        self.loop_ccs = loop_ccs
        self.loop_scr = loop_scr
        self.min_sift_inliers = min_sift_inliers
        self.n_samples = n_samples
        # 0.2 mm^2 of contact area expressed in (weighted) pixels at this resolution.
        self.coverage_threshold = coverage_area_mm2 / (self.ppmm ** 2)
        self.loop_mode = loop_mode
        self.use_coverage = use_coverage
        self.seed = seed
        self.sift = cv2.SIFT_create(contrastThreshold=0.02, nOctaveLayers=3)
        self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)

        self.kfs: list[Keyframe] = []
        self.kf_pose: list[np.ndarray] = []
        self.edges: list[tuple[int, int, np.ndarray]] = []
        self.priors: dict[int, tuple[int, np.ndarray]] = {}
        self.uf_parent: list[int] = []
        self.cov_active: list[bool] = []
        self.cov_nbrs: list[set[int]] = []
        self.loops: list[dict] = []
        self.parent: dict[int, int] = {}
        self.rel: dict[int, np.ndarray] = {}
        self.n_candidates = 0
        self.n_sessions = 0
        self.n_solves = 0

        self.ref_kidx: int | None = None
        self.ref_T_prev = np.eye(4)
        self.prev_is_kf = False
        self.prev_frame: TactileFrame | None = None
        self.prev_fid: int | None = None
        self.prev_in_contact = False

    # ---------------- union-find over tracking sessions ----------------
    def _find(self, s: int) -> int:
        while self.uf_parent[s] != s:
            self.uf_parent[s] = self.uf_parent[self.uf_parent[s]]
            s = self.uf_parent[s]
        return s

    def _component(self, root: int) -> list[int]:
        return [k for k, kf in enumerate(self.kfs) if self._find(kf.session) == root]

    # ---------------- tracking module ----------------
    def new_session_pose(self) -> np.ndarray:
        """Prior pose of a new tracking session's first keyframe (released code: identity)."""
        return np.eye(4)

    def _register(self, ref: TactileFrame, tar: TactileFrame, init: np.ndarray, ccs_thr: float, scr_thr: float):
        try:
            tar_T_ref, ccs, scr = register(ref, tar, init, self.n_samples)
        except LoseTrackError:
            return None
        if ccs < ccs_thr or scr < scr_thr:
            return None
        return tar_T_ref

    def process(self, fid: int, frame: TactileFrame) -> None:
        if not frame.in_contact and self.prev_fid is not None:
            self.parent[fid] = self.parent[self.prev_fid]
            self.rel[fid] = self.rel[self.prev_fid].copy()
            self.prev_in_contact = False
            return
        if not self.prev_in_contact or self.ref_kidx is None:
            self._new_trial(fid, frame)
            return
        ref = self.kfs[self.ref_kidx].frame
        curr_T_ref = self._register(ref, frame, inv_se3(self.ref_T_prev), self.track_ccs, self.track_scr)
        if curr_T_ref is not None:
            self._track_ok(fid, frame, curr_T_ref)
            return
        if self.prev_is_kf:
            self._new_trial(fid, frame)
            return
        kidx = self._add_keyframe(self.prev_fid, self.prev_frame, new_trial=False, ref_T_curr=self.ref_T_prev)
        curr_T_ref = self._register(self.kfs[kidx].frame, frame, np.eye(4), self.track_ccs, self.track_scr)
        if curr_T_ref is not None:
            self._track_ok(fid, frame, curr_T_ref)
        else:
            self._new_trial(fid, frame)

    def _track_ok(self, fid: int, frame: TactileFrame, curr_T_ref: np.ndarray) -> None:
        self.ref_T_prev = inv_se3(curr_T_ref)
        self.prev_is_kf = False
        self.prev_frame = frame
        self.prev_fid = fid
        self.prev_in_contact = True
        self.parent[fid] = self.ref_kidx
        self.rel[fid] = self.ref_T_prev.copy()

    def _new_trial(self, fid: int, frame: TactileFrame) -> None:
        self._add_keyframe(fid, frame, new_trial=True, ref_T_curr=None)
        self.prev_frame = frame
        self.prev_fid = fid
        self.prev_in_contact = True

    def _add_keyframe(self, fid: int, frame: TactileFrame, new_trial: bool, ref_T_curr: np.ndarray | None) -> int:
        kidx = len(self.kfs)
        if new_trial or self.ref_kidx is None:
            session = self.n_sessions
            self.n_sessions += 1
            self.uf_parent.append(session)
            pose = self.new_session_pose()
            self.priors[session] = (kidx, pose.copy())
        else:
            session = self.kfs[self.ref_kidx].session
            pose = self.kf_pose[self.ref_kidx] @ ref_T_curr
            self.edges.append((self.ref_kidx, kidx, ref_T_curr.copy()))
        self.kfs.append(Keyframe(fid, frame, session, self.sift))
        self.kf_pose.append(pose)
        self.cov_active.append(True)
        self.cov_nbrs.append(set())
        self.parent[fid] = kidx
        self.rel[fid] = np.eye(4)
        self.ref_kidx = kidx
        self.ref_T_prev = np.eye(4)
        self.prev_is_kf = True
        self._loop_closure(kidx)
        return kidx

    # ---------------- loop closure module ----------------
    def _sift_proposal(self, ref_kf: Keyframe, tar_kf: Keyframe):
        if ref_kf.des is None or tar_kf.des is None or len(ref_kf.kp) < 2 or len(tar_kf.kp) < 2:
            return None, 0
        matches = self.matcher.match(ref_kf.des, tar_kf.des)
        if len(matches) < 3:
            return None, 0
        src = np.float32([ref_kf.kp[m.queryIdx] for m in matches]).reshape(-1, 1, 2)
        dst = np.float32([tar_kf.kp[m.trainIdx] for m in matches]).reshape(-1, 1, 2)
        mat, inliers = cv2.estimateAffinePartial2D(src, dst, maxIters=100, ransacReprojThreshold=3)
        if mat is None or inliers is None:
            return None, 0
        if not np.isfinite(mat).all() or np.hypot(mat[0, 0], mat[0, 1]) < 1e-6:
            return None, 0
        h, w = tar_kf.frame.L.shape
        return affine_to_transform(mat, w, h, self.ppmm), int(np.sum(inliers))

    def candidate_keyframes(self, tar: int) -> list[int]:
        tar_kf = self.kfs[tar]
        out = []
        for ref in range(tar):
            if self.kfs[ref].session == tar_kf.session and ref == tar - 1:
                continue
            if self.use_coverage and not self.cov_active[ref]:
                continue
            out.append(ref)
        return out

    def _detect_loops(self, tar: int) -> list[int]:
        tar_kf = self.kfs[tar]
        matched = []
        for ref in self.candidate_keyframes(tar):
            ref_kf = self.kfs[ref]
            inliers = 0
            if self.loop_mode in {"two_stage", "only_sift"}:
                init, inliers = self._sift_proposal(ref_kf, tar_kf)
                if init is None or inliers < self.min_sift_inliers:
                    continue
                self.n_candidates += 1
                if self.loop_mode == "only_sift":
                    tar_T_ref = init
                else:
                    tar_T_ref = self._register(ref_kf.frame, tar_kf.frame, init, self.loop_ccs, self.loop_scr)
            else:  # only_nf: NormalFlow from the current pose estimate, no SIFT preselection
                self.n_candidates += 1
                init = inv_se3(self.kf_pose[tar]) @ self.kf_pose[ref]
                tar_T_ref = self._register(ref_kf.frame, tar_kf.frame, init, self.loop_ccs, self.loop_scr)
            if tar_T_ref is None:
                continue
            ref_T_tar = inv_se3(tar_T_ref)
            self.edges.append((ref, tar, ref_T_tar))
            matched.append(ref)
            self.loops.append({"i": int(ref_kf.fid), "j": int(tar_kf.fid), "T_ij": ref_T_tar.tolist(),
                               "sift_inliers": int(inliers)})
        return matched

    def _loop_closure(self, tar: int) -> None:
        if self.loop_mode == "none":
            return
        matched = self._detect_loops(tar)
        merged_groups = []
        for ref in matched:
            ra = self._find(self.kfs[ref].session)
            rb = self._find(self.kfs[tar].session)
            if ra == rb:
                continue
            keep, drop = min(ra, rb), max(ra, rb)
            loop = [e for e in self.edges if e[0] == ref and e[1] == tar][-1]
            ref_T_tar = loop[2]
            if drop == rb:
                correction = (self.kf_pose[ref] @ ref_T_tar) @ inv_se3(self.kf_pose[tar])
            else:
                correction = (self.kf_pose[tar] @ inv_se3(ref_T_tar)) @ inv_se3(self.kf_pose[ref])
            dropped_members = self._component(drop)
            kept_members = self._component(keep)
            for k in dropped_members:
                self.kf_pose[k] = correction @ self.kf_pose[k]
            self.uf_parent[drop] = keep
            self.priors.pop(drop, None)
            merged_groups.append((dropped_members, kept_members))
        if matched:
            self.solve()
        for dropped, kept in merged_groups:
            self._coverage_merge(dropped, kept)
        self._update_coverage(tar)

    def solve(self) -> None:
        priors = list(self.priors.values())
        poses = optimize_pose_graph(np.asarray(self.kf_pose), self.edges, priors)
        self.kf_pose = [p for p in poses]
        self.n_solves += 1

    # ---------------- coverage set ----------------
    def _backproject_weight(self, w_tar: np.ndarray, pc_ref: np.ndarray, tar_T_ref: np.ndarray) -> np.ndarray:
        pts = pc_ref @ tar_T_ref[:3, :3].T + tar_T_ref[:3, 3]
        h, w = w_tar.shape
        xx = pts[:, 0] / self.ppmm + w / 2 - 0.5
        yy = pts[:, 1] / self.ppmm + h / 2 - 0.5
        return wide_remap(w_tar, xx, yy, cv2.INTER_NEAREST)

    def _overlap_weight(self, tar: int, ref: int) -> float:
        p_tar, p_ref = self.kf_pose[tar], self.kf_pose[ref]
        if float(p_ref[:3, 2] @ p_tar[:3, 2]) < 0:
            return 0.0
        tar_T_ref = inv_se3(p_tar) @ p_ref
        return float(np.sum(self._backproject_weight(self.kfs[tar].W, self.kfs[ref].pc, tar_T_ref)))

    def _revealed_weight(self, k: int) -> float:
        wk = self.kfs[k].Wc
        nbrs = self.cov_nbrs[k]
        if not nbrs:
            return float(np.sum(wk))
        p_k = self.kf_pose[k]
        cover = np.zeros_like(wk)
        for nb in nbrs:
            nb_T_k = inv_se3(self.kf_pose[nb]) @ p_k
            cover = np.maximum(cover, self._backproject_weight(self.kfs[nb].W, self.kfs[k].pc, nb_T_k))
        return float(np.sum(wk - np.minimum(wk, cover)))

    def _deactivate(self, k: int) -> None:
        for nb in list(self.cov_nbrs[k]):
            self.cov_nbrs[nb].discard(k)
        self.cov_nbrs[k] = set()
        self.cov_active[k] = False

    def _link_and_prune(self, k: int, others: list[int]) -> None:
        if not self.cov_active[k]:
            return
        for ref in others:
            if ref == k or not self.cov_active[ref]:
                continue
            if self._overlap_weight(k, ref) > self.coverage_threshold:
                self.cov_nbrs[ref].add(k)
                self.cov_nbrs[k].add(ref)
        if self._revealed_weight(k) < self.coverage_threshold:
            self._deactivate(k)
            return
        for nb in list(self.cov_nbrs[k]):
            if self.cov_active[nb] and self._revealed_weight(nb) < self.coverage_threshold:
                self._deactivate(nb)

    def _update_coverage(self, tar: int) -> None:
        root = self._find(self.kfs[tar].session)
        others = [r for r in range(tar) if self.cov_active[r] and self._find(self.kfs[r].session) == root]
        self._link_and_prune(tar, others)

    def _coverage_merge(self, dropped: list[int], kept: list[int]) -> None:
        kept_active = [k for k in kept if self.cov_active[k]]
        for k in dropped:
            self._link_and_prune(k, kept_active)

    # ---------------- outputs ----------------
    def frame_poses(self, n_frames: int) -> np.ndarray:
        out = np.zeros((n_frames, 4, 4))
        for fid in range(n_frames):
            out[fid] = self.kf_pose[self.parent[fid]] @ self.rel[fid]
        return out

    def stats(self) -> dict:
        return {
            "keyframes": len(self.kfs),
            "coverage_keyframes": int(sum(self.cov_active)),
            "tracking_sessions": self.n_sessions,
            "unmerged_sessions": len(self.priors),
            "loop_candidates": int(self.n_candidates),
            "loops": len(self.loops),
            "pose_graph_solves": self.n_solves,
        }


def run_gelslam(gradients: np.ndarray, heights: np.ndarray, contacts: np.ndarray, mm_per_pixel: float,
                slam: GelSLAM | None = None, **kwargs) -> tuple[np.ndarray, list[dict], dict]:
    slam = slam or GelSLAM(mm_per_pixel, **kwargs)
    cv2.setRNGSeed(int(slam.seed))
    n = len(gradients)
    for fid in range(n):
        frame = TactileFrame(gradients[fid], heights[fid], contacts[fid], mm_per_pixel)
        slam.process(fid, frame)
    if slam.loop_mode != "none" and slam.loops:
        slam.solve()
    return slam.frame_poses(n), slam.loops, slam.stats()
