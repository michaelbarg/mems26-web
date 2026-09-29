#!/bin/bash
# T-517 (29.09 16:3x): waits until 23:00 IL (the end of RTH), then runs the night replay. Started in the background by
# the interactive cowork-dev session so the measurement does not depend on a scheduled Cowork run being approved.
cd /Users/michael/Downloads/mems26_web_git || exit 1
echo "WAITING since $(date)" > harness_out/t517/wait_2300.out
while [ "$(TZ=Asia/Jerusalem date +%H%M)" -lt 2300 ]; do sleep 60; done
echo "GO $(date)" >> harness_out/t517/wait_2300.out
bash harness_out/t517/run_night.sh
echo "EXIT rc=$? $(date)" >> harness_out/t517/wait_2300.out
