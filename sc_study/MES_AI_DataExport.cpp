// MES_AI_DataExport.cpp — v9.4.2-p30.11 (G1/G2/G4: proj H/L, TPO validation, va_ok)
// Sierra Chart ACSIL Study — 3 minute chart + V9 tick reversal + footprint exports
// REAL-TIME: exports every N seconds (ExportIntervalSec), NO "last bar only" guard.
// מייצא: MTF, CVD, VWAP, Imbalance, Market Profile, Woodi, Levels
//         + V9: Tick Reversal (15/12), Footprint, Volume Profile,
//               Imbalance Flags, Stacked Imbalances, Cumulative Delta

#include "sierrachart.h"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <map>
#include <vector>
#include <algorithm>
#include "v9_types.h"
#include "v9_exports.h"
#include "v9_woodies_export.h"

SCDLLName("MES_AI_DataExport")

SCSFExport scsf_MES_AI_DataExport(SCStudyInterfaceRef sc)
{
    SCSubgraphRef CVD  = sc.Subgraph[0];
    SCSubgraphRef VWAP = sc.Subgraph[1];

    SCInputRef ExportPath        = sc.Input[0];
    SCInputRef ExportIntervalSec = sc.Input[1];
    SCInputRef VAPercent         = sc.Input[2];
    SCInputRef ImbalanceRatio    = sc.Input[3];
    SCInputRef V9ExportPath      = sc.Input[4];
    SCInputRef V9TickRev15       = sc.Input[5];
    SCInputRef V9TickRev12       = sc.Input[6];
    SCInputRef V9Lookback        = sc.Input[7];
    SCInputRef V9WoodiesHistory  = sc.Input[8];
    SCInputRef LivePriceEnabled  = sc.Input[9];
    SCInputRef LivePriceIntervalMs = sc.Input[10];
    SCInputRef TradeCommandPath  = sc.Input[11];
    SCInputRef TradeResultPath   = sc.Input[12];
    SCInputRef TPOYesterdayStudyID = sc.Input[13];  // Sierra Study ID:1 (TPO VA Lines, ref=1)
    SCInputRef TPOTodayStudyID     = sc.Input[14];  // Sierra Study ID:3 (TPO VA Lines, ref=0, developing)
    SCInputRef IBStudyID           = sc.Input[15];   // Sierra Study ID:6 (Initial Balance)
    SCInputRef ProjHLStudyID       = sc.Input[16];   // Sierra Study ID for Daily Projected High-Low
    SCInputRef TPOChartNumber      = sc.Input[17];   // Chart # where TPO studies live (0 = same chart)
    SCInputRef WoodiesChartNumber  = sc.Input[18];   // Chart # where Woodies studies live (0 = same chart)
    SCInputRef YesterdayIBStudyID  = sc.Input[19];   // Sierra Study ID for Yesterday's Initial Balance (0 = disabled)
    SCInputRef ContinuousChartNumber = sc.Input[20]; // Chart # for 24h continuous 5-min bars (0 = disabled)

    if (sc.SetDefaults)
    {
        sc.GraphName        = "MES AI Data Export v9.4.3-chart5";
        sc.StudyDescription = "V9.1 REAL-TIME: MTF + VWAP + Footprint + Tick Reversal + Imbalance + Market Profile";
        sc.AutoLoop         = 1;
        sc.GraphRegion      = 1;

        CVD.Name         = "CVD";
        CVD.DrawStyle    = DRAWSTYLE_LINE;
        CVD.PrimaryColor = COLOR_CYAN;

        VWAP.Name         = "VWAP";
        VWAP.DrawStyle    = DRAWSTYLE_LINE;
        VWAP.PrimaryColor = COLOR_YELLOW;

        ExportPath.Name = "Export JSON Path";
        ExportPath.SetString("/Users/michael/SierraChart_Data/v9_export/mes_ai_data.json");

        ExportIntervalSec.Name = "Export Interval (seconds)";
        ExportIntervalSec.SetInt(3);

        VAPercent.Name = "Value Area %";
        VAPercent.SetFloat(70.0f);

        ImbalanceRatio.Name = "Imbalance Ratio (e.g. 3.0 = 3:1)";
        ImbalanceRatio.SetFloat(3.0f);

        V9ExportPath.Name = "V9 Export Directory";
        V9ExportPath.SetString("/Users/michael/SierraChart_Data/v9_export/");

        V9TickRev15.Name = "V9 Tick Reversal 15-tick (1=on)";
        V9TickRev15.SetInt(1);

        V9TickRev12.Name = "V9 Tick Reversal 12-tick (1=on)";
        V9TickRev12.SetInt(1);

        V9Lookback.Name = "V9 Lookback Bars";
        V9Lookback.SetInt(200);

        V9WoodiesHistory.Name = "V9 Woodies 30min History Bars";
        V9WoodiesHistory.SetInt(50);

        LivePriceEnabled.Name = "Live Price Export (1=on)";
        LivePriceEnabled.SetInt(1);

        LivePriceIntervalMs.Name = "Live Price Interval (ms)";
        LivePriceIntervalMs.SetInt(200);

        TradeCommandPath.Name = "Trade Command JSON Path";
        TradeCommandPath.SetString("/Users/michael/SierraChart_Data/v9_export/trade_command.json");

        TradeResultPath.Name = "Trade Result JSON Path";
        TradeResultPath.SetString("/Users/michael/SierraChart_Data/v9_export/trade_result.json");

        TPOYesterdayStudyID.Name = "TPO Yesterday Study ID (Sierra)";
        TPOYesterdayStudyID.SetInt(1);  // Study ID:1 — TPO Value Area Lines, ref=1

        TPOTodayStudyID.Name = "TPO Today Study ID (Sierra)";
        TPOTodayStudyID.SetInt(3);  // Study ID:3 — TPO Value Area Lines, ref=0, developing

        IBStudyID.Name = "Initial Balance Study ID (Sierra)";
        IBStudyID.SetInt(6);  // Study ID:6 — Initial Balance

        ProjHLStudyID.Name = "Projected High-Low Study ID (Sierra)";
        ProjHLStudyID.SetInt(0);  // 0 = disabled; set to Sierra Study ID when study is on chart

        TPOChartNumber.Name = "TPO Chart Number (0=same chart)";
        TPOChartNumber.SetInt(0);  // Set to the chart # where TPO/IB studies live

        WoodiesChartNumber.Name = "Woodies Chart Number (0=same chart)";
        WoodiesChartNumber.SetInt(0);  // Set to the chart # where Woodies studies live

        YesterdayIBStudyID.Name = "Yesterday Initial Balance Study ID (Sierra)";
        YesterdayIBStudyID.SetInt(0);  // 0 = disabled; set to Sierra Study ID of the IB study configured for the previous session

        ContinuousChartNumber.Name = "Continuous 24h Chart Number (0=disabled)";
        ContinuousChartNumber.SetInt(5);  // Chart #5 = MESM26 5-Min 24h Globex

        // v9.2.0: DISABLED — was causing Sierra-internal memory accumulation
        // (unbounded VAP storage per bar). Footprint export now uses fallback
        // distribution path which is bounded and safe.
        sc.MaintainVolumeAtPriceData = 0;

        return;
    }

    int idx = sc.Index;
    SCDateTime today = sc.BaseDateTimeIn[idx].GetDate();
    float cp  = sc.Close[idx];
    float ask_vol = sc.AskVolume[idx];
    float bid_vol = sc.BidVolume[idx];
    float delta   = ask_vol - bid_vol;

    // ── CVD ──────────────────────────────────────────────────
    CVD[idx] = (idx == 0) ? delta : CVD[idx - 1] + delta;
    float cvd20 = (idx >= 20) ? CVD[idx] - CVD[idx - 20] : 0;
    float cvd5  = (idx >= 5)  ? CVD[idx] - CVD[idx - 5]  : 0;

    // ── VWAP (מתחיל מחדש כל יום) ──────────────────────────
    float sum_pv = 0, sum_v = 0;
    for (int i = idx; i >= 0; i--)
    {
        if (sc.BaseDateTimeIn[i].GetDate() < today) break;
        float tp = (sc.High[i] + sc.Low[i] + sc.Close[i]) / 3.0f;
        float v  = sc.Volume[i];
        sum_pv += tp * v;
        sum_v  += v;
    }
    VWAP[idx] = (sum_v > 0) ? sum_pv / sum_v : cp;

    // ── Live Price Export (fast path — own throttle) ─────────
    // Runs every LivePriceIntervalMs (default 200ms), separate from
    // the main 3-second export. Minimal JSON, no heap allocs.
    if (LivePriceEnabled.GetInt() == 1)
    {
        static long long lastLivePriceMs = 0;
        long long nowMs = (long long)time(nullptr) * 1000;
        // Approximate ms from time_t (1-second resolution).
        // For sub-second: use sc.CurrentSystemDateTime if available.
        int intervalMs = LivePriceIntervalMs.GetInt();
        if (intervalMs < 50) intervalMs = 50;  // safety floor
        if ((nowMs - lastLivePriceMs) >= intervalMs || lastLivePriceMs == 0)
        {
            lastLivePriceMs = nowMs;
            const char* v9dir = V9ExportPath.GetString();
            // Build minimal JSON inline — no ostringstream, no alloc
            char buf[256];
            int len = snprintf(buf, sizeof(buf),
                "{\"price\":%.2f,\"ts\":%lld,\"bid\":%.2f,\"ask\":%.2f,\"vol\":%.0f}\n",
                cp, (long long)time(nullptr),
                sc.Bid, sc.Ask, sc.Volume[idx]);
            if (len > 0 && len < (int)sizeof(buf))
            {
                std::string path = std::string(v9dir) + "live_price.json";
                std::ofstream f(path.c_str());
                if (f.is_open()) { f.write(buf, len); f.close(); }
            }
        }
    }

    // ══ THROTTLE (EARLY — before heavy computation) ══════════
    // CVD + VWAP subgraph writes above run every bar (required for
    // accurate per-bar tracking). Everything below only runs every
    // ExportIntervalSec seconds. This prevents millions of map/vector
    // heap allocs during AutoLoop chart load (was causing 123 GB leak).
    static time_t lastExport = 0;
    time_t now_t = time(nullptr);
    if ((now_t - lastExport) < ExportIntervalSec.GetInt()) return;
    lastExport = now_t;

    float vwap = VWAP[idx];

    // VWAP distance & side
    float vwap_dist  = cp - vwap;
    bool  above_vwap = (cp > vwap);

    // VWAP pullback detection (last 5 bars trending toward VWAP from above/below)
    bool vwap_pullback = false;
    if (idx >= 5 && above_vwap)
    {
        bool was_higher = (sc.Close[idx-3] > sc.Close[idx-1]);
        bool low_volume = true;
        float avg_vol = 0;
        for (int i = idx-10; i < idx && i >= 0; i++) avg_vol += sc.Volume[i];
        avg_vol /= 10.0f;
        for (int i = idx-3; i <= idx; i++)
            if (sc.Volume[i] > avg_vol * 0.8f) { low_volume = false; break; }
        vwap_pullback = was_higher && low_volume && (cp - vwap < 4.0f);
    }

    // ── Woodi Pivots ─────────────────────────────────────────
    float PH=0, PL=0, PC=0;
    SCDateTime prevDate;
    bool foundPrev = false;
    for (int i = idx-1; i >= 0; i--)
    {
        SCDateTime bd = sc.BaseDateTimeIn[i].GetDate();
        if (!foundPrev && bd < today) { prevDate=bd; foundPrev=true; PC=sc.Close[i]; PH=sc.High[i]; PL=sc.Low[i]; }
        else if (foundPrev && bd == prevDate) { if (sc.High[i]>PH) PH=sc.High[i]; if (sc.Low[i]<PL) PL=sc.Low[i]; }
        else if (foundPrev) break;
    }
    float PP=0,R1=0,R2=0,S1=0,S2=0;
    if (foundPrev && PH>0) { PP=(PH+PL+PC*2)/4; R1=2*PP-PL; R2=PP+(PH-PL); S1=2*PP-PH; S2=PP-(PH-PL); }

    // ── Session POC + Value Area ──────────────────────────────
    float SH=sc.High[idx], SL=sc.Low[idx], TV=0;
    std::map<int,float> pvm;
    float HPrev=0,LPrev=0,CPrev=0;
    bool prevDayFound=false;
    for (int i=idx; i>=0; i--)
    {
        SCDateTime bd = sc.BaseDateTimeIn[i].GetDate();
        if (bd < today) {
            if (!prevDayFound) { HPrev=sc.High[i]; LPrev=sc.Low[i]; CPrev=sc.Close[i]; prevDayFound=true; }
            break;
        }
        float bh=sc.High[i], bl=sc.Low[i], bv=sc.Volume[i];
        if (bh>SH) SH=bh; if (bl<SL) SL=bl; TV+=bv;
        int steps=(int)((bh-bl)/0.25f)+1; float vps=bv/steps;
        int price_steps = 0;
        const int PRICE_MAX_STEPS = 1000;  // v9.2.0 safety cap
        for (float p=bl; p<=bh+0.001f && price_steps < PRICE_MAX_STEPS; p+=0.25f) {
            pvm[(int)(p*4)]+=vps;
            price_steps++;
        }
    }
    float POC=cp, maxV=0;
    for (auto& kv:pvm) if (kv.second>maxV){maxV=kv.second; POC=kv.first/4.0f;}

    float vat=TV*(VAPercent.GetFloat()/100), vav=maxV, VAH=POC, VAL=POC;
    auto itu=pvm.upper_bound((int)(POC*4)), itd=pvm.lower_bound((int)(POC*4));
    while(vav<vat){
        float un=(itu!=pvm.end())?itu->second:0, dn=(itd!=pvm.begin())?std::prev(itd)->second:0;
        if(un>=dn){if(itu!=pvm.end()){vav+=un;VAH=itu->first/4.0f;++itu;}else break;}
        else{if(itd!=pvm.begin()){--itd;vav+=itd->second;VAL=itd->first/4.0f;}else break;}
    }

    // TPO POC
    std::map<int,int> tpo_map;
    int tpo_back = (idx >= 30) ? 30 : idx;
    for(int i=idx-tpo_back; i<=idx; i++){
        for(float p=sc.Low[i]; p<=sc.High[i]+0.001f; p+=0.25f)
            tpo_map[(int)(p*4)]++;
    }
    float tpo_poc=cp; int tpo_max=0;
    for(auto& kv:tpo_map) if(kv.second>tpo_max){tpo_max=kv.second;tpo_poc=kv.first/4.0f;}

    // ── 72H / Weekly ─────────────────────────────────────────
    float H72=sc.High[idx],L72=sc.Low[idx],HWk=sc.High[idx],LWk=sc.Low[idx];
    SCDateTime t72=sc.BaseDateTimeIn[idx]; t72.SubtractSeconds(72*3600);
    SCDateTime twk=sc.BaseDateTimeIn[idx]; twk.SubtractSeconds((int)twk.GetDayOfWeek()*86400);
    for(int i=idx-1;i>=0;i--){
        SCDateTime bt=sc.BaseDateTimeIn[i];
        if(bt>=t72){if(sc.High[i]>H72)H72=sc.High[i];if(sc.Low[i]<L72)L72=sc.Low[i];}
        if(bt>=twk){if(sc.High[i]>HWk)HWk=sc.High[i];if(sc.Low[i]<LWk)LWk=sc.Low[i];}
        if(bt<t72&&bt<twk)break;
    }

    // ── Session Phase ─────────────────────────────────────────
    int H=sc.BaseDateTimeIn[idx].GetHour(), M=sc.BaseDateTimeIn[idx].GetMinute();
    const char* phase="OVERNIGHT";
    if(H==16&&M>=30)phase="OPEN";
    else if(H>=17&&H<19)phase="AM_SESSION";
    else if(H>=19&&H<21)phase="MIDDAY";
    else if(H>=21&&H<23)phase="PM_SESSION";
    else if(H==23)phase="CLOSE";
    float sesMin_f = (H*60.0f+M) - (16*60+30);
    int   sesMin   = (sesMin_f < 0) ? -1 : (int)sesMin_f;

    float slope = (idx >= 5) ? (sc.Close[idx] - sc.Close[idx-5]) / 5.0f : 0;

    // ── Imbalance Detection ───────────────────────────────────
    // בודק את הנר הנוכחי ו-4 הנרות האחרונים לחוסר איזון
    float imb_ratio = ImbalanceRatio.GetFloat();
    struct ImbLevel { float price; float buy_vol; float sell_vol; float ratio; };
    static std::vector<ImbLevel> imbalances;
    imbalances.clear();  // reuses capacity — no heap alloc after first call

    // בדיקת imbalance בנרות אחרונים
    int imb_lookback = (idx >= 5) ? 5 : idx;
    for (int i = idx - imb_lookback; i <= idx; i++)
    {
        if (i < 0) continue;
        float bv_bar = sc.AskVolume[i];
        float sv_bar = sc.BidVolume[i];
        float bar_range = sc.High[i] - sc.Low[i];
        if (bar_range < 0.5f) continue;

        float ratio = 0;
        float dom_price = (sc.High[i] + sc.Low[i]) / 2.0f;
        if (sv_bar > 0 && bv_bar / sv_bar >= imb_ratio) {
            ratio = bv_bar / sv_bar;
            imbalances.push_back({dom_price, bv_bar, sv_bar, ratio});
        } else if (bv_bar > 0 && sv_bar / bv_bar >= imb_ratio) {
            ratio = -(sv_bar / bv_bar);
            imbalances.push_back({dom_price, bv_bar, sv_bar, ratio});
        }
    }

    // מיין לפי ratio מוחלט (use v9_abs, not std::abs — ACSIL macro conflict)
    std::sort(imbalances.begin(), imbalances.end(), [](const ImbLevel& a, const ImbLevel& b){
        return v9_abs(a.ratio) > v9_abs(b.ratio);
    });

    // גבול: שמור עד 3 imbalances חזקים
    int imb_count = (int)imbalances.size();
    if (imb_count > 3) imb_count = 3;

    // Absorption detection: מוכרים הרבה אבל מחיר לא ירד
    bool absorption_bull = false;
    if (idx >= 3)
    {
        float sell_pressure = 0;
        for (int i = idx-2; i <= idx; i++) sell_pressure += sc.BidVolume[i];
        float price_change = sc.Close[idx] - sc.Close[idx-3];
        if (sell_pressure > 500 && price_change >= 0) absorption_bull = true;
    }

    // Liquidity sweep detection
    bool liq_sweep_long = false;
    bool liq_sweep_short = false;
    if (idx >= 3)
    {
        // Long sweep: מחיר שבר שפל ואז חזר מעליו
        float recent_low = SL;
        bool broke_low = (sc.Low[idx-1] < recent_low - 1.0f || sc.Low[idx-2] < recent_low - 1.0f);
        bool recovered  = (cp > recent_low + 0.5f);
        if (broke_low && recovered && delta > 0) liq_sweep_long = true;
    }

    // IB Breakout + Retest (מחושב כשיש IB)
    // יישלח ל-Bridge שיחשב

    // ── MTF (chart = 3 min per bar) ──────────────────────────
    struct MTFBar { float o,h,l,c,vol,buy,sell,delta_v; };
    auto calcBar = [&](int n) -> MTFBar {
        MTFBar b = {0,0,999999,0,0,0,0,0};
        int end = (idx-n+1>=0)?(idx-n+1):0;
        b.o=sc.Open[end]; b.c=sc.Close[idx];
        b.h=sc.High[end]; b.l=sc.Low[end];
        for(int i=end;i<=idx;i++){
            if(sc.High[i]>b.h)b.h=sc.High[i];
            if(sc.Low[i]<b.l)b.l=sc.Low[i];
            b.vol+=sc.Volume[i]; b.buy+=sc.AskVolume[i]; b.sell+=sc.BidVolume[i];
        }
        b.delta_v=b.buy-b.sell;
        return b;
    };
    MTFBar m3=calcBar(1), m15=calcBar(5), m30=calcBar(10), m60=calcBar(20);

    // ── Trend Strength ────────────────────────────────────────
    // HH/HL count in last 20 bars
    int hh_count=0, ll_count=0;
    for(int i=idx-1; i>=idx-20 && i>0; i--){
        if(sc.High[i]>sc.High[i-1]) hh_count++;
        if(sc.Low[i]<sc.Low[i-1])   ll_count++;
    }
    const char* trend_str = "NEUTRAL";
    if(hh_count > 14) trend_str = "STRONG_UP";
    else if(hh_count > 10) trend_str = "UP";
    else if(ll_count > 14) trend_str = "STRONG_DOWN";
    else if(ll_count > 10) trend_str = "DOWN";

    // ── JSON ──────────────────────────────────────────────────
    std::ostringstream j;
    j<<std::fixed<<std::setprecision(2);

    j<<"{"
     <<"\"timestamp\":"<<(long long)now_t
     <<",\"symbol\":\"MEMS26\""
     <<",\"current_price\":"<<cp
     <<",\"session_phase\":\""<<phase<<"\""
     <<",\"session_min\":"<<sesMin

     // CVD
     <<",\"cvd\":{"
       <<"\"current\":"<<CVD[idx]
       <<",\"change_20bar\":"<<cvd20
       <<",\"change_5bar\":"<<cvd5
       <<",\"cumul_today\":"<<CVD[idx]
       <<",\"trend\":\""<<(cvd20>100?"BULLISH":cvd20<-100?"BEARISH":"NEUTRAL")<<"\""
       <<",\"buy_vol\":"<<ask_vol
       <<",\"sell_vol\":"<<bid_vol
       <<",\"delta\":"<<delta
     <<"}"

     // VWAP
     <<",\"vwap\":{"
       <<"\"value\":"<<vwap
       <<",\"distance\":"<<vwap_dist
       <<",\"above\":"<<(above_vwap?"true":"false")
       <<",\"pullback\":"<<(vwap_pullback?"true":"false")
     <<"}"

     // Market Profile
     <<",\"market_profile\":{"
       <<"\"poc\":"<<POC
       <<",\"vah\":"<<VAH
       <<",\"val\":"<<VAL
       <<",\"session_high\":"<<SH
       <<",\"session_low\":"<<SL
       <<",\"tpo_poc\":"<<tpo_poc
       <<",\"in_value_area\":"<<(cp>=VAL&&cp<=VAH?"true":"false")
       <<",\"above_poc\":"<<(cp>POC?"true":"false")
     <<"}"

     // Woodi
     <<",\"woodi_pivots\":{"
       <<"\"pp\":"<<PP<<",\"r1\":"<<R1<<",\"r2\":"<<R2
       <<",\"s1\":"<<S1<<",\"s2\":"<<S2
       <<",\"above_pp\":"<<(cp>PP?"true":"false")
     <<"}"

     // Levels
     <<",\"time_levels\":{"
       <<"\"weekly_high\":"<<HWk<<",\"weekly_low\":"<<LWk
       <<",\"h72_high\":"<<H72<<",\"h72_low\":"<<L72
       <<",\"prev_high\":"<<HPrev<<",\"prev_low\":"<<LPrev<<",\"prev_close\":"<<CPrev
     <<"}"

     // Price Action
     <<",\"price_action\":{"
       <<"\"slope_5bar\":"<<slope
       <<",\"trend\":\""<<(slope>0?"UP":slope<0?"DOWN":"FLAT")<<"\""
       <<",\"trend_strength\":\""<<trend_str<<"\""
       <<",\"buy_vol_bar\":"<<ask_vol
       <<",\"sell_vol_bar\":"<<bid_vol
     <<"}"

     // Imbalance
     <<",\"order_flow\":{"
       <<"\"absorption_bull\":"<<(absorption_bull?"true":"false")
       <<",\"liq_sweep_long\":"<<(liq_sweep_long?"true":"false")
       <<",\"liq_sweep_short\":"<<(liq_sweep_short?"true":"false")
       <<",\"imbalances\":[";

    for(int i=0; i<imb_count; i++){
        if(i>0) j<<",";
        j<<"{"
         <<"\"price\":"<<imbalances[i].price
         <<",\"buy\":"<<imbalances[i].buy_vol
         <<",\"sell\":"<<imbalances[i].sell_vol
         <<",\"ratio\":"<<imbalances[i].ratio
         <<"}";
    }
    j<<"]}"

     // MTF
     <<",\"mtf\":{"
       <<"\"m3\":{\"o\":"<<m3.o<<",\"h\":"<<m3.h<<",\"l\":"<<m3.l<<",\"c\":"<<m3.c
         <<",\"vol\":"<<m3.vol<<",\"buy\":"<<m3.buy<<",\"sell\":"<<m3.sell<<",\"delta\":"<<m3.delta_v<<"}"
       <<",\"m15\":{\"o\":"<<m15.o<<",\"h\":"<<m15.h<<",\"l\":"<<m15.l<<",\"c\":"<<m15.c
         <<",\"vol\":"<<m15.vol<<",\"buy\":"<<m15.buy<<",\"sell\":"<<m15.sell<<",\"delta\":"<<m15.delta_v<<"}"
       <<",\"m30\":{\"o\":"<<m30.o<<",\"h\":"<<m30.h<<",\"l\":"<<m30.l<<",\"c\":"<<m30.c
         <<",\"vol\":"<<m30.vol<<",\"buy\":"<<m30.buy<<",\"sell\":"<<m30.sell<<",\"delta\":"<<m30.delta_v<<"}"
       <<",\"m60\":{\"o\":"<<m60.o<<",\"h\":"<<m60.h<<",\"l\":"<<m60.l<<",\"c\":"<<m60.c
         <<",\"vol\":"<<m60.vol<<",\"buy\":"<<m60.buy<<",\"sell\":"<<m60.sell<<",\"delta\":"<<m60.delta_v<<"}"
     <<"}"

     <<"}\n";

    std::ofstream f(ExportPath.GetString());
    if(f.is_open()){f<<j.str();f.close();}

    // ══════════════════════════════════════════════════════════════
    // V9 EXPORTS — New tick reversal + footprint + delta exports
    // ══════════════════════════════════════════════════════════════
    const char* v9dir = V9ExportPath.GetString();
    int v9_lookback = V9Lookback.GetInt();
    float v9_imb_threshold = 2.5f;  // 250% ratio for imbalance detection

    // ── Export 0: Canonical 5-minute OHLCV history for bars_5min bridge ──
    {
        int five_min_lookback = v9_min_i(v9_max_i(v9_lookback * 3, 600), 2000);
        std::string bars5_json = v9_5min_to_json(sc, five_min_lookback);
        v9_write_json(v9dir, "5min.json", bars5_json);
    }

    // ── Export 1: Tick Reversal 15-tick ──
    if (V9TickRev15.GetInt() == 1)
    {
        std::vector<TickReversalBar> tr15 = v9_build_tick_reversal_bars(sc, 15, v9_lookback);
        std::string json15 = v9_tick_reversal_to_json(tr15, 15);
        v9_write_json(v9dir, "tick_reversal_15.json", json15);
    }

    // ── Export 2: Tick Reversal 12-tick ──
    if (V9TickRev12.GetInt() == 1)
    {
        std::vector<TickReversalBar> tr12 = v9_build_tick_reversal_bars(sc, 12, v9_lookback);
        std::string json12 = v9_tick_reversal_to_json(tr12, 12);
        v9_write_json(v9dir, "tick_reversal_12.json", json12);
    }

    // ── Export 3+4+5: Footprint + Volume Profile + Imbalance Flags ──
    {
        v9_footprint_reset_budget();  // v9.2.0: reset per-cycle memory budget
        int fp_start = v9_max_i(0, sc.Index - 30);  // Last 30 chart bars
        std::vector<FootprintBar> fp_bars;
        for (int i = fp_start; i <= sc.Index; i++)
        {
            fp_bars.push_back(v9_build_footprint_bar(sc, i, v9_imb_threshold));
        }

        // Export 3: Footprint per bar — session-anchored cumulative delta
        float cum_delta = 0;
        for (int i = 0; i <= sc.Index; i++)
        {
            if (sc.BaseDateTimeIn[i].GetDate() < today) continue;
            cum_delta += sc.AskVolume[i] - sc.BidVolume[i];
        }
        std::string fp_json = v9_footprint_to_json(fp_bars, cum_delta);
        v9_write_json(v9dir, "footprint.json", fp_json);

        // Export 4: Volume Profile per bar
        std::string vp_json = v9_volume_profile_to_json(fp_bars, VAPercent.GetFloat());
        v9_write_json(v9dir, "volume_profile.json", vp_json);

        // Export 5: Imbalance flags (250%+)
        std::string imb_json = v9_imbalance_flags_to_json(fp_bars);
        v9_write_json(v9dir, "imbalance_flags.json", imb_json);

        // Export 6: Stacked imbalances (3+ consecutive)
        std::string stack_json = v9_stacked_imbalances_to_json(fp_bars, 3);
        v9_write_json(v9dir, "stacked_imbalances.json", stack_json);
    }

    // ── Export 7: Cumulative Delta running total ──
    {
        std::string cd_json = v9_cumulative_delta_to_json(sc, v9_lookback);
        v9_write_json(v9dir, "cumulative_delta.json", cd_json);
    }

    // ── Export 8: Woodies CCI 30-min (all 11 studies + patterns) ──
    {
        std::string w_json = v9_woodies_30min_to_json(sc, V9WoodiesHistory.GetInt());
        v9_write_json(v9dir, "woodies_30min.json", w_json);
    }

    // ── Export 8b: Woodies CCI 5-min (D-074: primary S4 / Cockpit panel) ──
    // Read all Woodies indicators from Sierra native studies for exact match.
    // Study IDs from Sierra chart (see docs/runbooks/SIERRA_DLL_OPS.md):
    //   ID:4  = CCI-14           (SG0)
    //   ID:10 = CCI-6 / TCCI     (SG0)
    //   ID:3  = Woodies EMA      (SG0)
    //   ID:2  = LSMA             (SG0)
    //   ID:6  = Sidewinder       (SG0)
    //   ID:7  = Chop Zone        (SG0)
    //   ID:12 = Pivot Points     (SG4=proj_hi, SG5=proj_lo)
    //   ID:11 = CCI Predictor    (SG0=hi, SG1=lo)
    {
        int w_chart = WoodiesChartNumber.GetInt();
        int wc = (w_chart > 0) ? w_chart : sc.ChartNumber;

        WoodiesSierraStudies sierra = {false, 0,0,0,0,0,0,0,0,0,0};

        if (w_chart > 0) {
            sierra.valid = true;
            SCFloatArray arr;

            // CCI-14 (Study ID:4, SG0)
            sc.GetStudyArrayFromChartUsingID(wc, 4, 0, arr);
            if (arr.GetArraySize() > idx) sierra.cci_14 = arr[idx];

            // CCI-6 / TCCI (Study ID:10, SG0)
            sc.GetStudyArrayFromChartUsingID(wc, 10, 0, arr);
            if (arr.GetArraySize() > idx) sierra.cci_6 = arr[idx];

            // Woodies EMA (Study ID:3, SG0)
            sc.GetStudyArrayFromChartUsingID(wc, 3, 0, arr);
            if (arr.GetArraySize() > idx) sierra.ema_34 = arr[idx];

            // LSMA (Study ID:2, SG0)
            sc.GetStudyArrayFromChartUsingID(wc, 2, 0, arr);
            if (arr.GetArraySize() > idx) sierra.lsma_25 = arr[idx];

            // Sidewinder (Study ID:6, SG5 = actual SWI value)
            // SG0/SG1 are ±200 reference lines, SG5 is the computed value
            sc.GetStudyArrayFromChartUsingID(wc, 6, 5, arr);
            if (arr.GetArraySize() > idx) sierra.sidewinder = arr[idx];

            // Chop Zone (Study ID:7, SG2 = angle value)
            // SG0/SG1 are ±100 reference lines, SG2 is the computed angle
            sc.GetStudyArrayFromChartUsingID(wc, 7, 2, arr);
            if (arr.GetArraySize() > idx) sierra.chopzone = arr[idx];

            // ProjHigh/ProjLow from Woodies Panel (Study ID:9, SG1/SG2)
            // NOT from Pivot Points — the Panel study holds these values
            sc.GetStudyArrayFromChartUsingID(wc, 9, 1, arr);
            if (arr.GetArraySize() > idx) sierra.proj_hi = arr[idx];
            sc.GetStudyArrayFromChartUsingID(wc, 9, 2, arr);
            if (arr.GetArraySize() > idx) sierra.proj_lo = arr[idx];

            // CCI-14 previous bar (for predictor + trend accuracy)
            sc.GetStudyArrayFromChartUsingID(wc, 4, 0, arr);
            if (arr.GetArraySize() > idx && idx > 0) sierra.cci_14_prev = arr[idx - 1];
        }


        std::string w5_json = v9_woodies_5min_to_json(
            sc, V9WoodiesHistory.GetInt(),
            sierra.valid ? &sierra : nullptr,
            wc, ProjHLStudyID.GetInt());
        v9_write_json(v9dir, "woodies_5min.json", w5_json);
    }

    // ── Export 9: TPO session levels from Sierra native studies ──
    // Reads POC/VAH/VAL from Sierra TPO Value Area Lines (IDs 1, 3)
    // and IB from Initial Balance (ID 6) via GetStudyArrayFromChartUsingID.
    {
        int tpo_yday_id = TPOYesterdayStudyID.GetInt();
        int tpo_today_id = TPOTodayStudyID.GetInt();
        int ib_study_id  = IBStudyID.GetInt();
        int tpo_chart = TPOChartNumber.GetInt();
        int chart_num = (tpo_chart > 0) ? tpo_chart : sc.ChartNumber;

        // Sierra TPO Value Area Lines subgraph layout (verified Sierra UI 2026-05-25):
        //   UI SG1 = TPO POC  (ACSIL idx 0)
        //   UI SG2 = TPO VAH  (ACSIL idx 1)
        //   UI SG3 = TPO VAL  (ACSIL idx 2)
        // Sierra Initial Balance subgraph layout (verified Sierra UI 2026-05-25):
        //   UI SG7 = IB High  (ACSIL idx 6)  — NOT SG1 as previously documented
        //   UI SG8 = IB Mid   (ACSIL idx 7)  — we compute mid as (high+low)/2 instead
        //   UI SG9 = IB Low   (ACSIL idx 8)  — NOT SG2 as previously documented
        // Reference: docs/forensics/SIERRA_UI_EVIDENCE_2026-05-25.md

        std::ostringstream j;
        j << std::fixed << std::setprecision(2);
        j << "{";
        json_str(j, "type", "tpo", false);
        json_str(j, "version", V9_VERSION);
        json_long(j, "export_ts", (long long)time(nullptr));

        // ── Today's developing TPO (Study ID:3, ref=0) ──
        SCFloatArray today_poc, today_vah, today_val;
        bool today_ok = false;
        float t_poc = 0, t_vah = 0, t_val = 0;
        if (tpo_today_id > 0) {
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_today_id, 0, today_poc);
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_today_id, 1, today_vah);
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_today_id, 2, today_val);
            if (today_poc.GetArraySize() > idx && today_poc[idx] != 0) {
                t_poc = today_poc[idx];
                t_vah = (today_vah.GetArraySize() > idx) ? today_vah[idx] : 0;
                t_val = (today_val.GetArraySize() > idx) ? today_val[idx] : 0;
                today_ok = true;
            }
        }

        // Session high/low from chart data (today only)
        float ses_high = sc.High[idx], ses_low = sc.Low[idx];
        for (int i = idx; i >= 0; i--) {
            if (sc.BaseDateTimeIn[i].GetDate() < today) break;
            if (sc.High[i] > ses_high) ses_high = sc.High[i];
            if (sc.Low[i] < ses_low)  ses_low  = sc.Low[i];
        }

        // G4: va_ok = true only if Sierra TPO study produced valid values
        bool va_ok = today_ok
            && t_poc > 3000 && t_poc < 10000
            && t_vah > 3000 && t_vah < 10000
            && t_val > 3000 && t_val < 10000
            && t_vah >= t_val;

        // Session date as "YYYY-MM-DD" (from current wall-clock time)
        char ses_date_buf[16] = {0};
        {
            time_t t_now = time(nullptr);
            struct tm tm_now;
            localtime_s(&tm_now, &t_now);
            snprintf(ses_date_buf, sizeof(ses_date_buf), "%04d-%02d-%02d",
                     tm_now.tm_year + 1900, tm_now.tm_mon + 1, tm_now.tm_mday);
        }

        // G2 (Memorial Day fix): reset session values to 0 when va_ok=false
        // Mirrors previous_session pattern at line 765-774 — prevents
        // garbage like poc=-89088 from leaking into tpo.json.
        if (!va_ok) {
            t_poc = 0; t_vah = 0; t_val = 0;
        }

        j << ",\"session\":{";
        json_float(j, "poc", t_poc, false);
        json_float(j, "vah", t_vah);
        json_float(j, "val", t_val);
        json_bool(j, "va_ok", va_ok);
        json_str(j, "session_date", ses_date_buf);
        json_float(j, "session_high", ses_high);
        json_float(j, "session_low", ses_low);
        json_float(j, "total_volume", 0);  // placeholder until we sum
        j << "}";

        // ── Initial Balance (Study ID:6) ──
        SCFloatArray ib_high_arr, ib_low_arr;
        float ib_h = 0, ib_l = 0;
        bool ib_found = false;
        if (ib_study_id > 0) {
            sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 6, ib_high_arr);
            sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 8, ib_low_arr);
            if (ib_high_arr.GetArraySize() > idx && ib_high_arr[idx] != 0) {
                ib_h = ib_high_arr[idx];
                ib_l = (ib_low_arr.GetArraySize() > idx) ? ib_low_arr[idx] : 0;
                ib_found = (ib_h > 0 && ib_l > 0);
            }
        }
        float ib_mid = ib_found ? (ib_h + ib_l) / 2.0f : 0;

        j << ",\"ib\":{";
        json_bool(j, "found", ib_found, false);
        json_float(j, "high", ib_h);
        json_float(j, "mid", ib_mid);
        json_float(j, "low", ib_l);
        j << "}";

        // ── Yesterday's locked TPO (Study ID:1, ref=1) ──
        SCFloatArray yday_poc, yday_vah, yday_val;
        float y_poc = 0, y_vah = 0, y_val = 0;
        bool yday_ok = false;
        if (tpo_yday_id > 0) {
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_yday_id, 0, yday_poc);
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_yday_id, 1, yday_vah);
            sc.GetStudyArrayFromChartUsingID(chart_num, tpo_yday_id, 2, yday_val);
            if (yday_poc.GetArraySize() > idx && yday_poc[idx] != 0) {
                y_poc = yday_poc[idx];
                y_vah = (yday_vah.GetArraySize() > idx) ? yday_vah[idx] : 0;
                y_val = (yday_val.GetArraySize() > idx) ? yday_val[idx] : 0;
                yday_ok = true;
            }
        }

        // Prior-day high/low/close from chart data
        float pd_high = 0, pd_low = 0, pd_close = 0;
        bool pd_found = false;
        for (int i = idx - 1; i >= 0; i--) {
            SCDateTime bd = sc.BaseDateTimeIn[i].GetDate();
            if (bd < today && !pd_found) {
                pd_high = sc.High[i]; pd_low = sc.Low[i]; pd_close = sc.Close[i];
                SCDateTime prev_date = bd;
                for (int k = i; k >= 0; k--) {
                    if (sc.BaseDateTimeIn[k].GetDate() != prev_date) break;
                    if (sc.High[k] > pd_high) pd_high = sc.High[k];
                    if (sc.Low[k] < pd_low) pd_low = sc.Low[k];
                }
                pd_found = true;
                break;
            }
        }

        j << ",\"prior_day\":{";
        json_bool(j, "found", pd_found, false);
        json_float(j, "high", pd_high);
        json_float(j, "low", pd_low);
        json_float(j, "close", pd_close);
        j << "}";

        // G2: Validate previous_session values — reject corrupt Sierra output
        // (e.g. poc=-76624, val=0). Valid MES range: 3000–10000.
        bool y_valid = yday_ok
            && y_poc > 3000 && y_poc < 10000
            && y_vah > 3000 && y_vah < 10000
            && y_val > 3000 && y_val < 10000
            && y_vah >= y_val;
        if (!y_valid) {
            y_poc = 0; y_vah = 0; y_val = 0;
        }

        // ── Yesterday Initial Balance (Step 9, 2026-05-28) ──
        // Same subgraph layout as today's IB study (Study ID:6):
        //   ACSIL idx 6 = IB High, idx 8 = IB Low.
        // The Sierra Study ID is configured via Input 19 (default 0 = disabled).
        // When disabled or invalid, emit 0 so backend can treat as null.
        int y_ib_study_id = YesterdayIBStudyID.GetInt();
        float y_ib_h = 0, y_ib_l = 0;
        bool y_ib_found = false;
        if (y_ib_study_id > 0) {
            SCFloatArray y_ib_high_arr, y_ib_low_arr;
            sc.GetStudyArrayFromChartUsingID(chart_num, y_ib_study_id, 6, y_ib_high_arr);
            sc.GetStudyArrayFromChartUsingID(chart_num, y_ib_study_id, 8, y_ib_low_arr);
            if (y_ib_high_arr.GetArraySize() > idx && y_ib_high_arr[idx] != 0) {
                y_ib_h = y_ib_high_arr[idx];
                y_ib_l = (y_ib_low_arr.GetArraySize() > idx) ? y_ib_low_arr[idx] : 0;
                // MES range validation — reject corrupt Sierra output
                bool y_ib_ok = y_ib_h > 3000 && y_ib_h < 10000
                            && y_ib_l > 3000 && y_ib_l < 10000
                            && y_ib_h >= y_ib_l;
                if (y_ib_ok) {
                    y_ib_found = true;
                } else {
                    y_ib_h = 0; y_ib_l = 0;
                }
            }
        }

        j << ",\"previous_session\":{";
        json_bool(j, "found", y_valid, false);
        json_float(j, "poc", y_poc);
        json_float(j, "vah", y_vah);
        json_float(j, "val", y_val);
        json_bool(j, "ib_found", y_ib_found);
        json_float(j, "ib_high", y_ib_h);
        json_float(j, "ib_low", y_ib_l);
        j << "}";

        j << "}";
        v9_write_json(v9dir, "tpo.json", j.str());
    }

    // ══════════════════════════════════════════════════════════════
    // T2.2: Trade Command Polling (reads command, writes result)
    // Bridge writes trade_command.json → DLL reads → executes → writes trade_result.json
    // ══════════════════════════════════════════════════════════════
    {
        const char* cmd_path = TradeCommandPath.GetString();
        if (cmd_path[0] != '\0')
        {
            std::ifstream cmd_file(cmd_path);
            if (cmd_file.is_open())
            {
                std::string cmd_content((std::istreambuf_iterator<char>(cmd_file)),
                                         std::istreambuf_iterator<char>());
                cmd_file.close();

                // Only process if non-empty and contains "action"
                if (cmd_content.size() > 10 && cmd_content.find("\"action\"") != std::string::npos)
                {
                    // Parse action field (simple string search — no JSON lib in ACSIL)
                    const char* result_status = "UNKNOWN";
                    int order_err = 0;

                    if (cmd_content.find("\"BUY\"") != std::string::npos ||
                        cmd_content.find("\"SELL\"") != std::string::npos)
                    {
                        // Bracket order: entry + stop + T1/T2/T3
                        // TODO: Implement actual Sierra order placement via
                        // sc.SubmitOrder() / sc.SubmitOCOOrder() when DEMO/LIVE mode enabled.
                        // For now: acknowledge receipt (SHADOW mode = paper only).
                        result_status = "ACK_SHADOW";
                    }
                    else if (cmd_content.find("\"CLOSE\"") != std::string::npos)
                    {
                        result_status = "ACK_CLOSE";
                    }
                    else if (cmd_content.find("\"CANCEL\"") != std::string::npos)
                    {
                        result_status = "ACK_CANCEL";
                    }
                    else if (cmd_content.find("\"MODIFY_STOP\"") != std::string::npos ||
                             cmd_content.find("\"MODIFY_TARGET\"") != std::string::npos ||
                             cmd_content.find("\"ARM_BE\"") != std::string::npos ||
                             cmd_content.find("\"SCALE_OUT\"") != std::string::npos ||
                             cmd_content.find("\"BAILOUT\"") != std::string::npos)
                    {
                        result_status = "ACK_MGMT";
                    }

                    // Write result JSON
                    const char* res_path = TradeResultPath.GetString();
                    if (res_path[0] != '\0')
                    {
                        char res_buf[512];
                        int res_len = snprintf(res_buf, sizeof(res_buf),
                            "{\"status\":\"%s\",\"ts\":%lld,\"error\":%d}\n",
                            result_status, (long long)time(nullptr), order_err);
                        if (res_len > 0 && res_len < (int)sizeof(res_buf))
                        {
                            std::ofstream res_file(res_path);
                            if (res_file.is_open()) { res_file.write(res_buf, res_len); res_file.close(); }
                        }
                    }

                    // Clear command file after processing (prevent re-read)
                    std::ofstream clear_cmd(cmd_path, std::ofstream::trunc);
                    if (clear_cmd.is_open()) clear_cmd.close();
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════
    // T2.3: Reversal Bar Cluster Export
    // Exports per-bar cluster + empty zone data for Layer 3
    // ══════════════════════════════════════════════════════════════
    {
        // Export the current bar's volume distribution as cluster data
        // This supplements tick_reversal_15.json with microstructure
        int rev_idx = sc.Index;
        float bar_h = sc.High[rev_idx];
        float bar_l = sc.Low[rev_idx];
        float bar_v = sc.Volume[rev_idx];
        float bar_ask = sc.AskVolume[rev_idx];
        float bar_bid = sc.BidVolume[rev_idx];
        float bar_range = bar_h - bar_l;

        if (bar_range > 0 && bar_v > 0)
        {
            float tick = sc.TickSize;
            if (tick <= 0) tick = 0.25f;
            int steps = (int)(bar_range / tick) + 1;
            if (steps > 200) steps = 200;

            // Find POC (highest volume level) via simple distribution
            float vol_per_step = bar_v / steps;
            float poc_price = (bar_h + bar_l) / 2.0f;
            float poc_vol = vol_per_step;

            // For cluster: top 3 levels around midpoint
            float mid = (bar_h + bar_l) / 2.0f;
            float cluster_high = (mid + tick > bar_h) ? bar_h : mid + tick;
            float cluster_low = (mid - tick < bar_l) ? bar_l : mid - tick;

            // Empty zone: levels at extremes with low volume
            float empty_high = bar_h;
            float empty_low = bar_h - tick;

            char cb[512];
            int cl = snprintf(cb, sizeof(cb),
                "{\"bar_idx\":%d,\"poc\":%.2f,\"poc_vol\":%.0f,"
                "\"cluster_high\":%.2f,\"cluster_low\":%.2f,"
                "\"empty_high\":%.2f,\"empty_low\":%.2f,"
                "\"bar_vol\":%.0f,\"bar_delta\":%.0f,\"ts\":%lld}\n",
                rev_idx, poc_price, poc_vol,
                cluster_high, cluster_low,
                empty_high, empty_low,
                bar_v, bar_ask - bar_bid, (long long)time(nullptr));
            if (cl > 0 && cl < (int)sizeof(cb))
            {
                std::string rpath = std::string(v9dir) + "reversal_cluster.json";
                std::ofstream rf(rpath.c_str());
                if (rf.is_open()) { rf.write(cb, cl); rf.close(); }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════
    // Export 10: Continuous 24h 5-min bars + CVD from chart #5
    // Reads OHLCV + bid/ask volume from a 24h Globex chart (Input 20).
    // Writes to SEPARATE files — does NOT touch chart #12 RTH exports.
    // ══════════════════════════════════════════════════════════════
    {
        int cont_chart = ContinuousChartNumber.GetInt();
        if (cont_chart > 0)
        {
            // ACSIL: GetChartBaseData fills ALL base arrays at once into SCGraphData
            SCGraphData c5_data;
            SCDateTimeArray c5_dt;

            sc.GetChartBaseData(cont_chart, c5_data);
            sc.GetChartDateTimeArray(cont_chart, c5_dt);

            int c5_size = c5_data[SC_OPEN].GetArraySize();
            if (c5_size > 0 && c5_dt.GetArraySize() >= c5_size)
            {
                int lookback = v9_min_i(c5_size, 600);
                int start = c5_size - lookback;

                // ── 5min_continuous.json: OHLCV bars ──
                {
                    std::ostringstream j;
                    j << std::fixed << std::setprecision(2);
                    j << "{";
                    json_str(j, "type", "5min_continuous", false);
                    json_str(j, "version", V9_VERSION);
                    json_long(j, "export_ts", (long long)time(nullptr));
                    json_int(j, "chart_number", cont_chart);
                    json_int(j, "total_bars", lookback);

                    j << ",\"bars\":[";
                    bool first = true;
                    for (int i = start; i < c5_size; i++)
                    {
                        long long ts = v9_sc_datetime_to_unix(c5_dt[i]);
                        if (ts <= 0) continue;
                        float o = c5_data[SC_OPEN][i], h = c5_data[SC_HIGH][i];
                        float l = c5_data[SC_LOW][i], c = c5_data[SC_LAST][i];
                        float v = c5_data[SC_VOLUME][i];
                        float delta = (i < (int)c5_data[SC_ASKVOL].GetArraySize() && i < (int)c5_data[SC_BIDVOL].GetArraySize())
                                    ? c5_data[SC_ASKVOL][i] - c5_data[SC_BIDVOL][i] : 0;

                        if (!first) j << ",";
                        first = false;
                        j << "{";
                        json_long(j, "ts", ts, false);
                        json_float(j, "o", o);
                        json_float(j, "h", h);
                        json_float(j, "l", l);
                        json_float(j, "c", c);
                        json_float(j, "vol", v);
                        json_float(j, "delta", delta);
                        j << "}";
                    }
                    j << "]";
                    j << "}";
                    v9_write_json(v9dir, "5min_continuous.json", j.str());
                }

                // ── cumulative_delta_continuous.json: session-anchored CVD ──
                {
                    // Find session start: 18:00 ET rollover (same as main CVD export).
                    // For simplicity: anchor to the start of lookback window.
                    // The bridge/backend handles session reset boundaries.
                    std::ostringstream j;
                    j << std::fixed << std::setprecision(2);
                    j << "{";
                    json_str(j, "type", "cumulative_delta_continuous", false);
                    json_str(j, "version", V9_VERSION);
                    json_long(j, "export_ts", (long long)time(nullptr));
                    json_int(j, "chart_number", cont_chart);
                    json_int(j, "output_interval", 300);

                    j << ",\"points\":[";
                    float running = 0;
                    bool first = true;
                    for (int i = start; i < c5_size; i++)
                    {
                        long long ts = v9_sc_datetime_to_unix(c5_dt[i]);
                        if (ts <= 0) continue;
                        float d = (i < (int)c5_data[SC_ASKVOL].GetArraySize() && i < (int)c5_data[SC_BIDVOL].GetArraySize())
                                ? c5_data[SC_ASKVOL][i] - c5_data[SC_BIDVOL][i] : 0;
                        running += d;

                        if (!first) j << ",";
                        first = false;
                        j << "{";
                        json_long(j, "t", ts, false);
                        json_float(j, "d", d);
                        json_float(j, "cum", running);
                        json_float(j, "p", c5_data[SC_LAST][i]);
                        j << "}";
                    }
                    j << "]";

                    json_float(j, "current_delta", running);
                    j << "}";
                    v9_write_json(v9dir, "cumulative_delta_continuous.json", j.str());
                }
            }
        }
    }
}
