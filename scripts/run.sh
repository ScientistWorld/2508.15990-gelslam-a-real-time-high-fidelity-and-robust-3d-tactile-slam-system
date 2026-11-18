#!/bin/bash
# Finish the enlarged paired headroom audit, then the independent reference.
set -euo pipefail
cd /home/user
bash redteam/hardening/audit_scale.sh
