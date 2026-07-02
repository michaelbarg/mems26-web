# -*- coding: utf-8 -*-
OUT="/sessions/epic-jolly-sagan/mnt/mems26_web_git/docs/spec_authority/PATTERN_VISUAL_BY_DAYTYPE_2026-07-02.html"
P=[]
def pat(pid,heb,fam,sys,bars,entry_i,entry_txt,stops,targets,cells,note="",cci=None,cci_marks=None):
    P.append(dict(pid=pid,heb=heb,fam=fam,sys=sys,bars=bars,ei=entry_i,et=entry_txt,stops=stops,tg=targets,cells=cells,note=note,cci=cci,cci_marks=cci_marks or []))
F="FULL";Fs="FULL*";R="REDUCED";S="SKIP"
pat("REACTIVE","היפוך 4-ברים","REV","S2",
 [(52,50,54,48,1,""),(50,49,52,47,1,""),(49,42,50,40,3,"b1 מוכרים"),(42,41,43,38,0,"b2 ווליום↓"),(41,46,47,39,2,"b3 קונים"),(46,51,52,45,2,"b4 אישור")],
 5,"סגירת b4 מעל שיא-b3 + CVD absorption (חי) · ווליום-b4 יתווסף (S2_B4_VOL_V1)",
 [("מ1 · שפל-b3",39),("מ2 · שפל-b2 (שפל-ההיפוך)",38),("מ3 · אזור-w4",37)],
 "C1 swing · C2 POC · C3 קצה-ערך-נגדי",
 [Fs,Fs,F,Fs,F,F,S],"עם-הכיוון בלבד בימי-מגמה ובווריאציה (פסק 07-02)")
pat("INITIATIVE","פריצת-קבלה","CONT","S2",
 [(44,45,46,43,1,""),(45,52,53,44,3,"b1 התפשטות"),(52,50,53,49,0,"b2 בדיקה"),(50,55,56,49,2,"b3 הצטרפות"),(55,58,59,54,2,"b4 אישור")],
 4,"סגירת b4 מעל שיא-b1 + CVD עם-הזרם",
 [("מ1 · שפל-בר-הפריצה",44),("מ2 · שפל-b2",49),("מ3 · הרמה-השבורה −3T",46)],
 "C1 swing · C2 מבנה-קרוב/IB-ext · C3 רנר",
 [F,F,S,F,S,S,S],"Normal=SKIP (פסק 07-02) · ראיה 07-02: 4 סטופים-מוקדמים (MAE עבר סטופ ב-≤2 נק' ואז MFE 27-52 לכיוון, −$267) ⇒ מדרגת-מ2 (שפל-b2) היא המתוקה")
pat("BULL_FLAG","מוט+דגל","CONT","S2",
 [(40,47,48,39,3,"מוט"),(47,54,55,46,3,"מוט"),(54,52,55,51,1,"דגל"),(52,50,53,49,0,"מתייבש"),(50,49,51,47,0,"הנמוך-בצובר"),(49,56,57,48,2,"פריצה")],
 5,"פריצת ראש-הדגל בסגירה",
 [("מ1 · שפל-בר-הפריצה",48),("מ2 · הבר-הנמוך בחלק-הצובר",47)],
 "C1 swing · C2 מבנה-קרוב · C3 VA/extension",
 [F,F,R,F,S,R,S],"✅ נפסק 07-02 (D-10): אימות ווליום+פריצה + סולם דו-מדרגתי סופי · סטופ-התחלתי אמיתי (מ-mgmt-log): 10.5 נק' חציוני")
pat("BEAR_FLAG","מוט+דגל (מראה)","CONT","S2",
 [(60,53,61,52,3,"מוט↓"),(53,46,54,45,3,"מוט↓"),(46,48,49,45,1,"דגל↑"),(48,50,51,47,0,"מתייבש"),(50,51,52,49,0,"הגבוה-בצובר"),(51,44,52,43,2,"שבירה")],
 5,"שבירת בסיס-הדגל בסגירה",
 [("מ1 · שיא-בר-השבירה",52),("מ2 · הבר-הגבוה בחלק-הצובר",52)],
 "כמו BULL_FLAG, מטה",[F,F,R,F,S,R,S],"")
