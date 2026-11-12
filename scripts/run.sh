#!/bin/bash
# Job entry point: reproduce the reference end to end (CPU only).
# Registers GelSLAM, scores it with the eval-owned NormalFlow baseline on the
# public training episodes (scoring/scores.json, scoring/scores_train.json)
# and on the hidden held-out episodes (scoring/scores_test.json), then
# validates the workspace.
#
# The hardening audit (variants, brute force, shortcuts, rank summaries) is
# redteam/hardening/audit.sh; see HARDENING.md.
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
bash scripts/reproduce.sh
python validate.py
