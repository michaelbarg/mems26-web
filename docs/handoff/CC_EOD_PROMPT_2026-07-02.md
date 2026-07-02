# פרומפט-ערב ל-Claude Code · 2026-07-02 (להדבקה כלשונו)

---
קרא לפי הסדר, ואל תיגע בקוד לפני שסיימת לקרוא:
1. `docs/handoff/EVENING_EXECUTION_CHECKLIST_2026-07-02.md` — הצ'קליסט המחייב של הלילה (בקרה אוטומטית תרוץ ב-23:20 ותתריע על כל מה שחסר).
2. `docs/handoff/CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md` — חבילת **20 הפריטים** המאושרים (כולם flag-gated default-OFF אלא אם צוין; עריכות-תאי-playbook = שינוי-חי-בריסטארט — ראה אזהרה בפריט-1).
3. `docs/plans/MICHAEL_ISSUES_LEDGER.md` — ההקשר: מה כל פריט פותר ולמה.
4. `docs/handoff/CC_HANDOFF_CONTRACT.md` — טסטים אנטי-טאוטולוגיים (שנכשלים-על-הישן!), פלט גולמי, NOT-DONE חובה.

**מה כבר חי מהיום (אל תיגע/אל תשחזר):** I-57 (slot+self-heal) · COOLDOWN_2STOP_V1 default-OFF (סטנדינג!) · I-58 (fill routing) · I-59 (sanitize+loud-log) · I-60 (dedup-אחרי-גייטים) · I-61 (target-side guard) · hydrate-fix. הטסטים שלהם ב-tests/v9/regression/ — כולם חייבים להישאר ירוקים.

**סדר-בנייה:** 2 (רזולבר — כולל רצפת-C1, מונוטוניות, עיגול-גריד, ATR-חי, אינווריאנט-BE, מלאי-רמות-אתמול; הראיות החיות 277-282 בגוף הפריט) → 1 (תאים+aliases) → 3 (RR_ENTRY_GATE_V1) → 4 (STOP_RESOLVER_V1 + חישוב-אחורה גולמי) → 18 (דוקטרינה+מצב-טרנד-בתוך-Variation) → 16 (VOL_REGIME_V1) → 5, 6, 13 (ווליום/אישורי-כניסה/P-b) → 12 (TT_SPEC_V2 לפי מסמך-המקור) → 10 (OPENING_WINDOW_FIRE_V1 + תיקון-I-53 באותו קומיט — יעד: הפתיחה של מחר) → 11 (ריכוז-notify ב-TradeManager + צמצום-fallback) → 17 (יומן-החלטות PG+API; ה-UI שלו יגיע מ-Cowork) → 20 (reconcile — לפחות שלב-ה-DLL-spec אם הזמן קצר) → 7+8 (מחקר בלבד — דוחות).
**פריט-19:** בנה את השלד (דגל+חיווט-daily_pnl-פר-מצב) אבל **אל תפעיל** — המספרים של מיכאל טרם נמסרו.
**סולמות-תבניות חסרים (HTLB/TLB/GB100/DBDT/HNS):** אם ההליכה בצ'אט-השני עדכנה את `PATTERN_RECONCILIATION` — בנה לפיה; אחרת בנה עם הנוכחיים וסמן NOT-DONE.

**חובות-סיום:** commit ל-UI-src שעדיין uncommitted (frontend/v9/src — חי ויציב מהיום) · טסט-Mechanism-C התנהגותי (מחליף הטאוטולוגי, ממצא-הביקורת) · כל דגל חדש ל-FLAG_REGISTRY.yaml (+3 החסרים: FIXED_CONTRACTS_3/DAYTYPE_CONFIRM_BARS/OPPOSITE_EXIT_THRESHOLD) → `gen_flag_index.py` · `gen_index.py` · STATUS_BOARD+ROADMAP (רשומת-לילה: root+fix+verified per item) · ריסטארט-סיום (0 פתוחות; אחרי 23:00) + הדבקת boot-line.
**NOT-DONE בסוף — בכנות מלאה.** בהצלחה.
---