pat("ZLR","דחיית קו-האפס","CONT","S4",
 [(42,48,49,41,2,"מגמה↑"),(48,53,54,47,2,""),(53,51,54,50,1,"פולבק→0"),(51,50,52,48,0,"ווליום↓"),(50,55,56,49,2,"דחייה")],
 4,"סגירה מעל בנר-הדחייה (V2: Stage-1 6-בר + SWI + CZI)",
 [("מ1 · שפל-בר-הדחייה (breakout_bar w1)",48)],
 "Trend: swing→IB-center→trail · Normal/Var: swing→POC→VAH",
 [F,F,R,F,S,S,S],"עוגן עודכן 06-30 — מסמכים ישנים עוד אומרים cluster_low",cci=[155,175,60,15,95],cci_marks=[("Stage-1: מגמה מעל +100",0),("פולבק לאזור-האפס (בלי לחצות −100)",3),("דחייה=ZLR",4)])
pat("TLB","שבירת קו-מגמה","CONT","S4",
 [(55,50,56,49,2,"פולבק"),(50,47,51,46,1,"קו-מגמה"),(47,45,48,44,0,"דועך"),(45,44,46,43,0,""),(44,50,51,43,2,"שבירה")],
 4,"שבירת קו-הפולבק על ה-CCI (V2: ±200 תוך 12 ברים + פרטנר CONT)",
 [("מ1 · שפל-הפולבק (w8)",43)],
 "כמו ZLR",[F,F,R,F,S,R,S],"שער-V2 חסר בכרטיס · Stage-2 לא נבנה",cci=[210,150,110,80,140],cci_marks=[("קיצון +200 (תנאי-V2)",0),("קו-מגמה יורד על פסגות-ה-CCI",2),("שבירת-הקו=כניסה",4)])
pat("TT","טוני'ס טרייד","CONT","S4",
 [(44,50,51,43,2,"שלב-1 מגמה↑"),(50,53,54,49,2,""),(53,51,54,50,1,"עצירה"),(51,50,52,49,0,"3-9 ברים"),(50,55,56,49,2,"חצייה-כפולה=כניסה")],
 4,"ספק-המקור (פריט-12): שלב-1 כמו-ZLR (6-בר מעל אפס · +100 · SWI · EMA-34) → עצירה 3-9 ברים מתחת לאפס (לא −100; לא −50=חזק) → CCI-14+TCCI סוגרים מעל האפס + מחיר מעל EMA-34",
 [("מ1 · שפל-הדחיסה (w9)",51)],
 "כמו ZLR",[F,F,R,R,S,S,S],"✅ נפסק 07-02: נתקן (TT_SPEC_V2, פריט-12) — הקוד זיהה תבנית אחרת (נשיקת-TCCI) + דרש trend בבר-הכניסה בניגוד למקור ⇒ 0 ירי · TN/TDD→FULL",cci=[130,90,-30,-60,40],cci_marks=[("שלב-1: מעל אפס, נגע +100",0),("שלב-2: עצירה מתחת לאפס (רצפה −100)",3),("שלב-3: חצייה-כפולה מעלה=כניסה",4)])
pat("GB100","חזרה ל-100","CONT","S4",
 [(42,48,49,41,2,"מגמה↑"),(48,52,53,47,2,""),(52,49,53,48,1,"חזרה ל-+100"),(49,47,50,46,0,"דועך"),(47,52,53,46,2,"באונס")],
 4,"היפוך מאזור ה-+100 של ה-CCI להמשך",
 [("מ1 · שפל-הפולבק (cluster_low w6)",46)],
 "כמו ZLR",[F,F,R,R,S,S,S],"TN/TDD→FULL (פסק 07-02)",cci=[190,160,115,100,150],cci_marks=[("מגמה מעל +100",0),("חזרה לאזור ה-+100 (תמיכה)",3),("באונס=כניסה",4)])
