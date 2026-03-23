// ============================================================
// MES_ZMQ_Publisher.cpp
// Sierra Chart ACSIL Study — ZeroMQ Publisher
//
// שולח כל נר שנסגר ב-ZeroMQ PUSH socket.
// Python Bridge מקבל ומעביר לענן.
//
// תלות: libzmq.dll (ר' README)
// port ברירת מחדל: 5555
// ============================================================

#include "SierraChartACSIL.h"
#include <zmq.h>
#include <sstream>
#include <iomanip>
#include <ctime>

// ZeroMQ context ו-socket — נשמרים בין קריאות
static void*  s_ZMQContext = nullptr;
static void*  s_ZMQSocket  = nullptr;
static bool   s_Connected  = false;

SCSFExport scsf_MES_ZMQ_Publisher(SCStudyInterfaceRef sc)
{
    SCInputRef ZMQ_Port       = sc.Input[0];
    SCInputRef ExportOnClose  = sc.Input[1];   // שלח רק בסגירת נר
    SCInputRef ExportInterval = sc.Input[2];   // גם שלח כל X שניות (Live tick)

    if (sc.SetDefaults)
    {
        sc.GraphName        = "MES ZMQ Publisher";
        sc.StudyDescription = "Publishes bar data via ZeroMQ to Python bridge";
        sc.AutoLoop         = 1;

        ZMQ_Port.Name       = "ZeroMQ Port";
        ZMQ_Port.SetInt(5555);

        ExportOnClose.Name  = "Export on Bar Close Only";
        ExportOnClose.SetYesNo(0);  // 0 = כל tick, 1 = רק בסגירה

        ExportInterval.Name = "Live Tick Interval (seconds, 0=every tick)";
        ExportInterval.SetInt(1);

        return;
    }

    int idx = sc.Index;

    // ── אתחול ZeroMQ בפעם הראשונה ──────────────────────────
    if (!s_Connected)
    {
        s_ZMQContext = zmq_ctx_new();
        s_ZMQSocket  = zmq_socket(s_ZMQContext, ZMQ_PUSH);

        int linger = 0;
        zmq_setsockopt(s_ZMQSocket, ZMQ_LINGER, &linger, sizeof(linger));

        // Non-blocking send
        int sndhwm = 10;
        zmq_setsockopt(s_ZMQSocket, ZMQ_SNDHWM, &sndhwm, sizeof(sndhwm));

        char endpoint[64];
        snprintf(endpoint, sizeof(endpoint), "tcp://*:%d", ZMQ_Port.GetInt());
        int rc = zmq_bind(s_ZMQSocket, endpoint);

        if (rc == 0)
        {
            s_Connected = true;
            sc.AddMessageToLog("ZMQ Publisher bound on port " + SCString(ZMQ_Port.GetInt()), 0);
        }
        else
        {
            sc.AddMessageToLog("ZMQ Publisher FAILED to bind!", 1);
            return;
        }
    }

    // ── פילטר: שלח רק בסגירת נר ──────────────────────────
    if (ExportOnClose.GetYesNo() && !sc.GetBarHasClosedStatus(idx))
        return;

    // ── פילטר: throttle לפי interval ──────────────────────
    static time_t lastSend = 0;
    time_t now = time(nullptr);
    int interval = ExportInterval.GetInt();
    if (interval > 0 && (now - lastSend) < interval)
        return;
    lastSend = now;

    // ── חישוב CVD (Cumulative Volume Delta) ───────────────
    float CumulDelta = 0.0f;
    SCDateTime today = sc.BaseDateTimeIn[idx].GetDate();
    for (int i = idx; i >= 0; i--)
    {
        if (sc.BaseDateTimeIn[i].GetDate() < today) break;
        CumulDelta += (sc.AskVolume[i] - sc.BidVolume[i]);
    }

    float BarDelta      = sc.AskVolume[idx] - sc.BidVolume[idx];
    float Delta20Bar    = 0.0f;
    if (idx >= 20)
    {
        float cvd_now = 0, cvd_20 = 0;
        for (int i = idx;    i >= idx-20 && i >= 0; i--) cvd_now  += (sc.AskVolume[i] - sc.BidVolume[i]);
        for (int i = idx-20; i >= idx-40 && i >= 0; i--) cvd_20   += (sc.AskVolume[i] - sc.BidVolume[i]);
        Delta20Bar = cvd_now - cvd_20;
    }

    // ── Session info ──────────────────────────────────────
    SCDateTime BarTime = sc.BaseDateTimeIn[idx];
    int Hour   = BarTime.GetHour();
    int Minute = BarTime.GetMinute();

    // Session phase (Israel time GMT+3)
    const char* phase = "OVERNIGHT";
    if      (Hour == 16 && Minute >= 30)         phase = "OPEN";
    else if (Hour >= 17 && Hour < 19)             phase = "AM_SESSION";
    else if (Hour >= 19 && Hour < 21)             phase = "MIDDAY";
    else if (Hour >= 21 && Hour < 23)             phase = "PM_SESSION";
    else if (Hour == 23)                           phase = "CLOSE";

    // Session minute (minutes since 16:30 IST)
    int sesMin = (Hour * 60 + Minute) - (16 * 60 + 30);
    if (sesMin < 0) sesMin = -1;

    // ── Session High/Low ──────────────────────────────────
    float SesHigh = sc.High[idx], SesLow = sc.Low[idx];
    for (int i = idx - 1; i >= 0; i--)
    {
        if (sc.BaseDateTimeIn[i].GetDate() < today) break;
        if (sc.High[i] > SesHigh) SesHigh = sc.High[i];
        if (sc.Low[i]  < SesLow)  SesLow  = sc.Low[i];
    }

    // ── IB (Initial Balance) high/low — first 60 min ──────
    float IBHigh = -1e9f, IBLow = 1e9f;
    SCDateTime ibEnd = sc.BaseDateTimeIn[idx];
    // IB = bars from session start until 60 minutes in
    for (int i = idx; i >= 0; i--)
    {
        if (sc.BaseDateTimeIn[i].GetDate() < today) break;
        int bHour = sc.BaseDateTimeIn[i].GetHour();
        int bMin  = sc.BaseDateTimeIn[i].GetMinute();
        int bSesMin = (bHour * 60 + bMin) - (16 * 60 + 30);
        if (bSesMin < 0 || bSesMin > 60) continue;
        if (sc.High[i] > IBHigh) IBHigh = sc.High[i];
        if (sc.Low[i]  < IBLow)  IBLow  = sc.Low[i];
    }

    // ── Woodi Pivots ──────────────────────────────────────
    float PH = 0, PL = 0, PC = 0;
    SCDateTime prevDate;
    bool foundPrev = false;
    for (int i = idx - 1; i >= 0; i--)
    {
        SCDateTime bd = sc.BaseDateTimeIn[i].GetDate();
        if (!foundPrev && bd < today)
        {
            prevDate  = bd;
            foundPrev = true;
            PC        = sc.Close[i];
            PH        = sc.High[i];
            PL        = sc.Low[i];
        }
        else if (foundPrev && bd == prevDate)
        {
            if (sc.High[i] > PH) PH = sc.High[i];
            if (sc.Low[i]  < PL) PL = sc.Low[i];
        }
        else if (foundPrev)
            break;
    }

    float PP=0, R1=0, R2=0, S1=0, S2=0;
    if (foundPrev && PH > 0)
    {
        PP = (PH + PL + PC * 2.0f) / 4.0f;
        R1 = 2.0f * PP - PL;
        R2 = PP + (PH - PL);
        S1 = 2.0f * PP - PH;
        S2 = PP - (PH - PL);
    }

    // ── 72H / Weekly high-low ─────────────────────────────
    float H72 = sc.High[idx], L72 = sc.Low[idx];
    float HWk = sc.High[idx], LWk = sc.Low[idx];
    SCDateTime cutoff72H = sc.BaseDateTimeIn[idx];
    cutoff72H.SubtractSeconds(72 * 3600);
    SCDateTime startOfWeek = sc.BaseDateTimeIn[idx];
    startOfWeek.SubtractSeconds(startOfWeek.GetDayOfWeek() * 86400);

    for (int i = idx - 1; i >= 0; i--)
    {
        SCDateTime bt = sc.BaseDateTimeIn[i];
        if (bt >= cutoff72H) {
            if (sc.High[i] > H72) H72 = sc.High[i];
            if (sc.Low[i]  < L72) L72 = sc.Low[i];
        }
        if (bt >= startOfWeek) {
            if (sc.High[i] > HWk) HWk = sc.High[i];
            if (sc.Low[i]  < LWk) LWk = sc.Low[i];
        }
        if (bt < cutoff72H && bt < startOfWeek) break;
    }

    // ── Build JSON payload ────────────────────────────────
    std::ostringstream json;
    json << std::fixed << std::setprecision(2);
    json << "{"
         << "\"ts\":"         << (long long)now             << ","
         << "\"sym\":\"MEMS26\","
         << "\"tf\":"         << sc.SecondsPerBar / 60      << ","
         << "\"bar\":{"
             << "\"o\":"      << sc.Open[idx]               << ","
             << "\"h\":"      << sc.High[idx]               << ","
             << "\"l\":"      << sc.Low[idx]                << ","
             << "\"c\":"      << sc.Close[idx]              << ","
             << "\"v\":"      << sc.Volume[idx]             << ","
             << "\"bv\":"     << sc.BidVolume[idx]          << ","
             << "\"av\":"     << sc.AskVolume[idx]          << ","
             << "\"delta\":"  << BarDelta
         << "},"
         << "\"cvd\":{"
             << "\"total\":"  << CumulDelta                 << ","
             << "\"d20\":"    << Delta20Bar                 << ","
             << "\"bull\":"   << (CumulDelta > 0 ? "true" : "false")
         << "},"
         << "\"session\":{"
             << "\"phase\":\"" << phase << "\","
             << "\"min\":"    << sesMin                     << ","
             << "\"sh\":"     << SesHigh                   << ","
             << "\"sl\":"     << SesLow                    << ","
             << "\"ibh\":"    << (IBHigh > -1e8f ? IBHigh : 0.0f) << ","
             << "\"ibl\":"    << (IBLow  <  1e8f ? IBLow  : 0.0f)
         << "},"
         << "\"woodi\":{"
             << "\"pp\":"     << PP << ","
             << "\"r1\":"     << R1 << ","
             << "\"r2\":"     << R2 << ","
             << "\"s1\":"     << S1 << ","
             << "\"s2\":"     << S2
         << "},"
         << "\"levels\":{"
             << "\"h72\":"    << H72 << ","
             << "\"l72\":"    << L72 << ","
             << "\"hwk\":"    << HWk << ","
             << "\"lwk\":"    << LWk
         << "}"
         << "}";

    std::string msg = json.str();

    // ── ZeroMQ PUSH (non-blocking) ────────────────────────
    int rc = zmq_send(s_ZMQSocket, msg.c_str(), msg.size(), ZMQ_DONTWAIT);
    if (rc < 0 && errno != EAGAIN)
    {
        sc.AddMessageToLog("ZMQ send error", 1);
    }
}
