#!/bin/bash
# משגר מסך-ההפעלה של MEMS26 — עובד בשתי המכונות (מייקל 07-13).
# מק-פיתוח: ~/Downloads/mems26_web_git · ‏iMac: ‏~/mems26/mems26_web_git
for CAND in "$HOME/Downloads/mems26_web_git" "$HOME/mems26/mems26_web_git" "$HOME/mems26_web_git"; do
  if [ -f "$CAND/scripts/MEMS26_CONTROL.command" ]; then
    exec "$CAND/scripts/MEMS26_CONTROL.command" "$@"
  fi
done

echo "══════════════════════════════════════════════════"
echo "❌ הריפו לא נמצא באף אחד מהמיקומים המוכרים במחשב הזה ($(hostname -s)):"
echo "   • $HOME/Downloads/mems26_web_git"
echo "   • $HOME/mems26/mems26_web_git"
echo "   • $HOME/mems26_web_git"
echo ""
echo "אם הריפו קיים במיקום אחר — אמור לסוכן ונוסיף אותו."
echo "אם זו חסימת-הרשאות: Settings → Privacy & Security → Full Disk Access → Terminal"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null
read -r -p "Enter לסגירה…" _
