"""T-159 regression — ציון-המודעות חייב להישאר מדיד, כן, ומודע-T-100.

הציון חושב שלוש פעמים מ-`/tmp/awareness_fix.py` ונעלם איתו. הטסט הזה נועל את
שלוש התכונות שבלעדיהן הוא היה חוזר להיות "מספר שמישהו הריץ פעם":

1. **חישוב נכון על קלט ידוע** — 78 ברים סינתטיים + 13 צילומי-TPO נותנים
   יום 65/78 ורמות 78/78 (בדיוק התקדים המאומת של 25.08), ונגיעת-VA נספרת
   כ"מודעת" רק כשיש DETECTED בחלון.
2. **חוסר-נתון מחזיר None, לא 0** — ציר בלי מקור הוא `NOT-MEASURABLE` עם
   סיבה, ולעולם לא `0/78 = 0%` (זה היה נקרא כ"המערכת עיוורת" במקום
   כ"לא מדדנו"). Rule 1: כישלון-כנה > ערך מסונתז.
3. **מודעות-T-100** — הסטת ה-‎−3ש' ב-`v9_tpo_history` מתוקנת מהמדידה מול
   `created_at`, ולכן יום נגוע (≤28.08) ויום נקי (≥31.08) חייבים להחזיר את
   **אותו** ציון. הרגרסיה שנמנעת כאן היא "להוסיף 3 שעות תמיד" — שהיה מזיז
   את כל הצילומים של כל יום שאחרי 31.08 ומייצר ציון שקרי.

if reverted → RED because: פרסר שקורא `ts` בלבד מפיל את 108/202 שורות
ה-candidate_ledger.v1 (T-420) והמכנה מפסיק להסתכם; תיקון-T-100 עיוור שובר את
שוויון שני הימים; והחזרת 0 במקום None מחזירה ציון מומצא.
"""
import json
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from scripts.awareness_score import (
    Bar,
    normalize_tpo,
    parse_ledger_lines,
    score_day,
)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
DAY = date(2026, 8, 25)

VAH, VAL, POC = 7700.0, 7680.0, 7690.0


def _bar_ts(i):
    return datetime.combine(DAY, time(9, 30), tzinfo=ET) + timedelta(minutes=5 * i)


def _bars(touch_idx=()):
    """78 ברי-RTH. ברים ב-touch_idx נוגעים ב-VAH, השאר רחוקים מה-VA."""
    out = []
    for i in range(78):
        if i in touch_idx:
            out.append(Bar(_bar_ts(i), VAH - 1, VAH + 1, VAH - 2, VAH))
        else:
            out.append(Bar(_bar_ts(i), 7750, 7752, 7748, 7751))
    return out


def _raw_tpo(skew_hours, carry_over=True):
    """13 צילומי-היום (09:30→15:30 ET) בצורת-ה-DB הגולמית, + גרירה מאתמול.

    skew_hours=3 מדמה את T-100: הכותב כתב naive-UTC לעמודת timestamptz תחת
    TZ=Asia/Jerusalem ⇒ ה-ts שנשמר מוקדם ב-3ש' מרגע-האמת, בעוד `created_at`
    (ברירת-מחדל now()) נשאר רגע-אמת.

    הצילום של הסשן הקודם אינו קישוט: בלעדיו לבר 09:30 אין VA *לפני* פתיחתו,
    וציר-הרמות יורד ל-77/78. הרמות נגררות בין סשנים — ה-IB לא.
    """
    rows = []
    if carry_over:
        prev = datetime.combine(DAY - timedelta(days=1), time(15, 30), tzinfo=ET)
        rows.append((prev - timedelta(hours=skew_hours), prev + timedelta(seconds=5),
                     POC, VAH, VAL, 7710.0, 7670.0))
    for k in range(13):
        true_ts = datetime.combine(DAY, time(9, 30), tzinfo=ET) + timedelta(minutes=30 * k)
        rows.append((true_ts - timedelta(hours=skew_hours),
                     true_ts + timedelta(seconds=5),
                     POC, VAH, VAL, 7710.0, 7670.0))
    return rows


