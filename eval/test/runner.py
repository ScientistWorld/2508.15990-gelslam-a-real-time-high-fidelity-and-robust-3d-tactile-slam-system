"""Fixed CPU accounting and an input-only filesystem for arbitrary method commands.

No elapsed-time limit is used. The supervisor counts CPU time for the command's
process group, including children, and Linux enforces a per-process backstop.
Landlock rules are inherited across exec/fork and cannot be relaxed by the method.
See https://www.kernel.org/doc/html/v6.6/userspace-api/landlock.html .
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

THREAD_KEYS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
               "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS", "OPENCV_FOR_THREADS_NUM")


def configure_cpu() -> None:
    for key in THREAD_KEYS:
        os.environ[key] = "1"
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    import cv2
    cv2.setNumThreads(1)


def _group_cpu_seconds(pgid: int) -> float:
    """Live + zombie CPU plus CPU of reaped children, counted once per group."""
    ticks = 0
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            # comm may contain whitespace and parentheses. Fields begin after its last ')'.
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid:  # stat field 5, pgrp
                ticks += sum(int(fields[k]) for k in (11, 12, 13, 14))  # utime/stime/cutime/cstime
        except (OSError, ValueError, IndexError):
            continue
    return ticks / os.sysconf('SC_CLK_TCK')


def run_isolated(command: list[str], input_path: Path, output: Path, root: Path, log_path: Path,
                 cpu_budget: int) -> dict:
    env = os.environ.copy()
    for key in THREAD_KEYS:
        env[key] = "1"
    env['PYTHONPATH'] = str(root)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['TMPDIR'] = str(output / 'tmp')
    env.pop('TACTILE_EVAL_CACHE', None)
    (output / 'tmp').mkdir()
    wrapper = [sys.executable, str(Path(__file__).resolve()), str(root), str(input_path), str(output),
               str(cpu_budget), json.dumps(command)]
    start = time.monotonic()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with log_path.open('ab') as log:
        log.write(('\n$ ' + ' '.join(command) + '\n').encode())
        log.flush()
        proc = subprocess.Popen(wrapper, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        used = 0.0
        exceeded = False
        while True:
            used = max(used, _group_cpu_seconds(proc.pid))
            if used > cpu_budget:
                exceeded = True
                os.killpg(proc.pid, signal.SIGKILL)
            if proc.poll() is not None:
                break
            time.sleep(0.2)  # observation interval only; never a completion deadline
        # No unfinished method work can be left outside the accounted episode.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        used = max(used, child_after.ru_utime + child_after.ru_stime - child_before.ru_utime - child_before.ru_stime)
        log.write(f'[evaluator] cpu_seconds={used:.6f} budget={cpu_budget} affinity=1 threads=1\n'.encode())
    if exceeded or used > cpu_budget or proc.returncode in (-signal.SIGXCPU, -signal.SIGKILL):
        raise RuntimeError(f'CPU budget exceeded ({cpu_budget} CPU seconds per episode)')
    if proc.returncode != 0:
        raise RuntimeError(f'command exited with code {proc.returncode}')
    return {"seconds": time.monotonic() - start, "cpu_seconds": used}  # diagnostics only


def restrict_filesystem(root: Path, input_path: Path, output: Path) -> None:
    """Deny reads of eval/git/history/results; permit writes only in this output."""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 1:
        raise RuntimeError(f'Landlock required, unavailable: errno={ctypes.get_errno()}')
    # Filesystem ABI 1 rights, plus REFER (ABI 2) and TRUNCATE (ABI 3).
    handled = (1 << 13) - 1
    if abi >= 2:
        handled |= 1 << 13
    if abi >= 3:
        handled |= 1 << 14
    read_file = (1 << 0) | (1 << 2)  # EXECUTE | READ_FILE
    read_dir = 1 << 3
    read = read_file | read_dir
    write_file = (1 << 1) | ((1 << 14) if abi >= 3 else 0)

    class Ruleset(ctypes.Structure):
        _fields_ = [('handled_access_fs', ctypes.c_uint64)]

    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]

    attrs = Ruleset(handled)
    fd = libc.syscall(444, ctypes.byref(attrs), ctypes.sizeof(attrs), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'landlock_create_ruleset')

    def allow(path: Path, rights: int):
        if not path.exists():
            return
        pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        try:
            if not path.is_dir():
                rights &= read_file | write_file
            attr = Beneath(rights, pfd)
            if libc.syscall(445, fd, 1, ctypes.byref(attr), 0) < 0:
                raise OSError(ctypes.get_errno(), f'landlock_add_rule {path}')
        finally:
            os.close(pfd)

    try:
        # Runtime libraries and OS metadata; no workspace or generic /tmp grant.
        for path in ['/usr', '/bin', '/sbin', '/lib', '/lib64', '/etc', '/sys']:
            allow(Path(path), read)
        for path in ['/dev/null', '/dev/urandom', '/dev/random']:
            allow(Path(path), read_file | (1 << 1))
        for path in ['/proc/self', '/proc/cpuinfo', '/proc/meminfo']:
            allow(Path(path), read)
        allow(root, read_dir)  # Python module discovery, no file-content grant
        excluded = {'eval', 'tmp', 'jobs', 'logs', 'scoring', 'trajectory', 'shared'}
        for path in root.iterdir():
            if path.name.startswith('.') or path.name in excluded:
                continue
            # Audit reports are readable, but private saved error arrays live under eval/.
            allow(path, read)
        allow(input_path, read_file)
        allow(output, handled)
        if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
            raise OSError(ctypes.get_errno(), 'PR_SET_NO_NEW_PRIVS')
        if libc.syscall(446, fd, 0) < 0:
            raise OSError(ctypes.get_errno(), 'landlock_restrict_self')
    finally:
        os.close(fd)


def main():
    root, inp, out, budget, command = sys.argv[1:]
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_CPU, (int(budget), int(budget) + 1))
    restrict_filesystem(Path(root), Path(inp), Path(out))
    args = json.loads(command)
    os.execvpe(args[0], args, os.environ)


if __name__ == '__main__':
    main()
