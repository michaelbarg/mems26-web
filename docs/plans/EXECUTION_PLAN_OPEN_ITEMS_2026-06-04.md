# תוכנית-ביצוע — כל הפתוחים: prompts, החלטות, עדיפות | 2026-06-04

מצב: מחלקת ה-DB סגורה (PG). S1/S2-fix in-flight. כל הנותר non-DB. סדר לפי עדיפות.
מקרא: 🟢 prompt מוכן · ✍️ prompt חדש לכתוב · ⚙️ bring-up (Mac-side, לא prompt) · ✅ החלטה ניתנה · ⏳ החלטה חסרה.

## P1 · לפתוח SHADOW (הכי קרוב — חוסם איסוף)
| פריט | prompt | החלטה |
|---|---|---|
| שירותים על PG ב-RTH + feed זורם (frozen-tail watch) | ⚙️ Mac-side | ✅ |
| כל הדגלים ON (כולל S2_VSA_VOLUME) | 🟢 `CC_PROMPT_ENABLE_FLAGS_SHADOW` | ✅ |
| pre-trade / `RTH_VERIFICATION_FULL_PASS` | ⚙️ פרוטוקול קיים | ✅ |
| (in-flight) S1 re-eval + D-090 + S2 VSA | 🟢 נשלח, ממתין אימות-Cowork | ✅ |

## P2 · במקביל ל-SHADOW (UX + data quality)
| פריט | prompt | החלטה |
|---|---|---|
| עיצוב-מחדש Trades | 🟢 `AGENT_PROMPT_TRADES_PAGE_REDESIGN` | ✅ (תאשר עיצוב בסוף) |
| עיצוב-מחדש Build-Status | 🟢 `DESIGNER_PROMPT_BUILD_STATUS_REDESIGN` | ⏳ **cull: איפה Build חי (/build בלבד מול דאשבורד) + ReadinessHeader keep/drop** |
| Config→YAML (auth/targets) | 🟢 `CC_PROMPT_CONFIG_YAML_AUTH_TARGETS` (רץ אחרי ה-audit) | ✅ Option A |
| Stop-anchor (VAH/POC/daily/swing) | ✍️ design proposal (אחרי go) | ⏳ **go + אילו anchors + כללים** |
| פערי build-status (TARGETS/STOP ל-S2/S4 · שערים גלובליים pre_fire/risk_checks · S5 TPO · S6 Killzone) | ✍️ backend (1–3 prompts) | ⏳ **drift: S3 firing/observer · killzone 8 מול 11 אזורים** |

## P3 · תוצר SHADOW soak (אחרי שנפתח)
| פריט | prompt | החלטה |
|---|---|---|
| ≥10 ימי RTH + ≥20 עסקאות | ⚙️ הרצה | ⏳ go/no-go ל-DEMO בסוף |
| כיול ספי-ATR יחסיים (k) | ✍️ (אחרי דאטה) | ⏳ **נעילת k אחרי soak** |
| סקירת תבניות חלשות (GB100/ZLR/VEGAS) | ✍️ (אחרי דאטה) | ⏳ **אילו לכבות** |

## P4 · חוסמי-LIVE (אחרי SHADOW→DEMO; חלק רץ במקביל)
| פריט | prompt | החלטה |
|---|---|---|
| **Pipeline 5 — נתיב הזמנה לסיארה** (החוסם-LIVE האמיתי) + Gateway MERGE | 🟢 `META_PROMPT_PIPELINE5...` | ⏳ **P5-1 ואילך** (Q1/Q2 נעולים) |
| Fix 3+4 — ניהול-עסקה על live_price + bad-tick/staleness | 🟢 `CC_PROMPT_TRADE_MGMT_LIVEPRICE_FIX3_FIX4` | ✅ active-from-start |
| DEMO (≥7 ימים, IronBeam) → LIVE קדם-טיסה (risk caps/kill-switch/alerting/UAT) | ✍️ (בהמשך) | ⏳ go/no-go ל-LIVE |

## P5 · ניקויים לפני LIVE (לא-חוסמים)
| פריט | prompt | החלטה |
|---|---|---|
| פרישת shim `INSERT OR REPLACE`→`ON CONFLICT` · הסרת fallback SQLite ב-main.py · 3 טסטי woodies HFE/B3 | ✍️ prompt-ניקוי אחד | ✅ |

## סיכום ספירה
- **prompts מוכנים (🟢):** 6 — ENABLE_FLAGS_SHADOW · TRADES_REDESIGN · DESIGNER_BUILD_STATUS · CONFIG_YAML · TRADE_MGMT_LIVEPRICE · PIPELINE5. (+ S1/S2-fix נשלח.)
- **prompts חדשים לכתוב (✍️):** ~5 — stop-anchor · build-status backend gaps · k-calibration · weak-pattern review · cleanup. (כולם בתזמון מאוחר יותר.)
- **החלטות חסרות שלך (⏳):** (1) Build-Status cull · (2) Stop-anchor go+כללים · (3) build-status drift (S3 firing/observer, killzone 8/11) · (4) post-soak: נעילת k + כיבוי תבניות · (5) Pipeline 5 P5-1+.

**הצעד הקרוב:** P1 — להעלות שירותים+feed ב-RTH ולפתוח SHADOW (אחרי אימות ה-S1/S2-fix). החוסם-LIVE האמיתי בהמשך = Pipeline 5.
