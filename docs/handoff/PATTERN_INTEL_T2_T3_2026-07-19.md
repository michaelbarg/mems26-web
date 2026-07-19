# PATTERN INTEL — T2 matrix + T3 geometry · 2026-07-19

**מבצע: cursor-agent** · מאמת: cowork (חוק-5).

## T2 · מטריצת 15×8 מול DIRECTION_AUTHORITY_MAP

### ראיה
```
$ python3 scripts/sim_matrix.py
PASS: 112 cells, keep=65 skip=47, counter-trend 9/9, mismatches=0
```
`sim_matrix` בודק playbook↔gateway בלבד — **לא** את מפת-D0. ההצלבה למטה ידנית.

### מטריצה (E=FULL R=REDUCED S=SKIP · 🟢 תואם-D0 · 🔴 סתירה · 🟡 תנאי-D0 שחסר ב-playbook)

| Pattern | TN | DD | Var | Nor | NC | NE | NT | NCv |
|---|---|---|---|---|---|---|---|---|
| ZLR CONT | E🟢 | E🟢 | E🟢 | R🟡 | S🟢 | S🟢 | S🟢 | S🟢 |
| TLB CONT | E🟢 | E🟢 | E🟢 | R🟡 | S🟢 | **R🔴** | S🟢 | S🟢 |
| TT CONT | R🟢 | R🟢 | R🟢 | R🟡 | S🟢 | S🟢 | S🟢 | S🟢 |
| GB100 CONT | R🟢 | R🟢 | R🟢 | R🟡 | S🟢 | S🟢 | S🟢 | S🟢 |
| INITIATIVE CONT | E🟢 | E🟢 | E🟢 | R🟡 | S🟢 | S🟢 | S🟢 | S🟢 |
| FLAGS CONT | E🟢 | E🟢 | E🟢 | R🟡 | S🟢 | **R🔴** | S🟢 | S🟢 |
| CONFLUENCE CONT | E🟢 | E🟢 | E🟢 | E🟡 | S🟢 | S🟢 | S🟢 | S🟢 |
| HTLB REV | **E🔴** | **E🔴** | E🟢 | R🟢 | R🟢 | R🟢 | S🟢 | S🟢 |
| VEGAS REV | S🟢 | S🟢 | R🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| GHOST REV | S🟢 | S🟢 | R🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| FAMIR REV | S🟢 | S🟢 | R🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| DBDT REV | S🟢 | **R🔴** | R🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| REACTIVE REV | E🟡 | E🟡 | E🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| HNS REV | R🟡 | R🟡 | E🟢 | E🟢 | E🟢 | E🟢 | S🟢 | S🟢 |
| HFE | disabled | | | | | | | |

### 🔴 עם file:line
1. HTLB×Trend FULL — `config/daytype_playbook.yaml:143` vs D0 REV❌ · `_REV_PATTERNS` `daytype_position_gate.py:47` · PATTERN_AWARE חוסם `:110-111`
2. DBDT×Trend_DD REDUCED — `daytype_playbook.yaml:148`
3. TLB×Neutral_Extreme REDUCED — `yaml:130` vs D0 CONT❌ · `:108-109`
4. FLAGS×Neutral_Extreme REDUCED — `yaml:140`

### 🟡
כל CONT×Normal = playbook בלי POC/mig (פער-D1). CONFLUENCE×Normal=FULL חזק יותר.

---

## T3 · Bible מול דטקטורים

| # | תבנית | פסיקה | סטייה |
|---|---|---|---|
| 1–10,12–14 | ZLR…FLAGS | ✅ | — |
| 11 | INITIATIVE | ⚠️ | Bible אומר 1.3–2.5×**ATR**; קוד = avg-range 14 (`five_min_system.py:44-46`) או קבוע 1.5–1.75pt (`:31-32`) כש-`S2_ATR_RELATIVE` OFF |
| 9 | HFE | ✅ disabled | — |

**רשימת-סטיות:** INITIATIVE baseline בלבד (`five_min_system.py:31-32,44-46`).