pat("VEGAS","היפוך-קיצון · cup&handle (לונג מהקיצון)","REV","S4",
 [(56,50,57,49,3,"מפולת"),(50,46,51,44,3,"קיצון"),(46,49,50,45,2,"התאוששות"),(49,48,50,47,1,"handle רדוד"),(48,53,54,47,2,"שבירת-rim")],
 4,"V2 בקוד: קאפ מתחת −200 → התאוששות חוצה −100 (rim) → handle רדוד (≥3 ברים, ריטרייס<50%) → כניסה בשבירת-ה-rim",
 [("מ1 · קצה-נר-ההיפוך",44),("מ2 · שפל-ה-handle",46),("מ3 · קצה-הקאפ",43)],
 "REV: C1 swing (capped) · C2 POC · C3 קצה-נגדי",
 [S,S,F,R,F,F,S],"✅ נפסק 07-02 (D-11): הקוד צודק — ספל-וידית; הכרטיס יתוקן · יישור: ידית 2→3 ברים, שער-50% נשאר",
 cci=[-140,-230,-90,-120,-60],cci_marks=[("קאפ < −200",1),("rim: חציית −100",2),("handle רדוד",3),("שבירת-rim=כניסה",4)])
pat("GHOST","ראש-וכתפיים על ה-CCI (שורט)","REV","S4",
 [(50,53,54,49,2,"כתף-שמאל"),(53,56,58,52,2,"ראש"),(56,54,57,53,1,""),(54,55,56,53,1,"כתף-ימין"),(55,50,56,49,2,"שבירת-neckline")],
 4,"בקוד: שלוש פסגות-CCI (הראש הגבוה) + שבירת ה-neckline של ה-CCI · הכרטיס הישן תיאר failed-high במחיר",
 [("מ1 · קצה-נר-הכישלון",63),("מ2 · הכתף",64)],
 "REV: כמו VEGAS",[S,S,F,R,F,F,S],"✅ נפסק 07-02 (D-12): CCI-H&S עם קו-בחינה מכריע · יישור-קוד ב-GHOST_SPEC_V2 · סולם: בר-כניסה → כתף-ימין → הראש",cci=[120,185,95,125,40],cci_marks=[("כתף",0),("ראש",1),("כתף-ימין נמוך מהראש",3),("שבירת-neckline=כניסה",4)])
pat("FAMIR","המשך-שנכשל (שורט)","REV","S4",
 [(48,52,53,47,2,"ניסיון↑"),(52,54,56,51,1,"ווליום חלש"),(54,49,55,48,2,"flip")],
 2,"ZLR שנכשל בדרך ל-±200 → היפוך נגדי (flip)",
 [("מ1 · שיא-בר-הכישלון (failed_bar)",56)],
 "REV: C1 swing · C2 POC · C3 קצה-נגדי",[S,S,F,R,F,F,S],"✅ נפסק 07-02 (D-13): ZLR-שנכשל מייד אחרי שלב-3 — ייושר ב-FAMIR_SPEC_V2 · סולם בהליכה",cci=[95,150,45],cci_marks=[("ZLR מנסה",0),("נכשל לפני +200",1),("flip=כניסה",2)])
pat("HTLB","הוק+שבירת-קו-אופקי (שורט)","REV","S4",
 [(50,52,54,49,1,"הוק"),(52,53,55,51,1,"קו אופקי"),(53,47,54,46,2,"שבירה")],
 2,"קו אופקי על הוקי-ה-CCI באזור [+100,+200] נשבר מטה · גם מתווה-כיוון לכל ה-woodies",
 [("מ1 · consolidation_extreme",55),("❓ מקור: בר-הפריצה — פתוח מ-06-26",56)],
 "REV: C1 swing (capped 14) · C2 POC · C3 VAL",
 [Fs,Fs,R,F,R,R,S],"עם-המגמה בלבד בימי-מגמה (פסק 07-02)",cci=[150,145,60],cci_marks=[("הוקים באזור +100..+200",0),("קו אופקי (≥2 נגיעות)",1),("שבירה=כניסה",2)])
pat("DOUBLE_TOP_AA","שתי פסגות (שורט)","REV","S2",
 [(48,54,55,47,2,"עלייה"),(54,57,59,53,2,"פסגה-1"),(57,52,58,51,1,"neckline"),(52,56,59,51,1,"פסגה-2 ווליום↓"),(56,49,57,48,2,"שבירה")],
 4,"סגירה מתחת ל-neckline · דיברגנס בפסגה-2",
 [("מ1 · שיא-בר-השבירה",57),("מ2 · הפסגות",59)],
 "היפוך: swing→POC→קצה — לא measured-move (נתן −112)",
 [S,S,F,R,F,F,S],"TDD=SKIP (פסק 07-02)")
