#!/bin/bash
# Debug job: smoke test and simulator calibration diagnostics.
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
python -c "import numpy, scipy, cv2; print(numpy.__version__, scipy.__version__, cv2.__version__)"
nproc || true
python tmp/smoke/smoke.py 2>&1 | tee tmp/smoke/smoke.log
