#!/bin/bash
# MEMS26 Restart All — stop + start
# Usage: bash scripts/restart_all.sh  OR  mems-restart

bash /Users/michael/Downloads/mems26_web_git/scripts/stop_all.sh
sleep 3
bash /Users/michael/Downloads/mems26_web_git/scripts/start_all.sh
