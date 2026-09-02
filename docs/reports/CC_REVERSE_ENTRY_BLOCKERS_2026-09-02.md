# מה חוסם כניסה הפוכה אחרי יציאה — שער-פר-שער

**שאלת-מייקל:** "לזהות היפוך → לסגור → לאפשר כניסה."
**הבעיה:** אחרי סגירת LONG על כישלון-תקרה, מה מונע כניסת SHORT מיידית?

## השערים הרלוונטיים (קובץ:שורה)

| # | שער | קובץ:שורה | מה הוא עושה | חוסם היפוך? |
|---|---|---|---|---|
| 1 | **`live_slot_occupied`** | `trading_gateway.py:3631` | סלוט עדיין תפוס | 🔴 **כן** — אם FLATTEN/MODIFY_STOP לא שוטח עדיין, הסלוט תפוס ואין כניסה חדשה |
| 2 | **`cooldown`** | `trading_gateway.py:~152` + `cooldown.py` | N שניות אחרי סגירה | 🟡 **אפשרי** — `COOLDOWN_AFTER_CLOSE_S` (default 0 = כבוי) |
| 3 | **`cluster_guard`** | `trading_gateway.py:~2720` + `cooldown.py:ClusterGuard` | מניעת 3 ירי תוך 5 דקות | 🟡 **אפשרי** — הסגירה+כניסה-חדשה = 2 אירועים קרובים |
| 4 | **`duplicate_fire`** | `trading_gateway.py:~182` | אותו pattern+direction ב-10s | ✅ לא — כיוון הפוך = לא דופליקט |
| 5 | **`awaiting_release`** | `trading_gateway.py:~1539` | ממתין לשחרור מבני | 🔴 **כן** — אם הכיוון החדש מחכה לשחרור |
| 6 | **`daytype_playbook`** | `trading_gateway.py:~625` | סוג-יום×תבנית=SKIP | 🟡 **אפשרי** — תלוי בתבנית ובסוג-היום |
| 7 | **`direction_compass`** | `trading_gateway.py:~1027` | כיוון-היום נגד הכניסה | 🟡 **אפשרי** — אם המצפן עדיין מצביע בכיוון הישן |

## החוסם הדומיננטי: `live_slot_occupied`

**file:line**: `trading_gateway.py:3631`
```python
elif self.live_slot is not None:
    result["live_blocked_by"] = "live_slot_occupied"
```

STRUCTURE_EXIT שולח FLATTEN_ACCOUNT → `exit_verifier` מחכה לאישור (sierra_state qty=0) → רק אז הסלוט משתחרר. **בפער הזה — אין כניסה.**

T-43c (28.08) הידק את זה: הסלוט לא משתחרר עד `position_qty==0 AND working_orders==0`.

## מה חסר להיפוך מלא

1. **סלוט**: FLATTEN → אישור → שחרור → **אפשר כניסה הפוכה**. זה כבר עובד אם FLATTEN מצליח.
2. **תזמון**: הכניסה ההפוכה חייבת להיות **בבר-האישור עצמו** (מהמחקר: F3 שורט ב-18:45 = בר-אישור התקרה). כל איחור = "רחוקים מהתקרה".
3. **מה באמת חסר**: `CEILING_FLIP_SHORT_V1` — מודול שמחמש כניסה הפוכה מיד אחרי זיהוי CEILING_FAILED. הגלאי קיים (ceiling_floor_state.py), הצרכן לכניסה-הפוכה **טרם נבנה**.

## NOT-DONE

- `CEILING_FLIP_SHORT_V1` — כניסה הפוכה בבר-האישור, דרך `failed_break.py` הקיים
- cooldown calibration — האם cooldown_after_close צריך להיות 0 ספציפית אחרי structure_exit
