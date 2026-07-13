#!/bin/bash
# ריסטארט-בלחיצה — עובד בשתי המכונות (מחפש את הריפו בכל המיקומים המוכרים).
for CAND in "$HOME/Downloads/mems26_web_git" "$HOME/mems26/mems26_web_git" "$HOME/mems26_web_git"; do
  if [ -f "$CAND/scripts/MEMS26_CONTROL.command" ]; then
    exec "$CAND/scripts/MEMS26_CONTROL.command" restart
  fi
done
echo "❌ הריפו לא נמצא במחשב הזה ($(hostname -s)) — אמור לסוכן."
read -r -p "Enter לסגירה…" _
