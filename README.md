
# MEMS26 AI Trader — Web System v3.0
### ZeroMQ + FastAPI + Claude AI + Next.js + WebSocket

---

## ארכיטקטורה

```
┌──────────────────────────────────────────────────────────────┐
│  המחשב שלך (Windows)                                         │
│                                                              │
│  Sierra Chart (גרף MEMS26)                                   │
│    └─ MES_ZMQ_Publisher.cpp  ─── ZMQ PUSH :5555             │
│                                       ↓                      │
│  zmq_bridge.py  ──── Feature Engineering                     │
│    └─ IB calc, Rev 15/22, CVD, Effort                        │
│    └─ POST to cloud every 1 second                           │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Render (ענן — FastAPI)                                       │
│                                                              │
│  POST /ingest  ← Bridge                                      │
│    └─ Claude AI → Score 1-10 + Signal                        │
│    └─ WebSocket broadcast → Dashboard                        │
│                                                              │
│  GET /ws  → React Dashboard                                  │
│  GET /health, /signals/latest, /signals/history              │
└──────────────────────────────┬───────────────────────────────┘
                               │ WebSocket
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Vercel (ענן — Next.js)                                       │
│                                                              │
│  Dashboard — גישה מכל מקום בעולם                             │
│  • גרף נרות + כל הרמות                                       │
│  • רמזור + ציון 1-10                                         │
│  • Signal Card עם Entry/SL/T1/T2/T3                          │
│  • CVD Panel + Reversal Status                               │
└──────────────────────────────────────────────────────────────┘
```

---

## התקנה שלב-אחר-שלב

### שלב 1 — Sierra Chart: ZMQ Publisher Study

**1.1 הורד libzmq עבור Windows:**
```
https://github.com/zeromq/libzmq/releases
→ הורד: libzmq-v143-mt-4_3_5.zip
→ חלץ libzmq.dll ל: C:\Windows\System32\
→ חלץ zmq.h ל: C:\SierraChart\ACS_Source\include\zmq.h
→ חלץ libzmq.lib ל: C:\SierraChart\ACS_Source\lib\libzmq.lib
```

**1.2 הוסף Linker Settings ב-Sierra Chart:**
```
Tools → Sierra Chart Settings → Custom Studies Build Settings
Additional Link Libraries: C:\SierraChart\ACS_Source\lib\libzmq.lib
```

**1.3 העתק וBuild:**
```
העתק: sc_study/MES_ZMQ_Publisher.cpp → C:\SierraChart\ACS_Source\
Analysis → Build Custom Studies DLL
```

**1.4 הוסף לגרף MEMS26:**
```
Analysis → Add/Manage Studies → MES ZMQ Publisher
Inputs:
  ZeroMQ Port: 5555
  Export on Bar Close Only: No (= כל tick)
  Live Tick Interval: 1 (שניה)
```

**✅ בדיקה:** פתח CMD ← `netstat -an | findstr 5555` ← צריך לראות LISTENING

---

### שלב 2 — Python Bridge (מקומי)

**2.1 התקן תלויות:**
```bash
cd mems26_web/bridge
pip install -r requirements.txt
```

**2.2 הגדר .env:**
```bash
copy .env.example .env
```
ערוך `.env`:
```
ZMQ_PORT=5555
CLOUD_URL=https://mems26-api.onrender.com    ← תעדכן אחרי שלב 3
BRIDGE_TOKEN=בחר-סיסמה-חזקה-כאן
```

**2.3 בדיקה מקומית (לפני Render):**
```bash
python zmq_bridge.py
```
צפוי:
```
[16:35:10] ZMQ PULL connected to localhost:5555
[16:35:12] → Cloud | AM_SESSION | 6521.50 | CVD:BULLISH | Effort:NORMAL | Rev15:NONE | Rev22:NONE
```

**✅ בדיקה:** רואים נתונים מתעדכנים בטרמינל כל שניה

---

### שלב 3 — FastAPI Backend על Render

**3.1 צור חשבון ב-Render:**
```
https://render.com → Sign up (חינמי)
```

**3.2 Render Blueprint (הכי פשוט):**
```bash
# Push the project to GitHub first
git init && git add . && git commit -m "initial"
git remote add origin https://github.com/YOUR_USER/mems26-web
git push -u origin main
```
ב-Render: New → Blueprint → בחר את ה-repo → Render יקרא את render.yaml אוטומטית

**3.3 הגדר Environment Variables ב-Render Dashboard:**
```
ANTHROPIC_API_KEY = sk-ant-...
BRIDGE_TOKEN      = אותה סיסמה שב-.env של Bridge
MAX_TRADES_DAY    = 3
MIN_CONFIDENCE    = HIGH
```

**3.4 עדכן CLOUD_URL ב-Bridge .env:**
```
CLOUD_URL=https://YOUR-APP-NAME.onrender.com
```
הפעל מחדש את Bridge.