pat("DOUBLE_BOTTOM_EE","שני שפלים (לונג)","REV","S2",
 [(56,50,57,49,2,"ירידה"),(50,47,51,45,2,"שפל-1"),(47,52,53,46,1,"neckline"),(52,48,53,45,1,"שפל-2 ווליום↓"),(48,55,56,47,2,"שבירה")],
 4,"סגירה מעל ה-neckline · absorption",
 [("מ1 · שפל-בר-השבירה",47),("מ2 · השפלים",45)],
 "כמו DOUBLE_TOP, מעלה",[S,S,F,R,F,F,S],"")
pat("INVERSE_HNS","ראש-וכתפיים הפוך (לונג)","REV","S2",
 [(56,51,57,50,2,"כתף-שמאל"),(51,46,52,44,2,"ראש"),(46,50,51,45,1,""),(50,48,51,46,0,"כתף-ימין ווליום↓"),(48,54,55,47,2,"שבירה")],
 4,"שבירת neckline מעלה בווליום עולה",
 [("מ1 · שפל-בר-השבירה",47),("מ2 · כתף-ימין (לא הראש)",46)],
 "היפוך: swing→POC→קצה",[S,S,F,Fs,F,F,S],"Variation=עם-הכיוון (פסק 07-02)")
pat("HNS_TOP","ראש-וכתפיים (שורט)","REV","S2",
 [(46,51,52,45,2,"כתף-שמאל"),(51,56,58,50,2,"ראש"),(56,52,57,51,1,""),(52,54,56,51,0,"כתף-ימין ווליום↓"),(54,48,55,47,2,"שבירה")],
 4,"שבירת neckline מטה",
 [("מ1 · שיא-בר-השבירה",55),("מ2 · כתף-ימין",56)],
 "כמו INVERSE_HNS, מטה",[S,S,F,Fs,F,F,S],"")
pat("PULLBACK_RETEST","פולבק-ריטסט (מוצע · פריט-8)","CONT","S2·מוצע",
 [(44,52,53,43,3,"פריצת הרמה"),(52,50,53,49,1,"פולבק"),(50,48,51,47,0,"נוגע ברמה · ווליום↓"),(48,54,55,47,2,"חידוש")],
 3,"בר-חידוש בכיוון-ההרחבה אחרי פולבק לרמה-השבורה (IB-edge/VA שהפכו S/R) — ספק-06-20; עדיין לא קיים בקוד",
 [("מ1 · קצה-בר-החידוש",47),("מ2 · קצה-הפולבק (מעבר לרמה)",46.5)],
 "CONT: C1 swing · C2 מבנה-קרוב · C3 קצה/extension",
 [F,F,S,F,S,S,S],"🔵 פריט-8 בחבילת-CC — מחקר+אפיון מול מיכאל לפני בנייה")
pat("HFE","הוק-מקיצון","REV","S4",
 [(50,54,55,49,2,""),(54,58,60,53,3,"קיצון ±200"),(58,53,60,52,2,"hook")],
 -1,"מושבת לצמיתות (HFE_DISABLED=1 · −$2,987)",
 [],"—",[S,S,S,S,S,S,S],"⚫ כבוי בכל השכבות",cci=[160,225,170],cci_marks=[("מעבר ל-+200",1),("hook",2)])

