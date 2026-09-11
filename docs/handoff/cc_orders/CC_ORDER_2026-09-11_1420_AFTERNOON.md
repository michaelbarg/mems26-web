## אחה"צ 11.09 — אימות-cowork על `0c62af06` (הרנס ×4, `/tmp/h1109b/`) + מה שנשאר. **אין ריסטארט ידני — המתוזמן ב-15:45 עושה זאת** על HEAD שעובר את הגולדנים; כל קומיט אחרי 15:30 = על אחריותך שההרנס ירוק.

### מאומת (לא ✅ עד שיש קובץ-מבחן — ראה למטה)
- **T-314(a)+(b)** — `[S1-OPENING] T-314: NEGATED OPEN_REJECTION_REVERSE → re-read=OPEN_AUCTION_IN dir=NEUTRAL (rej_high=7606.50 rej_low=7593.75)` ב-**16:55:03** (סגירת בר 16:50 < 7593.75) ✓ · בעל-אחד: `opening_lock.update_opening_lock` נקרא מ-`main.py:370` **ו**מ-`fwd_harness.py:769` ✓.
- **T-315** — `20:30:03 DOUBLE_TOP_AA_SHORT 7605.25 → dalton_intent:kind` מופיע ב-routes של 10.09 ✓ (חסום kind — צפוי עד T-316/T-319).
- **T-313** — `17:30:09 INITIATIVE_LONG → dalton_intent:kind` ✓ · 08-03/08-04/09-09 — אותה כתיבה אחת בכל אחד ✓ · 10.09 אפס כתיבות ✓ · 0 Traceback.
- שער-הבוקר (סוכן-cowork 13:50, `docs/reports/PREOPEN_SWEEP_2026-09-11.md`): flag_guard 252/252 · task_log_guard 0 · wire_guard 0 · guard_tests 160/0 · fire_drill GO · `.env` לא נגעו · `STRUCTURE_EXIT_REALIZE_PRE_T1_V1` לא ב-.env ⇒ כבוי.

### לעשות, לפי הסדר
1. **קבצי-מבחן-רגרסיה** (השורות T-313/T-314/T-315 פתוחות רק בגללם): `backend/v9/tests/test_t313_label_handoff.py` · `test_t314_opening_lock.py` (גיאומטריית 10.09: lock ORR/UP ב-16:45, negate על close<rej_low, **ו**מבחן-מוטציה שמוכיח ש-close>rej_high לא מפריך UP) · `test_t315_chain_fallthrough.py` (מנצח נחסם-בשער ⇒ הבא מנותב). אחרי שהם ירוקים — ✅ + שורת-לוח.
2. **T-316 / T-319a — למדוד מחדש** לפי שתי ההערות של cowork 13:13 ו-13:19 (בראש LIVE_CHANNEL): סים שמסוגל להפסיד (סטופ מעבר לקצה, ברי-5דק'), `$5`/נקודה × חוזים, אין ערבוב דולרים-עם-סימנים, המכנה האמיתי (יש רק 3 ימים מתויגים ב-`v9_day_type_state` — להגיד זאת, לא "מאז 01.08"), ו-`zone_of` **מיובא** מ-`location_gate` ולא מועתק. **לא להציג למייקל את +794.**
3. **T-312** — מה שנשאר: `gen_wiring_index.py --check` (קורא-בלי-כותב = כשל) · `GET /api/v9/wiring` · `wiring_guard.py` ב-`fire_drill`. הרנס-דרך-main.py נעשה לנעילת-הפתיחה בלבד — להרחיב לשאר הרג'יסטרי.
4. `config_consumer_guard.py` rc=1 — 13 שדות-YAML בלי צרכן (`daytype_playbook.yaml`/`stop_anchors.yaml`). לא בשער; לסגור בלילה: למחוק שדה מת או לחווט.
5. T-317 נשאר כבוי (n=0 = אין ראיה, לא "עובד"). לא להדליק.

כל פריט = קומיט + TASK_LOG + STATUS_BOARD **באותו קומיט** + LOG חתום עם פלט גולמי. אפס `.env`, אפס דגלים, אפס pytest כבד אחרי 16:10.
