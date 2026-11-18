#!/bin/bash
# Reproduce the reference end to end. Audit/recovery scripts are separate.
set -euo pipefail
cd /home/user
bash scripts/reproduce.sh
python validate.py