DT=["Trend_N","Trend_DD","Normal","Variation","Neu_C","Neu_E","Nontrend"]
def candles_svg(p):
    bars=p["bars"]; W=560; n=len(bars)
    has_cci=bool(p.get("cci")); H=280 if has_cci else 210
    ys=[v for b in bars for v in (b[2],b[3])]+[s[1] for s in p["stops"]]
    lo,hi=min(ys)-3,max(ys)+5
    def Y(v): return 20+(hi-v)/(hi-lo)*130
    bw=26; gap=(420-n*bw)/(n+1)
    out=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    for i,(o,c,h,l,vol,lab) in enumerate(bars):
        x=30+gap+i*(bw+gap)
        col="#3fb950" if c>=o else "#f85149"
        out.append(f'<line x1="{x+bw/2:.1f}" y1="{Y(h):.1f}" x2="{x+bw/2:.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.5"/>')
        top,bot=Y(max(o,c)),Y(min(o,c))
        out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw}" height="{max(bot-top,2):.1f}" fill="{col}" rx="1.5"/>')
        if vol: out.append(f'<rect x="{x+3:.1f}" y="{176-vol*7}" width="{bw-6}" height="{vol*7}" fill="#58a6ff" opacity="0.55"/>')
        if lab: out.append(f'<text x="{x+bw/2:.1f}" y="{Y(l)+11:.1f}" font-size="8.5" fill="#8b949e" text-anchor="middle">{lab}</text>')
        if i==p["ei"]:
            out.append(f'<path d="M {x+bw/2-7:.1f} {Y(h)-14:.1f} l 7 8 l 7 -8 z" fill="#e3b341"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{Y(h)-18:.1f}" font-size="9.5" fill="#e3b341" text-anchor="middle" font-weight="bold">כניסה</text>')
    for j,(lab,y) in enumerate(p["stops"]):
        yy=Y(y)+j*4
        out.append(f'<line x1="26" y1="{yy:.1f}" x2="450" y2="{yy:.1f}" stroke="#f85149" stroke-width="1" stroke-dasharray="5,4" opacity="{1-0.28*j:.2f}"/>')
        out.append(f'<text x="455" y="{yy+3:.1f}" font-size="8.5" fill="#f85149" opacity="{1-0.22*j:.2f}">{lab}</text>')
    if has_cci:
        cvals=p["cci"]; top,bot=200,262
        def CY(v): return top+(220-v)/440*(bot-top)
        for lv,lab in ((200,"+200"),(100,"+100"),(0,"0"),(-100,"−100"),(-200,"−200")):
            col="#6e7681" if lv else "#8b949e"
            out.append(f'<line x1="26" y1="{CY(lv):.1f}" x2="450" y2="{CY(lv):.1f}" stroke="{col}" stroke-width="0.7" stroke-dasharray="3,4"/>')
            out.append(f'<text x="455" y="{CY(lv)+3:.1f}" font-size="7.5" fill="{col}">{lab}</text>')
        pts=[]
        for i,v in enumerate(cvals):
            x=30+gap+i*(bw+gap)+bw/2; pts.append(f"{x:.1f},{CY(v):.1f}")
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#e3b341" stroke-width="2"/>')
        for lab,i in p["cci_marks"]:
            x=30+gap+i*(bw+gap)+bw/2
            out.append(f'<circle cx="{x:.1f}" cy="{CY(cvals[i]):.1f}" r="3" fill="#e3b341"/>')
            out.append(f'<text x="{x:.1f}" y="{CY(cvals[i])-6:.1f}" font-size="7.5" fill="#e6edf3" text-anchor="middle">{lab}</text>')
        out.append(f'<text x="30" y="{bot+14}" font-size="9" fill="#8b949e">🎯 {p["tg"]} · הפאנל התחתון = CCI (התבנית חיה שם)</text>')
    else:
        out.append(f'<text x="30" y="196" font-size="9" fill="#8b949e">🎯 {p["tg"]}</text>')
    out.append('</svg>'); return "".join(out)
def chips(cells):
    h=[]
    for d,v in zip(DT,cells):
        cls={"FULL":"cF","FULL*":"cF","REDUCED":"cR","SKIP":"cS"}[v]
        star="★" if v=="FULL*" else ""
        h.append(f'<span class="chip {cls}">{d}{star}</span>')
    return "".join(h)
cards=[]
for p in P:
    fam_c="#3fb950" if p["fam"]=="CONT" else "#d2a8ff"
    note=f'<div class="note">{p["note"]}</div>' if p["note"] else ""
    cards.append(f'<div class="card" id="{p["pid"]}"><div class="ch"><b>{p["pid"]}</b> <span class="heb">{p["heb"]}</span><span class="fam" style="color:{fam_c}">{p["fam"]}</span><span class="sys">{p["sys"]}</span></div>{candles_svg(p)}<div class="ent">▶ {p["et"]}</div><div class="chips">{chips(p["cells"])}</div>{note}</div>')
