#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  MEMS26 — מפעיל בלחיצה כפולה
#  מריץ את scripts/start_all.sh (Bridge + Backend + Frontend)
#  ולא משכפל שירות שכבר רץ. לא משנה שום קונפיגורציה.
# ═══════════════════════════════════════════════════════════════
cd /Users/michael/Downloads/mems26_web_git || {
  echo "🔴 לא נמצאה תיקיית הריפו"; read -n 1; exit 1;
}

bash scripts/start_all.sh

# פתיחת הדאשבורד בדפדפן (אם עלה)
sleep 1
open http://localhost:3000 2>/dev/null || true

echo ""
echo "───────────────────────────────────────────────"
echo "  ✅ סיום. הדאשבורד: http://localhost:3000"
echo "  לסטטוס: mems   ·   לעצירה: mems-stop"
echo "  (אפשר לסגור את החלון)"
echo "───────────────────────────────────────────────"
echo "הקש מקש כלשהו לסגירה..."
read -n 1
