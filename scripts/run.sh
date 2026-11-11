#!/bin/bash
# Debug job: simulator noise calibration on full-length episodes.
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
python tmp/smoke/calib.py 2>&1 | tee tmp/smoke/calib.log