daytype_top='''<div class="dt-grid">
<div class="dtc"><b>Trend_Normal · תנועה</b><span>CONT: C1=swing · C2=IB-center/1×ext · C3=מחזיק-לסגירה (trail) · REV נגד: נחסם</span></div>
<div class="dtc"><b>Trend_DD</b><span>CONT: C1=swing · C2=POC-התפלגות-2 · C3=trail · REV נגד: נחסם</span></div>
<div class="dtc"><b>Variation</b><span>CONT: C1=swing/½ext · C2=1×ext · C3=2×ext/קצה · REV עם-הכיוון: C2=POC · C3=קצה</span></div>
<div class="dtc"><b>Normal · מיקום</b><span>C1=swing · C2=POC · C3=קצה-ערך-נגדי (רנר)</span></div>
<div class="dtc"><b>Neutral_Extreme</b><span>C1=swing/POC · C2=POC · C3=קצה-נגדי → הקצה-המנצח</span></div>
<div class="dtc"><b>Neutral_Center</b><span>C1=swing/POC · C2=POC · C3=קצה-IB · בלי רנר</span></div>
<div class="dtc"><b>Nontrend</b><span>אין מסחר (NONTREND_DISABLE_ALL)</span></div>
</div>'''
html=f'''<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MEMS26 · תבניות בגרפים — זיהוי, כניסה, סטופים ויעדים לפי סוג-יום · 2026-07-02</title>
<style>
:root{{--bg:#0d1117;--p:#161b22;--tx:#e6edf3;--mut:#8b949e;--bd:#30363d}}
body{{background:var(--bg);color:var(--tx);font-family:system-ui;margin:0;padding:18px;font-size:14px}}
h1{{font-size:19px;margin:0 0 4px}}.sub{{color:var(--mut);font-size:12px;margin-bottom:12px}}
.legend{{background:var(--p);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;font-size:12px;color:var(--mut);margin-bottom:12px;line-height:1.7}}
.dt-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:8px;margin-bottom:14px}}
.dtc{{background:var(--p);border:1px solid var(--bd);border-radius:8px;padding:8px 10px;font-size:12px}}
.dtc b{{display:block;color:#58a6ff;margin-bottom:3px}}.dtc span{{color:var(--mut);line-height:1.5}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(580px,1fr));gap:12px}}
.card{{background:var(--p);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}}
.ch{{display:flex;gap:10px;align-items:baseline;margin-bottom:4px}}.ch b{{font-size:15px}}
.heb{{color:var(--mut)}}.fam{{font-size:11px;font-weight:bold}}.sys{{font-size:11px;color:var(--mut);border:1px solid var(--bd);border-radius:8px;padding:0 7px}}
svg{{width:100%;height:auto;background:#0a0e14;border-radius:8px}}
.ent{{font-size:12px;color:#e3b341;margin:6px 0 4px}}
.chips{{display:flex;flex-wrap:wrap;gap:4px}}
.chip{{font-size:10.5px;border-radius:9px;padding:1px 8px;border:1px solid var(--bd)}}
.cF{{color:#3fb950;border-color:#3fb950}}.cR{{color:#d29922;border-color:#d29922}}.cS{{color:#6e7681;text-decoration:line-through}}
.note{{font-size:11.5px;color:#d29922;margin-top:5px}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>MEMS26 · 16 התבניות בגרפים — מבנה-הברים, הכניסה, מדרגות-הסטופ והיעדים לפי סוג-יום</h1>
<div class="sub">נוצר 2026-07-02 מאמת-הקוד + הכרטיסים + פסקי-היום (D-1..D-5 + חבילת-הכלכלה). משלים את PATTERN_PLAYBOOK_CANDLES.html. · עודכן ~15:50: ראיית-INITIATIVE + כרטיס פולבק-ריטסט (פריט-8) + פריטי 6-7 (אישור-CVD+ווליום ל-S4 · חלון-דינמי) בחבילת-CC.</div>
<div class="legend">▲ צהוב = בר-הכניסה (תמיד בסגירת-בר, פסק D-5) · קווים אדומים מקווקוים = מדרגות-הסטופ מהקרובה לרחוקה (בוחרים את הראשונה בתוך רצועת 0.5–1.2/1.5×ATR; תמיד ±3 טיקים מעבר למבנה אמיתי) · עמודות כחולות = ווליום · צ'יפים = הרשאה לפי סוג-יום (★ = עם-הכיוון בלבד · קו-חוצה = SKIP) · 🎯 = סולם C1/C2/C3 · הכל בנקודות (1 נק' = 4 טיקים = $5)</div>
{daytype_top}
<div class="grid">{"".join(cards)}</div>
</body></html>'''
open(OUT,"w",encoding="utf-8").write(html)
print("written",OUT,len(html),"chars ·",len(P),"patterns")
