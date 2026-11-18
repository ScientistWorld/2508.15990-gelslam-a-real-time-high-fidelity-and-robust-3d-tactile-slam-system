#!/bin/bash
# This validation job applies and checks all hardening changes together.
set -euo pipefail
cd /home/user
bash redteam/hardening/audit_review.sh