def _ledger(detected_bars=(), gate_bars=()):
    """שתי משפחות-הרשומות שחיות באותו קובץ (מלכודת T-420)."""
    lines = []
    for i in detected_bars:                       # candidate_ledger.v1 — בלי "ts"
        lines.append(json.dumps({
            "schema": "candidate_ledger.v1", "event_type": "DETECTED",
            "observed_at": (_bar_ts(i).astimezone(UTC) + timedelta(seconds=3)).isoformat(),
            "signal_bar_ts": _bar_ts(i).astimezone(UTC).isoformat(),
            "system": 4, "pattern": "VEGAS"}))
    for i in gate_bars:                           # gateway — עם "ts"
        lines.append(json.dumps({
            "ts": _bar_ts(i).astimezone(UTC).isoformat(), "event_type": "GATE_DECISION",
            "system": 2, "pattern": "DALTON_EDGE_LONG", "outcome": "blocked"}))
    return lines


def _score(skew_hours=0, touch_idx=(20, 40), detected_bars=(20,), gate_bars=(),
           with_tpo=True, with_ledger=True, extra_lines=(), carry_over=True):
    snaps = normalize_tpo(_raw_tpo(skew_hours, carry_over)) if with_tpo else []
    lines = list(_ledger(detected_bars, gate_bars)) + list(extra_lines)
    events, census = parse_ledger_lines(lines if with_ledger else [])
    return score_day(DAY, _bars(touch_idx), snaps, events, census,
                     tpo_available=bool(snaps), ledger_available=with_ledger)


# ── 1 · חישוב נכון על קלט ידוע ───────────────────────────────────────────────

def test_day_and_levels_match_the_verified_precedent():
    """יום 65/78 · רמות 78/78 — המספרים המאומתים של 25.08."""
    res = _score()
    assert res["rth_bars"] == 78
    assert (res["axes"]["day"]["n"], res["axes"]["day"]["d"]) == (65, 78)
    assert round(res["axes"]["day"]["pct"], 1) == 83.3
    assert res["axes"]["day"]["ok"] is True
    assert (res["axes"]["levels"]["n"], res["axes"]["levels"]["d"]) == (78, 78)
    assert res["axes"]["levels"]["pct"] == 100.0
    # 13 הברים החסרים בציר-היום הם בדיוק 09:30-10:25 ET (לפני סגירת ה-IB)
    assert 78 - res["axes"]["day"]["n"] == 13


def test_levels_carry_over_between_sessions_but_ib_does_not():
    """בלי צילום מהסשן הקודם, בר-הפתיחה נשאר בלי רמות — והיום לא זז.

    זה המפריד בין שני הצירים: רמה נשארת רמה גם למחרת, IB הוא של הסשן הזה.
    """
    without = _score(carry_over=False)
    assert without["axes"]["levels"]["n"] == 77          # בר 09:30 בלי VA שקדם לו
    assert without["axes"]["day"]["n"] == 65             # ציר-היום אדיש לגרירה


def test_candidates_counts_only_touches_with_a_detected():
    """שתי נגיעות-VA, DETECTED על אחת ⇒ 1/2. המכנה הוא הנגיעות, לא 78."""
    res = _score(touch_idx=(20, 40), detected_bars=(20,))
    cand = res["axes"]["candidates"]
    assert (cand["n"], cand["d"]) == (1, 2)
    assert cand["pct"] == 50.0 and cand["ok"] is False
    assert [t for t, _ in res["missed_touches"]] == [_bar_ts(40).strftime("%H:%M")]


def test_detected_on_the_next_bar_still_counts():
    """הגלאי יורה על הבר הבא — נספר (חלון 0-1), ובר רחוק יותר לא."""
    assert _score(touch_idx=(20,), detected_bars=(21,))["axes"]["candidates"]["n"] == 1
    assert _score(touch_idx=(20,), detected_bars=(23,))["axes"]["candidates"]["n"] == 0


def test_decisions_counts_distinct_bars_across_both_record_shapes():
    """T-420: DETECTED (signal_bar_ts) ו-GATE_DECISION (ts) נספרים יחד.

    פרסר שקורא `ts` בלבד היה מחזיר 2 במקום 3 — וזה בדיוק העיוורון שהפיל
    108 מ-202 שורות ב-18.09.
    """
    res = _score(touch_idx=(), detected_bars=(5, 6), gate_bars=(6, 30))
    dec = res["axes"]["decisions"]
    assert (dec["n"], dec["d"]) == (3, 78)        # ברים 5,6,30 — 6 נספר פעם אחת
    c = res["ledger_census"]
    assert c["parsed"] + c["json_bad"] + c["no_usable_ts"] == c["lines"] == 4
    assert c["by_event"] == {"DETECTED": 2, "GATE_DECISION": 2}


