// MES_AI_DataExport.cpp — v8.1 / V6.7.0 (C5: 3-Bracket Trade Execution)
// Sierra Chart ACSIL Study — 3 minute chart
// מייצא: MTF (כולל m5), CVD, VWAP, Market Profile, Woodi Pivots + CCI, IB, Day Type,
//         Opening Range, Prev Day POC, Gap, Relative Volume, Candle Patterns,
//         Footprint (10 נרות), Order Fills, HistoryInit (960 נרות)
// C5: Reads trade_command.json, verifies checksum, executes bracket order

#include "sierrachart.h"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <map>
#include <vector>
#include <algorithm>
#include <cmath>

SCDLLName("MES_AI_DataExport")

#define MEMS26_DLL_VERSION "v7.7.1c"

// ── CCI Helper ────────────────────────────────────────────────────────────────
static float calcCCI(SCStudyInterfaceRef& sc, int idx, int period)
{
    if (idx < period - 1) return 0.0f;
    float sum = 0;
    for (int i = idx - period + 1; i <= idx; i++)
        sum += (sc.High[i] + sc.Low[i] + sc.Close[i]) / 3.0f;
    float mean = sum / period;
    float mad = 0;
    for (int i = idx - period + 1; i <= idx; i++)
        mad += std::fabs((sc.High[i] + sc.Low[i] + sc.Close[i]) / 3.0f - mean);
    mad /= period;
    if (mad < 0.0001f) return 0.0f;
    float tp = (sc.High[idx] + sc.Low[idx] + sc.Close[idx]) / 3.0f;
    return (tp - mean) / (0.015f * mad);
}

// ── Candle Pattern Helper ─────────────────────────────────────────────────────
static const char* detectCandlePattern(float o, float h, float l, float c)
{
    float body  = std::fabs(c - o);
    float range = h - l;
    if (range < 0.01f) return "DOJI";
    float upper_wick = h - (o > c ? o : c);
    float lower_wick = (o < c ? o : c) - l;
    float body_pct   = body / range;
    if (body_pct < 0.1f) return "DOJI";
    if (lower_wick > 2.0f * body && upper_wick < body * 0.5f && c > o) return "HAMMER";
    if (upper_wick > 2.0f * body && lower_wick < body * 0.5f && c < o) return "SHOOTING_STAR";
    if (c > o && body_pct > 0.6f && c > (h - range * 0.2f)) return "BULL_STRONG";
    if (c < o && body_pct > 0.6f && c < (l + range * 0.2f)) return "BEAR_STRONG";
    return (c >= o) ? "BULL" : "BEAR";
}

// ── SCDateTime → Unix Timestamp ──────────────────────────────────────────────
static long long ToUnixTime(SCDateTime dt)
{
    // SCDateTime = OLE Automation date (days since Dec 30 1899)
    // Unix epoch = Jan 1 1970 = OLE day 25569
    return (long long)((dt.GetAsDouble() - 25569.0) * 86400.0 + 0.5);
}

// ── Session Phase Helper ──────────────────────────────────────────────────────
static const char* getPhase(int H, int M)
{
    if (H == 9 && M >= 30) return "OPEN";
    if (H >= 9 && H < 11)  return "AM_SESSION";
    if (H >= 11 && H < 13) return "MIDDAY";
    if (H >= 13 && H < 16) return "PM_SESSION";
    if (H == 16)           return "CLOSE";
    return "OVERNIGHT";
}

// ── SHA-256 (minimal, self-contained) ────────────────────────────────────────
static void sha256(const unsigned char* data, size_t len, unsigned char out[32])
{
    uint32_t h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,
             h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
    static const uint32_t k[64]={
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    // Padding
    size_t new_len = len + 1;
    while (new_len % 64 != 56) new_len++;
    std::vector<unsigned char> msg(new_len + 8, 0);
    memcpy(&msg[0], data, len);
    msg[len] = 0x80;
    uint64_t bit_len = (uint64_t)len * 8;
    for (int i = 0; i < 8; i++) msg[new_len + 7 - i] = (unsigned char)(bit_len >> (i * 8));
    // Process blocks
    for (size_t off = 0; off < msg.size(); off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; i++)
            w[i] = ((uint32_t)msg[off+i*4]<<24)|((uint32_t)msg[off+i*4+1]<<16)|
                   ((uint32_t)msg[off+i*4+2]<<8)|msg[off+i*4+3];
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = ((w[i-15]>>7)|(w[i-15]<<25))^((w[i-15]>>18)|(w[i-15]<<14))^(w[i-15]>>3);
            uint32_t s1 = ((w[i-2]>>17)|(w[i-2]<<15))^((w[i-2]>>19)|(w[i-2]<<13))^(w[i-2]>>10);
            w[i] = w[i-16]+s0+w[i-7]+s1;
        }
        uint32_t a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,hh=h7;
        for (int i = 0; i < 64; i++) {
            uint32_t S1=((e>>6)|(e<<26))^((e>>11)|(e<<21))^((e>>25)|(e<<7));
            uint32_t ch=(e&f)^((~e)&g);
            uint32_t t1=hh+S1+ch+k[i]+w[i];
            uint32_t S0=((a>>2)|(a<<30))^((a>>13)|(a<<19))^((a>>22)|(a<<10));
            uint32_t maj=(a&b)^(a&c)^(b&c);
            uint32_t t2=S0+maj;
            hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h0+=a;h1+=b;h2+=c;h3+=d;h4+=e;h5+=f;h6+=g;h7+=hh;
    }
    uint32_t hash[8]={h0,h1,h2,h3,h4,h5,h6,h7};
    for(int i=0;i<8;i++){out[i*4]=(unsigned char)(hash[i]>>24);out[i*4+1]=(unsigned char)(hash[i]>>16);
        out[i*4+2]=(unsigned char)(hash[i]>>8);out[i*4+3]=(unsigned char)hash[i];}
}

static std::string sha256hex(const std::string& input)
{
    unsigned char hash[32];
    sha256((const unsigned char*)input.c_str(), input.size(), hash);
    char hex[65];
    for (int i = 0; i < 32; i++) sprintf(hex + i * 2, "%02x", hash[i]);
    hex[64] = 0;
    return std::string(hex);
}

// ── Minimal JSON field extraction (no external lib) ──────────────────────────
static std::string jsonStr(const std::string& json, const std::string& key)
{
    std::string search = "\"" + key + "\"";
    size_t p = json.find(search);
    if (p == std::string::npos) return "";
    p = json.find(':', p);
    if (p == std::string::npos) return "";
    p++;
    while (p < json.size() && json[p] == ' ') p++;
    if (p < json.size() && json[p] == '"') {
        size_t start = p + 1;
        size_t end = json.find('"', start);
        return (end != std::string::npos) ? json.substr(start, end - start) : "";
    }
    // number or bool
    size_t start = p;
    size_t end = json.find_first_of(",} \n\r", start);
    return (end != std::string::npos) ? json.substr(start, end - start) : json.substr(start);
}

static double jsonNum(const std::string& json, const std::string& key)
{
    std::string v = jsonStr(json, key);
    return v.empty() ? 0.0 : atof(v.c_str());
}

static long long jsonInt(const std::string& json, const std::string& key)
{
    std::string v = jsonStr(json, key);
    return v.empty() ? 0LL : atoll(v.c_str());
}

