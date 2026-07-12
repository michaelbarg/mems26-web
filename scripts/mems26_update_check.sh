#!/bin/bash
# mems26_update_check.sh — רץ כל שעה (LaunchAgent com.mems26.update_check):
# git fetch שקט; אם המכונה מפגרת אחרי origin — התראת-macOS עם מה-נדרש
# (כולל "יידרש Remote Build" כש-sc_study השתנה). מתריע פעם אחת לכל HEAD חדש.
set -uo pipefail
REPO="${MEMS26_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BRANCH="stabilize/mems26-local-truth-2026-05-16"
STATE="$HOME/.mems26_last_notified_head"
cd "$REPO" || exit 0

git fetch -q origin "$BRANCH" 2>/dev/null || exit 0
REMOTE=$(git rev-parse origin/"$BRANCH" 2>/dev/null) || exit 0
BEHIND=$(git rev-list --count HEAD..origin/"$BRANCH" 2>/dev/null || echo 0)
[ "$BEHIND" = "0" ] && exit 0
[ -f "$STATE" ] && [ "$(cat "$STATE")" = "$REMOTE" ] && exit 0   # כבר התרענו על זה

FILES=$(git diff --name-only HEAD..origin/"$BRANCH" 2>/dev/null)
EXTRA=""
echo "$FILES" | grep -q "^sc_study/"         && EXTRA="$EXTRA • יידרש Remote Build בסיירה"
echo "$FILES" | grep -q "config/RULED_FLAGS" && EXTRA="$EXTRA • ייתכנו דגלי .env חדשים"
echo "$FILES" | grep -q "^bridge/"           && EXTRA="$EXTRA • ריסטארט bridge"

osascript -e "display notification \"$BEHIND קומיטים חדשים$EXTRA\" with title \"MEMS26 — עדכון זמין\" subtitle \"פתח את מסך-ההפעלה → עדכן לגרסה האחרונה\" sound name \"Glass\"" 2>/dev/null
echo "$REMOTE" > "$STATE"
