# בדיקת-אינטגרציה Sierra fill-detection — לפני-לייב · 2026-07-14

**מכונה:** iMac · **מצב:** SIM (is_sim=1) · **מטרה:** לוודא שהמערכת קוראת מסיירה נכון — כניסה, מחיר, T1/T2/T3, סטופ, וסגירה — **לפני מעבר ללייב.**

## מתודולוגיה
‏BUY 3-contract bracket דרך `POST action=BUY` (op=PLACE) על סים, עם ניטור:
`trade_fills.json` → `trade_fills_journal.jsonl` → לוג-FillPoller → SYS-3 reconciler → v9_trades.

## ממצאים — המסלול Sierra→backend **עובד** (מחירים מדויקים)
| רכיב | תוצאה | ראיה |
|---|---|---|
| כניסה + qty + avg_price | ✅ | `sierra_state`: qty=3, avg=7564.75; ‏orders[] נושא את הברקט (target/stop, price, qty) |
| DLL כותב fills (מחיר מדויק) | ✅ | `journal`: `{"kind":"ENTRY","price":7564.75,...}` · `{"kind":"STOP","price":7563.75,"group":1}` ×3 |
| FillPoller קורא kind+price | ✅ | לוג: `kind=ENTRY price=7564.75` · `kind=STOP price=7563.75` |
| זיהוי-סגירה / פנטום | ✅ | `SYS-3 RECONCILER: DIVERGENCE: TM says 0, Sierra says 3 → reconcile/flatten NOW` |
| T1/T2/T3 | ⚠️ ביטחון-גבוה (לא-נורה) | קוד סימטרי ל-STOP: `sc_study/…:1503 tgt_kinds[]={T1,T2,T3}` · `:1516 SCT_OSC_FILLED` · `:1522` כותב kind+AvgFillPrice. במבחן המחיר ירד→סטופ (לא עלה→target) |

**תיקון להערה קודמת שלי:** `trade_fills.json` ריק **כי FillPoller צורך אותו** (offset-tracking, מעביר ל-journal) — **לא כי שבור.** המסלול תקין.

## המגבלה היחידה — קורלציה fill→v9_trades לא-נבדקה מקצה-לקצה
ה-BUY הידני **לא יוצר שורת v9_trades** (רק פייר S2/S4 יוצר) → כל המימושים סומנו **ORPHAN**:
`[FillPoller] ORPHAN FILL — no trade for order_id=6803 kind=ENTRY price=7564.75`. זה **צפוי** לפקודה-ידנית.
המנגנון לקורלציה קיים (I-58 fallback: `ORDER_SUBMITTED parent_id=… will need I-58 fallback`), אבל
**החוליה הסופית — fill → `v9_trades` (`t1_hit_ts`/`exit_price`) — דורשת פייר-אמיתי כדי לאמת.**

## הכרעה
מסלול קריאת-המימושים מסיירה **פונקציונלי ומדויק** (kind + מחיר-אמת + group). ה-orphan-detection +
SYS-3 + phantom-heal פועלים כרשת-בטיחות. **אין חוסם-לייב טכני** — אבל ה**קורלציה ל-v9_trades +
gsheets/live-ledger** צריכה להיבחן על ה**עסקה-האמיתית הראשונה** (cc-imac יעקוב צמוד ברגע הפייר הראשון:
qty בסיירה → journal event → v9_trades T*_HIT/exit_price → שורה בגיליון). המלצה: לפתוח בגודל-מינימלי
ולוודא את הקורלציה על הפייר הראשון לפני הגדלה.

## פעולות לדב (→ S-3)
1. **לאמת קורלציה** על פייר-אמיתי: fill journal → v9_trades (t1/t2/t3_hit_ts, exit_price=AvgFillPrice) → gsheets. אם ה-ORPHAN-fallback (I-58) לא ממפה — לתקן.
2. ה-orphan-counter תפח מ-BUY-ידני-בבדיקה (orphans=7) — לוודא ריסט/דעיכה נקי (לא זליגה ל-live incident).
