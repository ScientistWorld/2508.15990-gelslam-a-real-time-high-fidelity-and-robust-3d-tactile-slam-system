#!/bin/bash
# Current hardening audit. Historical iteration-11 results remain in results/.
set -e
cd /home/user
exec bash redteam/hardening/audit_review.sh