**✅ בדיקה:**
```bash
curl https://YOUR-APP-NAME.onrender.com/health
# → {"status":"ok","clients":0,"last_price":6521.50}
```

---

### שלב 4 — React Dashboard על Vercel

**4.1 צור חשבון ב-Vercel:**
```
https://vercel.com → Sign up עם GitHub (חינמי)
```

**4.2 Deploy:**
```
Vercel Dashboard → New Project → Import mems26-web → Root: frontend
```

**4.3 הגדר Environment Variable ב-Vercel:**
```
NEXT_PUBLIC_API_WS_URL = wss://YOUR-APP-NAME.onrender.com/ws
```

**4.4 Deploy:**
```
Vercel → Deploy
```

**✅ בדיקה:**
פתח את URL שVercel נותן → צריך לראות Dashboard עם:
- רמזור כתום (WAIT)
- גרף (ריק עד שBridge מחובר)
- ● LIVE בפינה הימנית עליונה

---

### שלב 5 — חיבור סופי End-to-End

```bash
# טרמינל 1 — Bridge
cd mems26_web/bridge
python zmq_bridge.py

# Sierra Chart — גרף MEMS26 פתוח עם Study פעיל
```

פתח את ה-Dashboard ב-Vercel URL מהטלפון/מחשב אחר.
תוך 5-10 שניות הגרף יתחיל להתמלא.

---

## פקודות שימושיות

```bash
# בדיקת Bridge מקומית
python zmq_bridge.py

# בדיקת API endpoints
curl https://YOUR-APP.onrender.com/health
curl https://YOUR-APP.onrender.com/signals/latest
curl https://YOUR-APP.onrender.com/signals/history

# פיתוח Frontend מקומי
cd frontend
npm install
npm run dev
# פתח: http://localhost:3000
```

---

## מבנה קבצים

```
mems26_web/
├── render.yaml                    ← Render deployment config
│
├── sc_study/
│   └── MES_ZMQ_Publisher.cpp     ← Sierra Chart ZMQ Study
│
├── bridge/
│   ├── zmq_bridge.py             ← Python local bridge
│   ├── requirements.txt
│   └── .env.example
│
├── backend/
│   ├── main.py                   ← FastAPI server (Render)
│   ├── requirements.txt
│   └── engine/
│       ├── signal_engine.py      ← Claude AI analysis
│       └── models.py             ← Data models
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── vercel.json
    └── src/
        ├── app/
        │   ├── page.tsx           ← Main dashboard page
        │   ├── layout.tsx
        │   └── globals.css
        └── components/
            ├── TradingChart.tsx   ← Canvas chart + levels
            ├── TrafficLight.tsx   ← Traffic light widget
            ├── SignalCard.tsx     ← TP/SL ladder
            ├── CVDPanel.tsx       ← CVD display
            ├── DailyTracker.tsx   ← Trades tracker
            ├── LevelsBadges.tsx   ← Key levels badges
            └── ReversalStatus.tsx ← Rev 15/22 status
```

---

## זרימת נתונים מפורטת

```
1. Sierra Chart → ZMQ PUSH (every 1 second)
   Payload: O,H,L,C,V, BidVol, AskVol, Delta, Woodi, 72H, IB

2. zmq_bridge.py → Feature Engineering
   + IB High/Low (first 60 min)
   + Rev 15/22 detection (Failed Breakout / Rejection)
   + Effort vs Result (Wyckoff)
   + CVD trend (20-bar slope)
   + POC approximation

3. Bridge → POST /ingest (every 1 second)
   Enriched payload with all features

4. FastAPI → Claude AI
   Full market state prompt → Score 1-10 + Entry/SL/TP

5. FastAPI → WebSocket broadcast
   All connected clients receive update in real-time

6. React Dashboard
   Chart updates, TrafficLight changes, SignalCard appears
```

---

## עלויות

| שירות | תוכנית | עלות |
|-------|--------|------|
| Render (API) | Free tier | $0/month (עם sleep בין requests) |
| Render (API) | Starter | $7/month (ללא sleep) |
| Vercel (Dashboard) | Hobby | $0/month |
| Anthropic API | Pay per use | ~$0.01 per signal |

**המלצה:** תתחיל עם Free tier. אם ה-sleep מפריע (Render free tier נרדם אחרי 15 דק), שדרג ל-Starter ($7/month).

---

## פתרון בעיות

| בעיה | פתרון |
|------|-------|
| ZMQ: Address already in use | פקודה אחת כבר מחזיקה את port 5555 — סגור Sierra Chart Study |
| Bridge: Connection refused | Sierra Chart לא מריץ את ה-Study |
| Render: 503 | Free tier ישן — שלח request ראשון, המתן 30 שניות |
| Dashboard: ○ RECONNECTING | CLOUD_URL ב-.env שגוי, או Render לא רץ |
| No signals | תקין! NO_TRADE = אין קונפלואנס מספיק. המתן לסשן |
| Claude API error | בדוק ANTHROPIC_API_KEY ב-Render |