SCSFExport scsf_MES_AI_DataExport(SCStudyInterfaceRef sc)
{
    SCSubgraphRef CVD   = sc.Subgraph[0];
    SCSubgraphRef VWAP  = sc.Subgraph[1];
    SCSubgraphRef CCI14 = sc.Subgraph[2];
    SCSubgraphRef CCI6  = sc.Subgraph[3];

    SCInputRef ExportPath        = sc.Input[0];
    SCInputRef ExportIntervalSec = sc.Input[1];
    SCInputRef VAPercent         = sc.Input[2];
    SCInputRef ImbalanceRatio    = sc.Input[3];
    SCInputRef IBPeriodMin       = sc.Input[4];
    SCInputRef HistoryPath       = sc.Input[5];
    SCInputRef FootprintBars     = sc.Input[6];
    SCInputRef CommandPath       = sc.Input[7];
    SCInputRef ResultPath        = sc.Input[8];
    SCInputRef BridgeToken       = sc.Input[9];

    if (sc.SetDefaults)
    {
        sc.GraphName        = "MES AI Data Export v7.7.1c";
        sc.UpdateAlways     = 1;  // V7.7.1: run every update for position monitoring
        sc.StudyDescription = "Full export v7: All indicators + Footprint Booleans + OrderFills + History960";
        sc.AutoLoop         = 1;
        sc.GraphRegion      = 1;
        sc.MaintainVolumeAtPriceData = 1;
        CVD.Name   = "CVD";   CVD.DrawStyle   = DRAWSTYLE_LINE; CVD.PrimaryColor   = COLOR_CYAN;
        VWAP.Name  = "VWAP";  VWAP.DrawStyle  = DRAWSTYLE_LINE; VWAP.PrimaryColor  = COLOR_YELLOW;
        CCI14.Name = "CCI14"; CCI14.DrawStyle = DRAWSTYLE_LINE; CCI14.PrimaryColor = COLOR_WHITE;
        CCI6.Name  = "CCI6";  CCI6.DrawStyle  = DRAWSTYLE_LINE; CCI6.PrimaryColor  = COLOR_GREEN;
        ExportPath.Name = "Export JSON Path";
        ExportPath.SetString("C:\\SierraChart2\\Data\\mes_ai_data.json");
        ExportIntervalSec.Name = "Export Interval (seconds)"; ExportIntervalSec.SetInt(3);
        VAPercent.Name = "Value Area %"; VAPercent.SetFloat(70.0f);
        ImbalanceRatio.Name = "Imbalance Ratio"; ImbalanceRatio.SetFloat(3.0f);
        IBPeriodMin.Name = "IB Period (minutes)"; IBPeriodMin.SetInt(60);
        HistoryPath.Name = "History JSON Path";
        HistoryPath.SetString("C:\\SierraChart2\\Data\\mes_ai_history.json");
        FootprintBars.Name = "Footprint Bars Count";
        FootprintBars.SetInt(200);
        CommandPath.Name = "Trade Command JSON Path";
        CommandPath.SetString("C:\\SierraChart2\\Data\\trade_command.json");
        ResultPath.Name = "Trade Result JSON Path";
        ResultPath.SetString("C:\\SierraChart2\\Data\\trade_result.json");
        BridgeToken.Name = "Bridge Token";
        BridgeToken.SetString("michael-mems26-2026");
        // V7.0: Trading variables for single-bracket-with-3-targets model
        // Per Sierra Chart Engineering (ThreadID=105021), this is the
        // supported native pattern for partial scale-out.
        sc.AllowOnlyOneTradePerBar              = 0;
        sc.SupportAttachedOrdersForTrading      = 1;
        sc.MaintainTradeStatisticsAndTradesData = 1;
        sc.AllowMultipleEntriesInSameDirection   = 0;
        sc.AllowEntryWithWorkingOrders           = 1;
        sc.MaximumPositionAllowed                = 10;
        sc.SupportReversals                      = 0;
        sc.AllowOppositeEntryWithOpposingPositionOrOrders = 0;
        sc.CancelAllOrdersOnEntriesAndReversals  = 0;
        sc.CancelAllWorkingOrdersOnExit          = 0;
        sc.AddMessageToLog(SCString().Format(
            "MES_AI_DataExport loaded — DLL version: %s built: %s %s",
            MEMS26_DLL_VERSION, __DATE__, __TIME__), 1);
        return;
    }

    // V7.4: Must be set OUTSIDE SetDefaults per Sierra docs
    sc.SupportTradingScaleIn  = 1;
    sc.SupportTradingScaleOut = 1;

    int idx = sc.Index;
    SCDateTime now_dt = sc.BaseDateTimeIn[idx];
    SCDateTime today  = now_dt.GetDate();
    float cp      = sc.Close[idx];
    float ask_vol = sc.AskVolume[idx];
    float bid_vol = sc.BidVolume[idx];
    float delta   = ask_vol - bid_vol;
    int   H = now_dt.GetHour(), M = now_dt.GetMinute();

    // ── CVD ──────────────────────────────────────────────────
    CVD[idx] = (idx == 0) ? delta : CVD[idx - 1] + delta;
    float cvd20 = (idx >= 20) ? CVD[idx] - CVD[idx - 20] : 0;
    float cvd5  = (idx >= 5)  ? CVD[idx] - CVD[idx - 5]  : 0;

    // ── VWAP ─────────────────────────────────────────────────
    float sum_pv = 0, sum_v = 0;
    for (int i = idx; i >= 0; i--) {
        if (sc.BaseDateTimeIn[i].GetDate() < today) break;
        float tp = (sc.High[i] + sc.Low[i] + sc.Close[i]) / 3.0f;
        sum_pv += tp * sc.Volume[i]; sum_v += sc.Volume[i];
    }
    VWAP[idx] = (sum_v > 0) ? sum_pv / sum_v : cp;
    float vwap = VWAP[idx], vwap_dist = cp - vwap;
    bool above_vwap = (cp > vwap), vwap_pullback = false;
    if (idx >= 5 && above_vwap) {
        bool was_higher = (sc.Close[idx-3] > sc.Close[idx-1]);
        float avg_vol = 0; for (int i=idx-10;i<idx&&i>=0;i++) avg_vol+=sc.Volume[i]; avg_vol/=10.0f;
        bool low_vol = true; for (int i=idx-3;i<=idx;i++) if(sc.Volume[i]>avg_vol*0.8f){low_vol=false;break;}
        vwap_pullback = was_higher && low_vol && (cp-vwap<4.0f);
    }

    // ── Woodi Pivots ─────────────────────────────────────────
    float PH=0,PL=0,PC=0; SCDateTime prevDate; bool foundPrev=false;
    for (int i=idx-1;i>=0;i--) {
        SCDateTime bd=sc.BaseDateTimeIn[i].GetDate();
        if (!foundPrev&&bd<today){prevDate=bd;foundPrev=true;PC=sc.Close[i];PH=sc.High[i];PL=sc.Low[i];}
        else if(foundPrev&&bd==prevDate){if(sc.High[i]>PH)PH=sc.High[i];if(sc.Low[i]<PL)PL=sc.Low[i];}
        else if(foundPrev) break;
    }
    float PP=0,R1=0,R2=0,S1=0,S2=0;
    if(foundPrev&&PH>0){PP=(PH+PL+PC*2)/4.0f;R1=2*PP-PL;R2=PP+(PH-PL);S1=2*PP-PH;S2=PP-(PH-PL);}

    // ── Woodies CCI ──────────────────────────────────────────
    CCI14[idx]=calcCCI(sc,idx,14); CCI6[idx]=calcCCI(sc,idx,6);
    float cci14=CCI14[idx],cci6=CCI6[idx],cci_diff=cci6-cci14;
    float cci14_prev=(idx>=1)?CCI14[idx-1]:0, cci6_prev=(idx>=1)?CCI6[idx-1]:0;
    const char* cci_trend=(cci14>100)?"TREND_UP":(cci14<-100)?"TREND_DOWN":(cci14>0)?"ABOVE_ZERO":"BELOW_ZERO";
    const char* hist_color="GRAY";
    if(cci14>100&&cci6>100&&cci14>cci14_prev&&cci6>cci6_prev) hist_color="BLUE";
    else if(cci14<-100&&cci6<-100&&cci14<cci14_prev&&cci6<cci6_prev) hist_color="DARK_RED";
    else if(cci14>0&&cci6>0) hist_color="GREEN";
    else if(cci14<0&&cci6<0) hist_color="RED";
    bool turbo_bull=(cci14_prev<=0&&cci14>0&&cci6_prev<=0&&cci6>0);
    bool turbo_bear=(cci14_prev>=0&&cci14<0&&cci6_prev>=0&&cci6<0);
    bool zlr_bull=false,zlr_bear=false;
    if(idx>=2){float p2=CCI14[idx-2],p1=CCI14[idx-1];if(p2>5&&std::fabs(p1)<20&&cci14>p1&&cci14>0)zlr_bull=true;if(p2<-5&&std::fabs(p1)<20&&cci14<p1&&cci14<0)zlr_bear=true;}
    bool hook_up=(cci14>cci14_prev&&cci6>cci6_prev&&cci14<0);
    bool hook_down=(cci14<cci14_prev&&cci6<cci6_prev&&cci14>0);

    // ── Market Profile (Today) ────────────────────────────────
    float SH=sc.High[idx],SL=sc.Low[idx],TV=0; std::map<int,float> pvm;
    for(int i=idx;i>=0;i--){if(sc.BaseDateTimeIn[i].GetDate()<today)break;float bh=sc.High[i],bl=sc.Low[i],bv=sc.Volume[i];if(bh>SH)SH=bh;if(bl<SL)SL=bl;TV+=bv;float vps=bv/((int)((bh-bl)/0.25f)+1);for(float p=bl;p<=bh+0.001f;p+=0.25f)pvm[(int)(p*4)]+=vps;}
    float POC=cp,maxV=0; for(auto&kv:pvm)if(kv.second>maxV){maxV=kv.second;POC=kv.first/4.0f;}
    float vat=TV*(VAPercent.GetFloat()/100),vav=maxV,VAH=POC,VAL=POC;
    auto itu=pvm.upper_bound((int)(POC*4)),itd=pvm.lower_bound((int)(POC*4));
    while(vav<vat){float un=(itu!=pvm.end())?itu->second:0,dn=(itd!=pvm.begin())?std::prev(itd)->second:0;if(un>=dn){if(itu!=pvm.end()){vav+=un;VAH=itu->first/4.0f;++itu;}else break;}else{if(itd!=pvm.begin()){--itd;vav+=itd->second;VAL=itd->first/4.0f;}else break;}}
    float tpo_poc=cp;int tpo_max=0;std::map<int,int>tpo_map;int tpo_back=(idx>=30)?30:idx;
    for(int i=idx-tpo_back;i<=idx;i++)for(float p=sc.Low[i];p<=sc.High[i]+0.001f;p+=0.25f)tpo_map[(int)(p*4)]++;
    for(auto&kv:tpo_map)if(kv.second>tpo_max){tpo_max=kv.second;tpo_poc=kv.first/4.0f;}

    // ── Prev Day POC ──────────────────────────────────────────
    std::map<int,float> prev_pvm; float prev_day_poc=0; bool in_prev=false; SCDateTime prevD;
    for(int i=idx-1;i>=0;i--){SCDateTime bd=sc.BaseDateTimeIn[i].GetDate();if(!in_prev&&bd<today){in_prev=true;prevD=bd;}if(in_prev&&bd==prevD){float bh=sc.High[i],bl=sc.Low[i],bv=sc.Volume[i],vps=bv/((int)((bh-bl)/0.25f)+1);for(float p=bl;p<=bh+0.001f;p+=0.25f)prev_pvm[(int)(p*4)]+=vps;}else if(in_prev&&bd<prevD)break;}
    if(!prev_pvm.empty()){float pmv=0;for(auto&kv:prev_pvm)if(kv.second>pmv){pmv=kv.second;prev_day_poc=kv.first/4.0f;}}

    // ── Session Phase ─────────────────────────────────────────
    const char* phase = getPhase(H, M);
    float sesMin_f=(H*60.0f+M)-(9*60+30); int sesMin=(sesMin_f<0)?-1:(int)sesMin_f;

    // ── Daily Open + Gap ─────────────────────────────────────
    float daily_open=cp; for(int i=idx;i>=0;i--){if(sc.BaseDateTimeIn[i].GetDate()==today)daily_open=sc.Open[i];else break;}
    float gap=daily_open-PC, gap_pct=(PC>0)?(gap/PC*100.0f):0;
    const char* gap_type=(gap>2.0f)?"GAP_UP":(gap<-2.0f)?"GAP_DOWN":"FLAT";

    // ── Overnight H/L ─────────────────────────────────────────
    float ONH=sc.High[idx],ONL=sc.Low[idx];
    for(int i=idx;i>=0;i--){if(sc.BaseDateTimeIn[i].GetDate()<today)break;if(sc.High[i]>ONH)ONH=sc.High[i];if(sc.Low[i]<ONL)ONL=sc.Low[i];}

    // ── 72H / Weekly ─────────────────────────────────────────
    float H72=sc.High[idx],L72=sc.Low[idx],HWk=sc.High[idx],LWk=sc.Low[idx];
    SCDateTime t72=now_dt;t72.SubtractSeconds(72*3600);SCDateTime twk=now_dt;twk.SubtractSeconds((int)twk.GetDayOfWeek()*86400);
    for(int i=idx-1;i>=0;i--){SCDateTime bt=sc.BaseDateTimeIn[i];if(bt>=t72){if(sc.High[i]>H72)H72=sc.High[i];if(sc.Low[i]<L72)L72=sc.Low[i];}if(bt>=twk){if(sc.High[i]>HWk)HWk=sc.High[i];if(sc.Low[i]<LWk)LWk=sc.Low[i];}if(bt<t72&&bt<twk)break;}

    // ── IB + Opening Range ────────────────────────────────────
    int ib_minutes=IBPeriodMin.GetInt();
    float IBH=0,IBL=0; bool ib_locked=false;
    for(int i=idx;i>=0;i--){if(sc.BaseDateTimeIn[i].GetDate()<today)break;int bH=sc.BaseDateTimeIn[i].GetHour(),bM=sc.BaseDateTimeIn[i].GetMinute();float mfo=(bH*60.0f+bM)-(9*60+30);if(mfo<0||mfo>ib_minutes)continue;if(IBH==0||sc.High[i]>IBH)IBH=sc.High[i];if(IBL==0||sc.Low[i]<IBL)IBL=sc.Low[i];}
    float ib_range=(IBH>0&&IBL>0)?(IBH-IBL):0;
    ib_locked=(sesMin>=ib_minutes);
    bool ib_breakout_up=ib_locked&&IBH>0&&cp>IBH;
    bool ib_breakout_down=ib_locked&&IBL>0&&cp<IBL;

    float ORH=0,ORL=0;
    for(int i=idx;i>=0;i--){if(sc.BaseDateTimeIn[i].GetDate()<today)break;int bH=sc.BaseDateTimeIn[i].GetHour(),bM=sc.BaseDateTimeIn[i].GetMinute();float mfo=(bH*60.0f+bM)-(9*60+30);if(mfo<0||mfo>30)continue;if(ORH==0||sc.High[i]>ORH)ORH=sc.High[i];if(ORL==0||sc.Low[i]<ORL)ORL=sc.Low[i];}
    float or_range=(ORH>0&&ORL>0)?(ORH-ORL):0;

    // ── Extension Count + Return to IB ───────────────────────
    int ext_up_count=0, ext_down_count=0;
    bool returned_after_breakout=false, was_outside_ib=false, was_up=false;
    if(ib_locked && IBH>0 && IBL>0) {
        for(int i=0;i<=idx;i++) {
            if(sc.BaseDateTimeIn[i].GetDate()<today) continue;
            int bH2=sc.BaseDateTimeIn[i].GetHour(),bM2=sc.BaseDateTimeIn[i].GetMinute();
            float mfo2=(bH2*60.0f+bM2)-(9*60+30);
            if(mfo2<ib_minutes) continue;
            float bar_c=sc.Close[i];
            bool outside_up=(bar_c>IBH+0.5f), outside_down=(bar_c<IBL-0.5f), inside_ib=(bar_c>=IBL&&bar_c<=IBH);
            if(outside_up&&!was_outside_ib){ext_up_count++;was_outside_ib=true;was_up=true;}
            if(outside_down&&!was_outside_ib){ext_down_count++;was_outside_ib=true;was_up=false;}
            if(inside_ib&&was_outside_ib){returned_after_breakout=true;was_outside_ib=false;}
        }
    }
    int total_extensions=ext_up_count+ext_down_count;

    // ── Day Type ─────────────────────────────────────────────
    const char* day_type="DEVELOPING";
    if(ib_locked && IBH>0) {
        if(ib_range<6.0f&&total_extensions==0) day_type="BALANCED";
        else if(total_extensions>=2&&!returned_after_breakout) day_type="TRENDING";
        else if(total_extensions>=1&&!returned_after_breakout) day_type="NORMAL_TRENDING";
        else if(total_extensions>=1&&returned_after_breakout) day_type="NORMAL";
        else if(ib_range>15.0f) day_type="VOLATILE";
        else day_type="BALANCED";
    }

    // ── Relative Volume ──────────────────────────────────────
    float avg_vol_20=0; int vc=0;
    for(int i=idx-1;i>=idx-20&&i>=0;i--){avg_vol_20+=sc.Volume[i];vc++;}
    if(vc>0)avg_vol_20/=vc;
    float rel_vol=(avg_vol_20>0)?(sc.Volume[idx]/avg_vol_20):1.0f;
    const char* vol_ctx=(rel_vol>2.0f)?"VERY_HIGH":(rel_vol>1.5f)?"HIGH":(rel_vol<0.5f)?"VERY_LOW":(rel_vol<0.8f)?"LOW":"NORMAL";

    // ── Order Flow ────────────────────────────────────────────
    bool absorption_bull=false;
    if(idx>=3){float sp=0;for(int i=idx-2;i<=idx;i++)sp+=sc.BidVolume[i];if(sp>500&&(cp-sc.Close[idx-3])>=0)absorption_bull=true;}
    bool liq_sweep_long=false,liq_sweep_short=false;
    if(idx>=3){bool bl2=(sc.Low[idx-1]<SL-1.0f||sc.Low[idx-2]<SL-1.0f);if(bl2&&(cp>SL+0.5f)&&delta>0)liq_sweep_long=true;bool bh2=(sc.High[idx-1]>SH+1.0f||sc.High[idx-2]>SH+1.0f);if(bh2&&(cp<SH-0.5f)&&delta<0)liq_sweep_short=true;}

    float imb_ratio=ImbalanceRatio.GetFloat();
    struct ImbLevel{float price,buy_vol,sell_vol,ratio;};
    std::vector<ImbLevel> imbalances;
    int imb_lb=(idx>=5)?5:idx;
    for(int i=idx-imb_lb;i<=idx;i++){if(i<0)continue;float bv=sc.AskVolume[i],sv=sc.BidVolume[i],dom=(sc.High[i]+sc.Low[i])/2.0f;if(sc.High[i]-sc.Low[i]<0.5f)continue;if(sv>0&&bv/sv>=imb_ratio)imbalances.push_back({dom,bv,sv,bv/sv});else if(bv>0&&sv/bv>=imb_ratio)imbalances.push_back({dom,bv,sv,-(sv/bv)});}
    std::sort(imbalances.begin(),imbalances.end(),[](const ImbLevel&a,const ImbLevel&b){return std::fabs(a.ratio)>std::fabs(b.ratio);});
    int imb_count=(int)imbalances.size();if(imb_count>3)imb_count=3;

    // ── Footprint Booleans (A8) — price-level analysis ───────
    bool fp_absorption = false;
    bool fp_exhaustion = false;
    bool fp_trapped_buyers = false;
    int  fp_stacked_count = 0;
    const char* fp_stacked_dir = "NONE";
    bool fp_pullback_delta_declining = false;
    bool fp_pullback_aggressive_buy  = false;
    bool fp_pullback_aggressive_sell = false;

    {
        float tick_sz = sc.TickSize;  // MES = 0.25
        if (tick_sz < 0.01f) tick_sz = 0.25f;
        int vap_size = sc.VolumeAtPriceForBars->GetSizeAtBarIndex(idx);

        // ── 1. Absorption + 2. Exhaustion — scan extreme ticks of current bar ──
        if (vap_size > 0)
        {
            // Find top 3 and bottom 3 price levels
            float bar_hi = sc.High[idx], bar_lo = sc.Low[idx];
            unsigned int top_ask = 0, top_bid = 0, top_vol = 0;
            unsigned int bot_ask = 0, bot_bid = 0, bot_vol = 0;

            for (int v = 0; v < vap_size; v++)
            {
                const s_VolumeAtPriceV2 *vap = NULL;
                if (!sc.VolumeAtPriceForBars->GetVAPElementAtIndex(idx, v, &vap)) continue;
                if (vap == NULL) continue;
                float px = vap->PriceInTicks * tick_sz;

                // Top 3 ticks (near high)
                if (px >= bar_hi - tick_sz * 2.5f)
                {
                    top_ask += vap->AskVolume;
                    top_bid += vap->BidVolume;
                    top_vol += vap->Volume;
                }
                // Bottom 3 ticks (near low)
                if (px <= bar_lo + tick_sz * 2.5f)
                {
                    bot_ask += vap->AskVolume;
                    bot_bid += vap->BidVolume;
                    bot_vol += vap->Volume;
                }
            }

            // Absorption: huge opposing volume at extreme but price rejected
            // At high: big AskVol (buyers) but close < high → buyers absorbed by hidden sellers
            if (top_ask > 50 && cp < bar_hi - tick_sz && top_ask > top_bid * 2)
                fp_absorption = true;
            // At low: big BidVol (sellers) but close > low → sellers absorbed by hidden buyers
            if (bot_bid > 50 && cp > bar_lo + tick_sz && bot_bid > bot_ask * 2)
                fp_absorption = true;

            // Exhaustion: < 5 contracts at extreme tick → Zero Print
            if (top_vol > 0 && top_vol < 5) fp_exhaustion = true;
            if (bot_vol > 0 && bot_vol < 5) fp_exhaustion = true;
        }

        // ── 3. Trapped Buyers — broke above recent high then reversed ──
        if (idx >= 3)
        {
            float prev_hi = sc.High[idx-1];
            for (int i = idx-2; i >= idx-3 && i >= 0; i--)
                if (sc.High[i] > prev_hi) prev_hi = sc.High[i];
            // Broke above then closed below open = trapped buyers
            if (sc.High[idx] > prev_hi + 0.5f && cp < sc.Open[idx])
                fp_trapped_buyers = true;
        }

        // ── 4-5. Stacked Imbalances — consecutive price levels ×250% ──
        if (vap_size >= 3)
        {
            int consec_bull = 0, consec_bear = 0;
            int max_bull = 0, max_bear = 0;
            const float STACK_RATIO = 2.5f;  // 250%

            for (int v = 0; v < vap_size; v++)
            {
                const s_VolumeAtPriceV2 *vap = NULL;
                if (!sc.VolumeAtPriceForBars->GetVAPElementAtIndex(idx, v, &vap)) continue;
                if (vap == NULL) continue;
                unsigned int av = vap->AskVolume, bv = vap->BidVolume;

                bool bull_imb = (bv > 0 && (float)av / bv >= STACK_RATIO);
                bool bear_imb = (av > 0 && (float)bv / av >= STACK_RATIO);

                if (bull_imb) { consec_bull++; if (consec_bull > max_bull) max_bull = consec_bull; }
                else consec_bull = 0;

                if (bear_imb) { consec_bear++; if (consec_bear > max_bear) max_bear = consec_bear; }
                else consec_bear = 0;
            }

            if (max_bull >= 2 || max_bear >= 2)
            {
                fp_stacked_count = (max_bull >= max_bear) ? max_bull : max_bear;
                if (fp_stacked_count > 10) fp_stacked_count = 10;
                fp_stacked_dir = (max_bull >= max_bear) ? "LONG" : "SHORT";
            }
        }

        // ── 6. Pullback Delta Declining — delta shrinking over last 3 bars ��─
        if (idx >= 3)
        {
            float d0 = sc.AskVolume[idx]   - sc.BidVolume[idx];
            float d1 = sc.AskVolume[idx-1] - sc.BidVolume[idx-1];
            float d2 = sc.AskVolume[idx-2] - sc.BidVolume[idx-2];
            // Absolute delta declining = momentum fading
            if (std::fabs(d0) < std::fabs(d1) && std::fabs(d1) < std::fabs(d2))
                fp_pullback_delta_declining = true;
        }

        // ── 7. Pullback Aggressive Buy — strong +delta during price dip ──
        if (idx >= 3)
        {
            bool price_dipping = (cp < sc.Close[idx-3]);
            bool price_rising  = (cp > sc.Close[idx-3]);
            float recent_delta = delta;
            for (int i = idx-1; i >= idx-2 && i >= 0; i--)
                recent_delta += sc.AskVolume[i] - sc.BidVolume[i];
            if (price_dipping && recent_delta > 100)
                fp_pullback_aggressive_buy = true;
            // ── 7b. Pullback Aggressive Sell — strong -delta during price rise ──
            if (price_rising && recent_delta < -100)
                fp_pullback_aggressive_sell = true;
        }
    }

    // ── Candle Patterns ───────────────��───────────────────────
    const char* pat0=detectCandlePattern(sc.Open[idx],sc.High[idx],sc.Low[idx],sc.Close[idx]);
    const char* pat1=(idx>=1)?detectCandlePattern(sc.Open[idx-1],sc.High[idx-1],sc.Low[idx-1],sc.Close[idx-1]):"NONE";
    const char* pat2=(idx>=2)?detectCandlePattern(sc.Open[idx-2],sc.High[idx-2],sc.Low[idx-2],sc.Close[idx-2]):"NONE";
    bool bull_engulf=(idx>=1)&&(sc.Close[idx]>sc.Open[idx-1])&&(sc.Open[idx]<sc.Close[idx-1])&&(sc.Close[idx-1]<sc.Open[idx-1]);
    bool bear_engulf=(idx>=1)&&(sc.Close[idx]<sc.Open[idx-1])&&(sc.Open[idx]>sc.Close[idx-1])&&(sc.Close[idx-1]>sc.Open[idx-1]);

    // ── MTF — מיושר לגבולות זמן אמיתיים ──────────────────────
    struct MTFBar{float o,h,l,c,vol,buy,sell,delta_v; long long bar_ts;};
    auto calcBarAligned=[&](int interval_sec)->MTFBar{
        MTFBar b={0,0,999999,0,0,0,0,0,0};
        long long now_ts = ToUnixTime(sc.BaseDateTimeIn[idx]);
        long long bar_start = (now_ts / interval_sec) * interval_sec;
        b.bar_ts = bar_start;
        b.c = sc.Close[idx];
        bool first = true;
        for(int i=idx;i>=0;i--){
            long long bts = ToUnixTime(sc.BaseDateTimeIn[i]);
            if(bts < bar_start) break;
            b.o = sc.Open[i];
            if(first){b.h=sc.High[i];b.l=sc.Low[i];first=false;}
            if(sc.High[i]>b.h)b.h=sc.High[i];
            if(sc.Low[i]<b.l)b.l=sc.Low[i];
            b.vol+=sc.Volume[i];b.buy+=sc.AskVolume[i];b.sell+=sc.BidVolume[i];
        }
        b.delta_v=b.buy-b.sell;return b;
    };
    MTFBar m3=calcBarAligned(180),m5=calcBarAligned(300),m15=calcBarAligned(900),m30=calcBarAligned(1800),m60=calcBarAligned(3600);

    // ── Footprint — נרות אחרונים (bar-level) ──────────────────
    std::ostringstream fp_j;
    fp_j << std::fixed << std::setprecision(2);
    fp_j << "[";
    int fp_count = FootprintBars.GetInt();
    if (fp_count < 10) fp_count = 10;
    if (fp_count > 960) fp_count = 960;
    int fp_start = (idx >= fp_count - 1) ? idx - (fp_count - 1) : 0;
    for (int bi = fp_start; bi <= idx; bi++) {
        if (bi > fp_start) fp_j << ",";
        fp_j << "{\"ts\":"    << ToUnixTime(sc.BaseDateTimeIn[bi])
             << ",\"o\":"     << sc.Open[bi]
             << ",\"h\":"     << sc.High[bi]
             << ",\"l\":"     << sc.Low[bi]
             << ",\"c\":"     << sc.Close[bi]
             << ",\"buy\":"   << sc.AskVolume[bi]
             << ",\"sell\":"  << sc.BidVolume[bi]
             << ",\"delta\":" << (sc.AskVolume[bi] - sc.BidVolume[bi])
             << "}";
    }
    fp_j << "]";

    // ── Order Fills ───────────────────────────────────────────
    std::ostringstream fills_j;
    fills_j << std::fixed << std::setprecision(2);
    fills_j << "[";
    bool fills_first = true;
    int fill_count = sc.GetOrderFillArraySize();
    int fill_start = (fill_count > 20) ? fill_count - 20 : 0;
    for (int f = fill_start; f < fill_count; f++) {
        s_SCOrderFillData fill;
        sc.GetOrderFillEntry(f, fill);
        if (!fills_first) fills_j << ",";
        fills_first = false;
        fills_j << "{\"price\":"  << fill.FillPrice
                << ",\"qty\":"   << fill.Quantity
                << ",\"side\":\"" << (fill.BuySell == BSE_BUY ? "BUY" : "SELL") << "\""
                << ",\"ts\":"    << ToUnixTime(fill.FillDateTime)
                << ",\"pos\":"   << fill.TradePositionQuantity
                << "}";
    }
    fills_j << "]";

    // ── HistoryInit — שולח 960 נרות + MTF היסטוריה פעם אחת בטעינה ──
    if (sc.IsFullRecalculation && idx == sc.ArraySize - 1)
    {
        int hist_count = (sc.ArraySize >= 960) ? 960 : sc.ArraySize;
        int hist_start = sc.ArraySize - hist_count;

        // ── 3m history (existing) ──
        std::ostringstream hj;
        hj << std::fixed << std::setprecision(2);
        hj << "{\"candles\":[";

        for (int i = hist_start; i < sc.ArraySize; i++) {
            if (i > hist_start) hj << ",";
            int bH2 = sc.BaseDateTimeIn[i].GetHour();
            int bM2 = sc.BaseDateTimeIn[i].GetMinute();
            hj << "{"
               << "\"ts\":"    << ToUnixTime(sc.BaseDateTimeIn[i])
               << ",\"o\":"    << sc.Open[i]
               << ",\"h\":"    << sc.High[i]
               << ",\"l\":"    << sc.Low[i]
               << ",\"c\":"    << sc.Close[i]
               << ",\"buy\":"  << sc.AskVolume[i]
               << ",\"sell\":" << sc.BidVolume[i]
               << ",\"vol\":"  << sc.Volume[i]
               << ",\"delta\":" << (sc.AskVolume[i] - sc.BidVolume[i])
               << ",\"cci14\":" << CCI14[i]
               << ",\"cci6\":"  << CCI6[i]
               << ",\"vwap\":"  << VWAP[i]
               << ",\"phase\":\"" << getPhase(bH2, bM2) << "\""
               << ",\"above_vwap\":" << (sc.Close[i] > VWAP[i] ? "true" : "false")
               << "}";
        }
        hj << "],";

        // ── MTF history — aggregate 3m bars into 5m/15m/30m/1h ──
        struct MTFHist { long long ts; float o,h,l,c,vol,buy,sell; };
        auto buildMTF = [&](int interval_sec, int max_bars) -> std::vector<MTFHist> {
            std::map<long long, MTFHist> buckets;
            for (int i = hist_start; i < sc.ArraySize; i++) {
                long long bts = ToUnixTime(sc.BaseDateTimeIn[i]);
                if (bts <= 0) continue;
                long long bucket = (bts / interval_sec) * interval_sec;
                auto it = buckets.find(bucket);
                if (it == buckets.end()) {
                    MTFHist bar;
                    bar.ts = bucket;
                    bar.o = sc.Open[i]; bar.h = sc.High[i]; bar.l = sc.Low[i]; bar.c = sc.Close[i];
                    bar.vol = sc.Volume[i]; bar.buy = sc.AskVolume[i]; bar.sell = sc.BidVolume[i];
                    buckets[bucket] = bar;
                } else {
                    MTFHist &bar = it->second;
                    if (sc.High[i] > bar.h) bar.h = sc.High[i];
                    if (sc.Low[i] < bar.l) bar.l = sc.Low[i];
                    bar.c = sc.Close[i];
                    bar.vol += sc.Volume[i]; bar.buy += sc.AskVolume[i]; bar.sell += sc.BidVolume[i];
                }
            }
            // Sort by ts, take last max_bars
            std::vector<MTFHist> result;
            for (auto &kv : buckets) result.push_back(kv.second);
            // std::map already sorted by key (ts), so result is sorted
            if ((int)result.size() > max_bars)
                result.erase(result.begin(), result.begin() + (result.size() - max_bars));
            return result;
        };

        auto writeMTFArray = [&](std::ostringstream &out, const std::vector<MTFHist> &bars) {
            out << "[";
            for (int i = 0; i < (int)bars.size(); i++) {
                if (i > 0) out << ",";
                const MTFHist &b = bars[i];
                out << "{\"ts\":" << b.ts
                    << ",\"open\":" << b.o << ",\"high\":" << b.h
                    << ",\"low\":" << b.l << ",\"close\":" << b.c
                    << ",\"vol\":" << b.vol << ",\"buy\":" << b.buy
                    << ",\"sell\":" << b.sell << ",\"delta\":" << (b.buy - b.sell)
                    << "}";
            }
            out << "]";
        };

        auto m5h  = buildMTF(300,  288);
        auto m15h = buildMTF(900,  96);
        auto m30h = buildMTF(1800, 48);
        auto m60h = buildMTF(3600, 64);

        hj << "\"mtf_history\":{\"m5\":";
        writeMTFArray(hj, m5h);
        hj << ",\"m15\":";
        writeMTFArray(hj, m15h);
        hj << ",\"m30\":";
        writeMTFArray(hj, m30h);
        hj << ",\"m60\":";
        writeMTFArray(hj, m60h);
        hj << "}}";

        std::ofstream hf(HistoryPath.GetString());
        if (hf.is_open()) { hf << hj.str(); hf.close(); }
    }

    // ── Throttle ─────────────────────────────────────────────
    static time_t lastExport=0; time_t now_t=time(nullptr);
    if((now_t-lastExport)<ExportIntervalSec.GetInt())return;
    lastExport=now_t;

    // ── JSON ──────────────────────────────────────────────────
    std::ostringstream j; j<<std::fixed<<std::setprecision(2);
    j<<"{"
     <<"\"timestamp\":"<<(long long)now_t
     <<",\"symbol\":\"MEMS26\""
     <<",\"current_price\":"<<cp
     <<",\"session_phase\":\""<<phase<<"\""
     <<",\"session_min\":"<<sesMin
     <<",\"cvd\":{\"current\":"<<CVD[idx]<<",\"change_20bar\":"<<cvd20<<",\"change_5bar\":"<<cvd5<<",\"trend\":\""<<(cvd20>100?"BULLISH":cvd20<-100?"BEARISH":"NEUTRAL")<<"\",\"buy_vol\":"<<ask_vol<<",\"sell_vol\":"<<bid_vol<<",\"delta\":"<<delta<<"}"
     <<",\"vwap\":{\"value\":"<<vwap<<",\"distance\":"<<vwap_dist<<",\"above\":"<<(above_vwap?"true":"false")<<",\"pullback\":"<<(vwap_pullback?"true":"false")<<"}"
     <<",\"woodies_cci\":{\"cci14\":"<<cci14<<",\"cci6\":"<<cci6<<",\"cci_diff\":"<<cci_diff<<",\"trend\":\""<<cci_trend<<"\",\"hist_color\":\""<<hist_color<<"\",\"turbo_bull\":"<<(turbo_bull?"true":"false")<<",\"turbo_bear\":"<<(turbo_bear?"true":"false")<<",\"zlr_bull\":"<<(zlr_bull?"true":"false")<<",\"zlr_bear\":"<<(zlr_bear?"true":"false")<<",\"hook_up\":"<<(hook_up?"true":"false")<<",\"hook_down\":"<<(hook_down?"true":"false")<<"}"
     <<",\"market_profile\":{\"poc\":"<<POC<<",\"vah\":"<<VAH<<",\"val\":"<<VAL<<",\"session_high\":"<<SH<<",\"session_low\":"<<SL<<",\"tpo_poc\":"<<tpo_poc<<",\"prev_day_poc\":"<<prev_day_poc<<",\"in_value_area\":"<<(cp>=VAL&&cp<=VAH?"true":"false")<<",\"above_poc\":"<<(cp>POC?"true":"false")<<"}"
     <<",\"day_context\":{\"day_type\":\""<<day_type<<"\",\"ib_high\":"<<IBH<<",\"ib_low\":"<<IBL<<",\"ib_range\":"<<ib_range<<",\"ib_locked\":"<<(ib_locked?"true":"false")<<",\"ib_breakout_up\":"<<(ib_breakout_up?"true":"false")<<",\"ib_breakout_down\":"<<(ib_breakout_down?"true":"false")<<",\"or_high\":"<<ORH<<",\"or_low\":"<<ORL<<",\"or_range\":"<<or_range<<",\"gap\":"<<gap<<",\"gap_pct\":"<<gap_pct<<",\"gap_type\":\""<<gap_type<<"\",\"ext_up\":"<<ext_up_count<<",\"ext_down\":"<<ext_down_count<<",\"total_ext\":"<<total_extensions<<",\"returned_after_break\":"<<(returned_after_breakout?"true":"false")<<"}"
     <<",\"volume_context\":{\"current_vol\":"<<sc.Volume[idx]<<",\"avg_vol_20\":"<<avg_vol_20<<",\"rel_vol\":"<<rel_vol<<",\"context\":\""<<vol_ctx<<"\"}"
     <<",\"candle_patterns\":{\"bar0\":\""<<pat0<<"\",\"bar1\":\""<<pat1<<"\",\"bar2\":\""<<pat2<<"\",\"bull_engulf\":"<<(bull_engulf?"true":"false")<<",\"bear_engulf\":"<<(bear_engulf?"true":"false")<<"}"
     <<",\"woodi_pivots\":{\"pp\":"<<PP<<",\"r1\":"<<R1<<",\"r2\":"<<R2<<",\"s1\":"<<S1<<",\"s2\":"<<S2<<",\"above_pp\":"<<(cp>PP?"true":"false")<<"}"
     <<",\"time_levels\":{\"weekly_high\":"<<HWk<<",\"weekly_low\":"<<LWk<<",\"h72_high\":"<<H72<<",\"h72_low\":"<<L72<<",\"prev_high\":"<<PH<<",\"prev_low\":"<<PL<<",\"prev_close\":"<<PC<<",\"daily_open\":"<<daily_open<<",\"overnight_high\":"<<ONH<<",\"overnight_low\":"<<ONL<<"}"
     <<",\"order_flow\":{\"absorption_bull\":"<<(absorption_bull?"true":"false")<<",\"liq_sweep_long\":"<<(liq_sweep_long?"true":"false")<<",\"liq_sweep_short\":"<<(liq_sweep_short?"true":"false")<<",\"imbalances\":[";
    for(int i=0;i<imb_count;i++){if(i>0)j<<",";j<<"{\"price\":"<<imbalances[i].price<<",\"buy\":"<<imbalances[i].buy_vol<<",\"sell\":"<<imbalances[i].sell_vol<<",\"ratio\":"<<imbalances[i].ratio<<"}";}
    j<<"]}"
     <<",\"footprint_bools\":{\"absorption_detected\":"<<(fp_absorption?"true":"false")
        <<",\"exhaustion_detected\":"<<(fp_exhaustion?"true":"false")
        <<",\"trapped_buyers\":"<<(fp_trapped_buyers?"true":"false")
        <<",\"stacked_imbalance_count\":"<<fp_stacked_count
        <<",\"stacked_imbalance_dir\":\""<<fp_stacked_dir<<"\""
        <<",\"pullback_delta_declining\":"<<(fp_pullback_delta_declining?"true":"false")
        <<",\"pullback_aggressive_buy\":"<<(fp_pullback_aggressive_buy?"true":"false")
        <<",\"pullback_aggressive_sell\":"<<(fp_pullback_aggressive_sell?"true":"false")<<"}"
     <<",\"mtf\":{"
        <<"\"m3\":{\"ts\":"<<m3.bar_ts<<",\"o\":"<<m3.o<<",\"h\":"<<m3.h<<",\"l\":"<<m3.l<<",\"c\":"<<m3.c<<",\"vol\":"<<m3.vol<<",\"buy\":"<<m3.buy<<",\"sell\":"<<m3.sell<<",\"delta\":"<<m3.delta_v<<"}"
        <<",\"m5\":{\"ts\":"<<m5.bar_ts<<",\"o\":"<<m5.o<<",\"h\":"<<m5.h<<",\"l\":"<<m5.l<<",\"c\":"<<m5.c<<",\"vol\":"<<m5.vol<<",\"buy\":"<<m5.buy<<",\"sell\":"<<m5.sell<<",\"delta\":"<<m5.delta_v<<"}"
        <<",\"m15\":{\"ts\":"<<m15.bar_ts<<",\"o\":"<<m15.o<<",\"h\":"<<m15.h<<",\"l\":"<<m15.l<<",\"c\":"<<m15.c<<",\"vol\":"<<m15.vol<<",\"buy\":"<<m15.buy<<",\"sell\":"<<m15.sell<<",\"delta\":"<<m15.delta_v<<"}"
        <<",\"m30\":{\"ts\":"<<m30.bar_ts<<",\"o\":"<<m30.o<<",\"h\":"<<m30.h<<",\"l\":"<<m30.l<<",\"c\":"<<m30.c<<",\"vol\":"<<m30.vol<<",\"buy\":"<<m30.buy<<",\"sell\":"<<m30.sell<<",\"delta\":"<<m30.delta_v<<"}"
        <<",\"m60\":{\"ts\":"<<m60.bar_ts<<",\"o\":"<<m60.o<<",\"h\":"<<m60.h<<",\"l\":"<<m60.l<<",\"c\":"<<m60.c<<",\"vol\":"<<m60.vol<<",\"buy\":"<<m60.buy<<",\"sell\":"<<m60.sell<<",\"delta\":"<<m60.delta_v<<"}}"
     <<",\"footprint\":"<<fp_j.str()
     <<",\"order_fills\":"<<fills_j.str()
     <<"}\n";

    std::ofstream f(ExportPath.GetString());
    if(f.is_open()){f<<j.str();f.close();}

    // ── C5: Trade Command Execution ──────────────────────────────────────
    // Poll trade_command.json every second, verify checksum, execute bracket
    {
        static time_t s_lastCmdCheck = 0;
        static std::string s_lastTradeId;
        time_t now_c = time(nullptr);
        if (now_c - s_lastCmdCheck < 1) goto c5_done;
        s_lastCmdCheck = now_c;

        std::ifstream cf(CommandPath.GetString());
        if (!cf.is_open()) goto c5_done;
        std::string cmdJson((std::istreambuf_iterator<char>(cf)),
                             std::istreambuf_iterator<char>());
        cf.close();
        if (cmdJson.size() < 10) goto c5_done;

        std::string cmd      = jsonStr(cmdJson, "cmd");
        double cmdPrice      = jsonNum(cmdJson, "price");
        int    cmdQty        = (int)jsonNum(cmdJson, "qty");
        double cmdStop       = jsonNum(cmdJson, "stop");
        double cmdT1         = jsonNum(cmdJson, "t1");
        double cmdT2         = jsonNum(cmdJson, "t2");
        double cmdT3         = jsonNum(cmdJson, "t3");
        std::string tradeId  = jsonStr(cmdJson, "trade_id");
        long long expiresAt  = jsonInt(cmdJson, "expires_at");
        std::string checksum = jsonStr(cmdJson, "checksum");

        // Skip if same trade_id (already processed)
        if (tradeId == s_lastTradeId) goto c5_done;

        // TTL check — 60 seconds
        if (expiresAt > 0 && (long long)now_c > expiresAt) {
            sc.AddMessageToLog("C5: Command expired — skipping", 1);
            s_lastTradeId = tradeId;
            goto c5_done;
        }

        // Verify SHA-256 checksum
        {
            std::ostringstream raw;
            raw << std::fixed << std::setprecision(2);
            raw << cmd << ":" << cmdPrice << ":" << cmdQty << ":"
                << cmdStop << ":" << tradeId << ":" << expiresAt
                << ":" << BridgeToken.GetString();
            std::string computed = sha256hex(raw.str());
            if (computed != checksum) {
                sc.AddMessageToLog("C5: CHECKSUM MISMATCH — ignoring", 1);
                s_lastTradeId = tradeId;
                goto c5_done;
            }
        }

        s_lastTradeId = tradeId;

        // Write result helper
        auto writeResult = [&](const char* status, const char* detail, int orderId) {
            std::ostringstream rj;
            rj << std::fixed << std::setprecision(2);
            rj << "{\"trade_id\":\"" << tradeId << "\""
               << ",\"status\":\"" << status << "\""
               << ",\"detail\":\"" << detail << "\""
               << ",\"order_id\":" << orderId
               << ",\"ts\":" << (long long)now_c
               << ",\"price\":" << cp
               << "}";
            std::ofstream rf(ResultPath.GetString());
            if (rf.is_open()) { rf << rj.str(); rf.close(); }
        };

        // Debug: log raw command content
        sc.AddMessageToLog(SCString().Format(
            "C5: trade_command file size=%d bytes, first 200 chars: %.200s",
            (int)cmdJson.length(), cmdJson.c_str()), 1);

        // ── CANCEL ──
        if (cmd == "CANCEL") {
            sc.CancelAllOrders();
            sc.FlattenAndCancelAllOrders();
            writeResult("OK", "CANCEL executed", 0);
            sc.AddMessageToLog("C5: CANCEL — canceled + flattened all", 0);
            goto c5_done;
        }

        // ── CLOSE ── V6.8: clean close from Backend
        if (cmd == "CLOSE") {
            sc.AddMessageToLog("C5: CLOSE command received", 1);
            sc.CancelAllOrders();
            sc.FlattenAndCancelAllOrders();
            writeResult("OK", "CLOSE complete", 0);
            sc.AddMessageToLog("C5: CLOSE complete (canceled + flattened)", 1);
            goto c5_done;
        }

        // ── SCALE_OUT — disabled in V7.6.2 (safe no-op) ──
        // V7.2-V7.5 all had fatal issues (SellExit error, CancelOrder
        // error, ModifyOrder froze Sierra). V7.6 MoveToBreakEven makes
        // runtime SCALE_OUT obsolete.
        if (cmd == "SCALE_OUT") {
            std::string contract = jsonStr(cmdJson, "contract");
            sc.AddMessageToLog(SCString().Format(
                "C5: SCALE_OUT ignored (DLL %s) — contract=%s — "
                "obsolete: auto-breakeven handles stop management",
                MEMS26_DLL_VERSION, contract.c_str()), 1);
            writeResult("OK", "SCALE_OUT ignored (V7.6.2)", 0);
            goto c5_done;
        }

        // ── BUY / SELL — Bracket Order ──
        if (cmd != "BUY" && cmd != "SELL") {
            writeResult("ERROR", "Unknown cmd", 0);
            goto c5_done;
        }

        // Validate
        if (cmdPrice <= 0 || cmdStop <= 0 || cmdQty <= 0 || cmdQty > 3) {
            writeResult("ERROR", "Invalid price/stop/qty", 0);
            goto c5_done;
        }
        if (std::fabs(cmdPrice - cmdStop) > 8.0) {
            writeResult("ERROR", "Risk > 8pt", 0);
            goto c5_done;
        }

        // V6.8: Strict brackets[] parser with debug logging
        {
            struct BracketSpec { std::string id; int qty; double target; };
            std::vector<BracketSpec> brackets;

            size_t bKey = cmdJson.find("\"brackets\"");
            if (bKey != std::string::npos) {
                size_t aS = cmdJson.find('[', bKey);
                size_t aE = cmdJson.find(']', aS);
                if (aS != std::string::npos && aE != std::string::npos) {
                    std::string arr = cmdJson.substr(aS + 1, aE - aS - 1);
                    size_t pos = 0;
                    while (brackets.size() < 3) {
                        size_t oS = arr.find('{', pos);
                        if (oS == std::string::npos) break;
                        size_t oE = arr.find('}', oS);
                        if (oE == std::string::npos) break;
                        std::string obj = arr.substr(oS, oE - oS + 1);
                        BracketSpec b;
                        b.id = jsonStr(obj, "id");
                        b.qty = (int)jsonNum(obj, "qty");
                        b.target = jsonNum(obj, "target");
                        brackets.push_back(b);
                        sc.AddMessageToLog(SCString().Format(
                            "C5: parsed bracket: id=%s qty=%d target=%.2f",
                            b.id.c_str(), b.qty, b.target), 1);
                        pos = oE + 1;
                    }
                }
            }

            sc.AddMessageToLog(SCString().Format(
                "C5: parsed %d brackets from JSON", (int)brackets.size()), 1);

            if (brackets.size() == 3) {
                // V7.0: Single BuyEntry with 3 attached targets + shared stop
                // Per Sierra Engineering (ThreadID=105021), this is the native
                // pattern for partial scale-out brackets.

                // Sort by target distance: nearest first for LONG, farthest for SHORT
                std::sort(brackets.begin(), brackets.end(),
                    [&](const BracketSpec& a, const BracketSpec& b) {
                        return (cmd == "BUY") ? a.target < b.target : a.target > b.target;
                    });

                s_SCNewOrder NewOrder;
                NewOrder.OrderQuantity = 3;
                NewOrder.OrderType = SCT_ORDERTYPE_MARKET;
                NewOrder.TextTag = "MEMS26_PARENT";
                NewOrder.Target1Price = (float)brackets[0].target;
                NewOrder.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
                NewOrder.OCOGroup1Quantity = 1;
                NewOrder.Target2Price = (float)brackets[1].target;
                NewOrder.AttachedOrderTarget2Type = SCT_ORDERTYPE_LIMIT;
                NewOrder.OCOGroup2Quantity = 1;
                NewOrder.Target3Price = (float)brackets[2].target;
                NewOrder.AttachedOrderTarget3Type = SCT_ORDERTYPE_LIMIT;
                NewOrder.OCOGroup3Quantity = 1;
                // V7.6.3: Separate stops per OCO group so MoveToBreakEven
                // can move C2/C3 stops when C1 fills (requires "different group")
                NewOrder.Stop1Price = (float)cmdStop;
                NewOrder.AttachedOrderStop1Type = SCT_ORDERTYPE_STOP;
                NewOrder.Stop2Price = (float)cmdStop;
                NewOrder.AttachedOrderStop2Type = SCT_ORDERTYPE_STOP;
                NewOrder.Stop3Price = (float)cmdStop;
                NewOrder.AttachedOrderStop3Type = SCT_ORDERTYPE_STOP;

                // V7.6: When C1 fills, auto-move StopAll to entry (breakeven)
                NewOrder.MoveToBreakEven.Type = MOVETO_BE_ACTION_TYPE_OCO_GROUP_TRIGGERED;
                NewOrder.MoveToBreakEven.BreakEvenLevelOffsetInTicks = 0;
                NewOrder.MoveToBreakEven.TriggerOCOGroup = OCO_GROUP_1;

                sc.AddMessageToLog(SCString().Format(
                    "C5: %s 3-target bracket dispatch (DLL %s) — T1=%.2f T2=%.2f T3=%.2f stopAll=%.2f qty=3",
                    cmd.c_str(), MEMS26_DLL_VERSION,
                    brackets[0].target, brackets[1].target,
                    brackets[2].target, cmdStop), 1);

                int Result = (cmd == "BUY")
                    ? (int)sc.BuyEntry(NewOrder) : (int)sc.SellEntry(NewOrder);

                sc.AddMessageToLog(SCString().Format(
                    "C5: bracket dispatch Result=%d", Result), 1);
                if (Result > 0) {
                    s_lastTradeId = tradeId;
                    // V7.7.1c: Persist trade_id to file for position monitoring
                    { std::string dp(ExportPath.GetString());
                      size_t s = dp.rfind('/'); if (s == std::string::npos) s = dp.rfind('\\');
                      if (s != std::string::npos) {
                          std::ofstream idf(dp.substr(0, s+1) + "mems26_current_trade_id.txt");
                          if (idf.is_open()) { idf << tradeId; idf.close(); }
                      }
                    }
                    writeResult("OK", "1 bracket with 3 targets accepted", Result);
                    sc.AddMessageToLog(
                        "C5: dispatch complete: 1 bracket with 3 targets accepted", 1);
                    sc.AddMessageToLog(
                        "C5: V7.6 MoveToBreakEven armed — C1 fill → StopAll → entry", 1);
                } else {
                    writeResult("ERROR", "bracket rejected", Result);
                    sc.AddMessageToLog(SCString().Format(
                        "C5: ERROR bracket rejected: %d", Result), 1);
                }
            } else {
                // V6.8: replaced by strict parser above — kept for reference
                sc.AddMessageToLog(SCString().Format(
                    "C5: ERROR expected 3 brackets, got %d — using legacy fallback",
                    (int)brackets.size()), 1);
                s_SCNewOrder order;
                order.OrderQuantity = cmdQty;
                order.TimeInForce = SCT_TIF_GTC;
                order.OrderType = SCT_ORDERTYPE_MARKET;
                order.AttachedOrderStop1Type = SCT_ORDERTYPE_STOP;
                order.Stop1Price = (float)cmdStop;
                if (cmdT1 > 0) {
                    order.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
                    order.Target1Price = (float)cmdT1;
                }
                int result = (cmd == "BUY")
                    ? (int)sc.BuyEntry(order) : (int)sc.SellEntry(order);
                if (result > 0) {
                    SCString msg;
                    msg.Format("C5: LEGACY %s %d @ %.2f stop=%.2f t1=%.2f",
                               cmd.c_str(), cmdQty, cmdPrice, cmdStop, cmdT1);
                    writeResult("OK", msg.GetChars(), result);
                    sc.AddMessageToLog(msg, 0);
                } else {
                    writeResult("ERROR", "Entry failed", result);
                    sc.AddMessageToLog(SCString().Format(
                        "C5: LEGACY %s FAILED result=%d", cmd.c_str(), result), 1);
                }
            }
        }
    }
    c5_done:;

    // V7.7.1c: POSITION CHANGE DETECTION (runs every update interval)
    {
        s_SCPositionData PosData;
        sc.GetTradePosition(PosData);
        int currentQty = (int)PosData.PositionQuantity;
        int lastQty = sc.GetPersistentInt(200);

        if (currentQty != lastQty) {
            // Read trade_id from sidecar file
            std::string tradeId = "unknown";
            std::string dp(ExportPath.GetString());
            size_t sl = dp.rfind('/'); if (sl == std::string::npos) sl = dp.rfind('\\');
            std::string dataDir = (sl != std::string::npos) ? dp.substr(0, sl + 1) : "";
            { std::ifstream idf(dataDir + "mems26_current_trade_id.txt");
              if (idf.is_open()) { std::getline(idf, tradeId); idf.close(); } }

            std::ostringstream ej;
            ej << std::fixed << std::setprecision(2);
            ej << "{\n"
               << "  \"event_type\": \"POSITION_CHANGE\",\n"
               << "  \"trade_id\": \"" << tradeId << "\",\n"
               << "  \"prev_qty\": " << lastQty << ",\n"
               << "  \"new_qty\": " << currentQty << ",\n"
               << "  \"last_price\": " << (double)sc.LastTradePrice << ",\n"
               << "  \"avg_price\": " << (double)PosData.AveragePrice << ",\n"
               << "  \"ts\": " << (long long)time(NULL) << ",\n"
               << "  \"dll_version\": \"" << MEMS26_DLL_VERSION << "\"\n"
               << "}\n";

            std::ofstream ef(dataDir + "trade_events.json");
            if (ef.is_open()) { ef << ej.str(); ef.close(); }

            sc.AddMessageToLog(SCString().Format(
                "C5: V7.7.1c position %d -> %d (trade=%s), event written",
                lastQty, currentQty, tradeId.c_str()), 1);
            sc.GetPersistentInt(200) = currentQty;
        }
    }
}
