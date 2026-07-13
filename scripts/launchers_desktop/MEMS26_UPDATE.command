#!/bin/bash
# כפתור-עדכון — מושך את הגרסה האחרונה ומיישם (§10). עובד בשתי המכונות.
for CAND in "$HOME/Downloads/mems26_web_git" "$HOME/mems26/mems26_web_git" "$HOME/mems26_web_git"; do
  if [ -f "$CAND/scripts/MEMS26_CONTROL.command" ]; then
    exec "$CAND/scripts/MEMS26_CONTROL.command" update
  fi
done
echo "❌ הריפו לא נמצא במחשב הזה ($(hostname -s)) — אמור לסוכן."
read -r -p "Enter לסגירה…" _