# ── 2 · חוסר-נתון ⇒ None, לעולם לא 0 ─────────────────────────────────────────

def test_missing_tpo_is_not_measurable_not_zero():
    res = _score(with_tpo=False)
    for key in ("day", "levels"):
        assert res["axes"][key]["n"] is None, key
        assert res["axes"][key]["pct"] is None and res["axes"][key]["ok"] is None
        assert "v9_tpo_history" in res["axes"][key]["not_measurable"]


def test_missing_ledger_is_not_measurable_not_zero():
    res = _score(with_ledger=False)
    for key in ("candidates", "decisions"):
        assert res["axes"][key]["n"] is None, key
        assert res["axes"][key]["ok"] is None
        assert "ליגר" in res["axes"][key]["not_measurable"]
    # המונה החלקי נשמר לצד ההודעה — שקוף, ולא מתחזה לציון
    assert res["axes"]["decisions"]["partial_n"] == 0


def test_zero_opportunity_events_is_not_a_zero_score():
    """יום בלי נגיעות-VA אינו 0% מודעות — הוא יום בלי מה למדוד."""
    cand = _score(touch_idx=(), detected_bars=())["axes"]["candidates"]
    assert cand["n"] is None and cand["pct"] is None
    assert "אפס אירועי-הזדמנות" in cand["not_measurable"]


def test_row_without_any_timestamp_blocks_the_axis_with_t420():
    """שורה בלי אף שדה-זמן ⇒ הציר NOT-MEASURABLE (T-420) + מונה חלקי.

    לא משלימים ts מ-trade_id/מסדר-השורות — זו מחלקת-השגיאה ש-Rule 1 אוסר.
    """
    orphan = [json.dumps({"event_type": "GATE_DECISION", "trade_id": "1916",
                          "system": 2, "outcome": "blocked"})]
    res = _score(touch_idx=(20,), detected_bars=(20,), extra_lines=orphan)
    dec = res["axes"]["decisions"]
    assert dec["n"] is None and "T-420" in dec["not_measurable"]
    assert dec["partial_n"] == 1 and dec["partial_d"] == 78
    c = res["ledger_census"]
    assert c["no_usable_ts"] == 1
    assert c["parsed"] + c["json_bad"] + c["no_usable_ts"] == c["lines"] == 2


def test_broken_json_is_counted_not_silently_dropped():
    _, census = parse_ledger_lines(['{"event_type": "DETECTED"', '', '{"ts": null}'])
    assert census["lines"] == 2 and census["json_bad"] == 1 and census["no_usable_ts"] == 1
    assert census["parsed"] == 0                                   # אף שורה לא הניבה אירוע
    assert census["parsed"] + census["json_bad"] + census["no_usable_ts"] == census["lines"]


# ── 3 · מודעות-T-100 ─────────────────────────────────────────────────────────

def test_t100_skew_is_measured_and_corrected():
    """ts מוסט ‎−3ש' חוזר לרגע-האמת, וההסטה מדווחת."""
    snaps = normalize_tpo(_raw_tpo(3, carry_over=False))
    assert {s.skew_h for s in snaps} == {3}
    assert snaps[0].ts == datetime.combine(DAY, time(9, 30), tzinfo=ET)
    clean = normalize_tpo(_raw_tpo(0, carry_over=False))
    assert {s.skew_h for s in clean} == {0}
    assert [s.ts for s in clean] == [s.ts for s in snaps]


def test_shifted_day_and_clean_day_score_identically():
    """יום נגוע-T-100 (≤28.08) ויום נקי (≥31.08) ⇒ אותו ציון בדיוק.

    זה הטסט שמפיל "תמיד להוסיף 3 שעות": תיקון עיוור היה מזיז את הצילומים
    של היום-הנקי ב-3ש' קדימה ושובר גם את ציר-היום וגם את ציר-הרמות.
    """
    shifted, clean = _score(skew_hours=3), _score(skew_hours=0)
    for key in ("day", "levels", "candidates", "decisions"):
        assert shifted["axes"][key]["n"] == clean["axes"][key]["n"], key
        assert shifted["axes"][key]["d"] == clean["axes"][key]["d"], key
    assert shifted["tpo_skew_hours"] == [3] and clean["tpo_skew_hours"] == [0]
