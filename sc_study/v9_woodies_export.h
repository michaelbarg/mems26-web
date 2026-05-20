// v9_woodies_export.h — MEMS26 V9 Woodies CCI export (30-min synthetic bars)
// Version: v9.3.1-p30.10
// Updated: 2026-05-19 (P30.10 HUD: ccidiff H/mid/L, predictor H/L, prev_ohlc, low angle)
// ProjHigh/ProjLow: require Sierra study subgraphs — see docs/handoff export matrix.
// Computes CCI-14, TCCI-6, LSMA-25, EMA-34, Sidewinder, ChopZone,
// trend state, CCI predictor, ZLR + HFE detection from 3-min chart bars.
// ACSIL-safe: uses v9_max/v9_min/v9_abs, no std::max/min.
#pragma once

#include "sierrachart.h"
#include "v9_types.h"
#include <cmath>

// ── 30-min bar aggregated from 3-min chart bars (10 bars per period) ──
static const int WOODIES_30MIN_PERIOD = 10;  // 10 × 3-min = 30 min

struct Woodies30MinBar {
    float open, high, low, close;
    float volume, ask_vol, bid_vol;
    long long timestamp;
    int chart_bar_start;  // first chart bar index in this 30min bar
};

// ── Build 30-min synthetic bars from chart bars ──
inline std::vector<Woodies30MinBar> v9_build_30min_bars(
    SCStudyInterfaceRef sc, int max_bars)
{
    std::vector<Woodies30MinBar> bars;
    bars.reserve(max_bars + 1);
    int total_chart = sc.Index + 1;
    // Start from a 10-bar-aligned boundary
    int usable = total_chart - (total_chart % WOODIES_30MIN_PERIOD);
    int start_from = v9_max_i(0, usable - max_bars * WOODIES_30MIN_PERIOD);
    // Align start
    start_from = start_from - (start_from % WOODIES_30MIN_PERIOD);
    if (start_from < 0) start_from = 0;

    for (int b = start_from; b + WOODIES_30MIN_PERIOD - 1 <= sc.Index; b += WOODIES_30MIN_PERIOD) {
        Woodies30MinBar bar;
        bar.chart_bar_start = b;
        bar.open   = sc.Open[b];
        bar.high   = sc.High[b];
        bar.low    = sc.Low[b];
        bar.close  = sc.Close[b + WOODIES_30MIN_PERIOD - 1];
        bar.volume = 0; bar.ask_vol = 0; bar.bid_vol = 0;
        for (int i = b; i < b + WOODIES_30MIN_PERIOD && i <= sc.Index; i++) {
            bar.high    = v9_max(bar.high, sc.High[i]);
            bar.low     = v9_min(bar.low, sc.Low[i]);
            bar.volume += sc.Volume[i];
            bar.ask_vol += sc.AskVolume[i];
            bar.bid_vol += sc.BidVolume[i];
        }
        bar.timestamp = (long long)time(nullptr);
        bars.push_back(bar);
    }
    return bars;
}

// ── CCI calculation (standard: (TP - SMA(TP,n)) / (0.015 * MeanDev)) ──
inline float v9_calc_cci(const std::vector<Woodies30MinBar>& bars, int end_idx, int period)
{
    if (end_idx < period - 1 || end_idx >= (int)bars.size()) return 0;

    // Typical prices
    float sum_tp = 0;
    for (int i = end_idx - period + 1; i <= end_idx; i++) {
        float tp = (bars[i].high + bars[i].low + bars[i].close) / 3.0f;
        sum_tp += tp;
    }
    float sma_tp = sum_tp / period;

    float tp_current = (bars[end_idx].high + bars[end_idx].low + bars[end_idx].close) / 3.0f;

    // Mean deviation
    float mean_dev = 0;
    for (int i = end_idx - period + 1; i <= end_idx; i++) {
        float tp = (bars[i].high + bars[i].low + bars[i].close) / 3.0f;
        mean_dev += v9_abs(tp - sma_tp);
    }
    mean_dev /= period;

    if (mean_dev < 0.0001f) return 0;
    return (tp_current - sma_tp) / (0.015f * mean_dev);
}

// ── CCI at bar High / Low / Close anchor (Woodies CCIDiff H/mid/L) ──
// 'H'|'L'|'C': last bar TP uses (2H+L)/3, (H+2L)/3, or standard HLC/3.
inline float v9_tp_for_anchor(const Woodies30MinBar& bar, char anchor)
{
    if (anchor == 'H') return (2.0f * bar.high + bar.low) / 3.0f;
    if (anchor == 'L') return (bar.high + 2.0f * bar.low) / 3.0f;
    return (bar.high + bar.low + bar.close) / 3.0f;
}

inline float v9_calc_cci_at_anchor(
    const std::vector<Woodies30MinBar>& bars, int end_idx, int period, char anchor)
{
    if (end_idx < period - 1 || end_idx >= (int)bars.size()) return 0;

    float sum_tp = 0;
    for (int i = end_idx - period + 1; i <= end_idx; i++) {
        float tp = (i == end_idx)
            ? v9_tp_for_anchor(bars[i], anchor)
            : (bars[i].high + bars[i].low + bars[i].close) / 3.0f;
        sum_tp += tp;
    }
    float sma_tp = sum_tp / period;
    float tp_current = v9_tp_for_anchor(bars[end_idx], anchor);

    float mean_dev = 0;
    for (int i = end_idx - period + 1; i <= end_idx; i++) {
        float tp = (i == end_idx)
            ? v9_tp_for_anchor(bars[i], anchor)
            : (bars[i].high + bars[i].low + bars[i].close) / 3.0f;
        mean_dev += v9_abs(tp - sma_tp);
    }
    mean_dev /= period;

    if (mean_dev < 0.0001f) return 0;
    return (tp_current - sma_tp) / (0.015f * mean_dev);
}

// ── EMA calculation ──
inline float v9_calc_ema(const std::vector<Woodies30MinBar>& bars, int end_idx, int period)
{
    if (end_idx < 0 || bars.empty()) return 0;
    float k = 2.0f / (period + 1);
    int start = v9_max_i(0, end_idx - period * 3);  // enough warmup
    float ema = bars[start].close;
    for (int i = start + 1; i <= end_idx; i++) {
        ema = bars[i].close * k + ema * (1.0f - k);
    }
    return ema;
}

// ── LSMA (Least Squares Moving Average) period 25 ──
inline float v9_calc_lsma(const std::vector<Woodies30MinBar>& bars, int end_idx, int period)
{
    if (end_idx < period - 1 || end_idx >= (int)bars.size()) return 0;
    // Linear regression: y = a + b*x, LSMA = predicted value at last point
    float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
    int n = period;
    for (int i = 0; i < n; i++) {
        float x = (float)i;
        float y = bars[end_idx - n + 1 + i].close;
        sum_x += x;
        sum_y += y;
        sum_xy += x * y;
        sum_x2 += x * x;
    }
    float denom = n * sum_x2 - sum_x * sum_x;
    if (v9_abs(denom) < 0.0001f) return bars[end_idx].close;
    float b = (n * sum_xy - sum_x * sum_y) / denom;
    float a = (sum_y - b * sum_x) / n;
    return a + b * (n - 1);  // value at last point
}

// ── Sidewinder (SWI): momentum via CCI slope ──
// SWI = CCI(14) - CCI(14)[3 bars ago], scaled to ±200 range
inline float v9_calc_sidewinder(float cci_current, float cci_3ago)
{
    return cci_current - cci_3ago;
}

// ── ChopZone indicator: ADX-like measure ──
// Simplified: uses close vs EMA distance normalized by ATR
inline float v9_calc_chopzone(const std::vector<Woodies30MinBar>& bars, int end_idx, float ema_val)
{
    if (end_idx < 1 || end_idx >= (int)bars.size()) return 0;
    // ATR approximation over 14 bars
    float atr_sum = 0;
    int atr_count = 0;
    int atr_start = v9_max_i(1, end_idx - 13);
    for (int i = atr_start; i <= end_idx; i++) {
        float tr1 = bars[i].high - bars[i].low;
        float tr2 = v9_abs(bars[i].high - bars[i-1].close);
        float tr3 = v9_abs(bars[i].low - bars[i-1].close);
        float tr = v9_max(tr1, v9_max(tr2, tr3));
        atr_sum += tr;
        atr_count++;
    }
    float atr = (atr_count > 0) ? atr_sum / atr_count : 1.0f;
    if (atr < 0.01f) atr = 0.01f;

    // ChopZone: angle of close relative to EMA, normalized by ATR
    float angle = (bars[end_idx].close - ema_val) / atr;
    return angle * 100.0f;  // Scale to ±100-ish range
}

// ── Trend state: BLUE (up), RED (down), GRAY (neutral), YELLOW (warning) ──
inline const char* v9_woodies_trend_state(float cci14, float cci14_prev, float swi)
{
    // Woodies convention:
    // BLUE:   CCI > 0 for 6+ bars (we approximate: CCI > 0 and rising)
    // RED:    CCI < 0 for 6+ bars
    // YELLOW: CCI crossed zero recently (transition)
    // GRAY:   choppy / no clear trend
    if (cci14 > 50 && cci14_prev > 0 && swi > 20)  return "BLUE";
    if (cci14 < -50 && cci14_prev < 0 && swi < -20) return "RED";
    if ((cci14 > 0 && cci14_prev < 0) || (cci14 < 0 && cci14_prev > 0)) return "YELLOW";
    return "GRAY";
}

// ── CCI Predictor: linear extrapolation ──
inline float v9_cci_predictor(float cci_current, float cci_prev)
{
    // Simple: next = current + (current - prev)
    return cci_current + (cci_current - cci_prev);
}

// ── HUD JSON fields (P30.10): CCIDiff, predictor H/L, prev OHLC, low angle ──
// proj_hi / proj_lo: Daily Projected High-Low (G1), passed from caller via study read.
inline void v9_woodies_json_hud_fields(
    std::ostringstream& j,
    const std::vector<Woodies30MinBar>& bars,
    int bi)
{
    float cci14_c = v9_calc_cci_at_anchor(bars, bi, 14, 'C');
    float cci6_c  = v9_calc_cci_at_anchor(bars, bi, 6, 'C');
    float cci14_h = v9_calc_cci_at_anchor(bars, bi, 14, 'H');
    float cci6_h  = v9_calc_cci_at_anchor(bars, bi, 6, 'H');
    float cci14_l = v9_calc_cci_at_anchor(bars, bi, 14, 'L');
    float cci6_l  = v9_calc_cci_at_anchor(bars, bi, 6, 'L');

    json_float(j, "ccidiff", cci14_c - cci6_c);
    json_float(j, "ccidiff_h", cci14_h - cci6_h);
    json_float(j, "ccidiff_l", cci14_l - cci6_l);

    float cci14_prev_h = (bi > 0) ? v9_calc_cci_at_anchor(bars, bi - 1, 14, 'H') : 0;
    float cci14_prev_l = (bi > 0) ? v9_calc_cci_at_anchor(bars, bi - 1, 14, 'L') : 0;
    json_float(j, "predictor_cci_high", v9_cci_predictor(cci14_h, cci14_prev_h));
    json_float(j, "predictor_cci_low", v9_cci_predictor(cci14_l, cci14_prev_l));

    if (bi > 0) {
        j << ",\"prev_ohlc\":{";
        json_float(j, "o", bars[bi - 1].open, false);
        json_float(j, "h", bars[bi - 1].high);
        json_float(j, "l", bars[bi - 1].low);
        json_float(j, "c", bars[bi - 1].close);
        j << "}";
        float low_delta = bars[bi].low - bars[bi - 1].low;
        json_float(j, "low_prev_angle",
            (float)(std::atan2((double)low_delta, 2.0) * 180.0 / 3.141592653589793));
    }
}

// ── ZLR (Zero Line Reject) detection ──
// ZLR UP:   CCI was above +100 → pulls back toward 0 (but stays > -100) → bounces up
// ZLR DOWN: CCI was below -100 → pulls back toward 0 (but stays < +100) → drops
struct ZLRResult {
    bool detected;
    const char* direction;  // "UP", "DOWN", or "NONE"
    float entry_cci;
    int bars_since_extreme;
};

inline ZLRResult v9_detect_zlr(const float* cci_hist, int n, int lookback)
{
    ZLRResult r = {false, "NONE", 0, 0};
    if (n < lookback + 1) return r;

    float current = cci_hist[n - 1];
    float prev    = cci_hist[n - 2];

    // Check for ZLR UP: was above 100, pulled to near-zero, bouncing
    bool was_above_100 = false;
    int bars_since = 0;
    for (int i = n - 2; i >= n - lookback && i >= 0; i--) {
        if (cci_hist[i] > 100) { was_above_100 = true; bars_since = n - 1 - i; break; }
    }
    if (was_above_100 && bars_since <= lookback) {
        // Check pullback: CCI came to 0..+100 range, then bouncing up
        bool pulled_near_zero = false;
        for (int i = n - 2; i >= n - bars_since && i >= 0; i--) {
            if (cci_hist[i] >= -50 && cci_hist[i] <= 100) { pulled_near_zero = true; break; }
        }
        if (pulled_near_zero && current > prev && current > 0 && current < 200) {
            r.detected = true;
            r.direction = "UP";
            r.entry_cci = current;
            r.bars_since_extreme = bars_since;
            return r;
        }
    }

    // Check for ZLR DOWN: was below -100, pulled to near-zero, dropping
    bool was_below_n100 = false;
    bars_since = 0;
    for (int i = n - 2; i >= n - lookback && i >= 0; i--) {
        if (cci_hist[i] < -100) { was_below_n100 = true; bars_since = n - 1 - i; break; }
    }
    if (was_below_n100 && bars_since <= lookback) {
        bool pulled_near_zero = false;
        for (int i = n - 2; i >= n - bars_since && i >= 0; i--) {
            if (cci_hist[i] >= -100 && cci_hist[i] <= 50) { pulled_near_zero = true; break; }
        }
        if (pulled_near_zero && current < prev && current < 0 && current > -200) {
            r.detected = true;
            r.direction = "DOWN";
            r.entry_cci = current;
            r.bars_since_extreme = bars_since;
            return r;
        }
    }

    return r;
}

// ── HFE (Hook From Extreme) detection ──
// CCI reaches ±200 within lookback, then hooks back toward zero line
// HFE UP:   CCI hit -200 or below → hooks up (LONG candidate)
// HFE DOWN: CCI hit +200 or above → hooks down (SHORT candidate)
struct HFEResult {
    bool detected;
    const char* direction;  // "UP", "DOWN", or "NONE"
    int extreme_bars_ago;   // how many bars since the ±200 extreme
};

inline HFEResult v9_detect_hfe(const float* cci_hist, int n, int lookback)
{
    HFEResult r = {false, "NONE", 0};
    if (n < 4) return r;

    float current = cci_hist[n - 1];
    float prev    = cci_hist[n - 2];
    int search_start = v9_max_i(0, n - lookback);

    // Search for negative extreme (CCI <= -200)
    for (int i = n - 3; i >= search_start; i--) {
        if (cci_hist[i] <= -200.0f) {
            int bars_ago = n - 1 - i;
            float hook_distance = current - cci_hist[i];
            // Hook: moved at least 50 points back AND current rising
            if (hook_distance >= 50.0f && current > prev) {
                r.detected = true;
                r.direction = "UP";
                r.extreme_bars_ago = bars_ago;
                return r;
            }
            break;  // only check first (most recent) extreme
        }
    }

    // Search for positive extreme (CCI >= +200)
    for (int i = n - 3; i >= search_start; i--) {
        if (cci_hist[i] >= 200.0f) {
            int bars_ago = n - 1 - i;
            float hook_distance = cci_hist[i] - current;
            if (hook_distance >= 50.0f && current < prev) {
                r.detected = true;
                r.direction = "DOWN";
                r.extreme_bars_ago = bars_ago;
                return r;
            }
            break;
        }
    }

    return r;
}

// ══════════════════════════════════════════════════════════════
// D-074: 5-min Woodies export (2 × 3-min chart bars ≈ 6 min)
// ══════════════════════════════════════════════════════════════
static const int WOODIES_5MIN_PERIOD = 2;  // 2 × 3-min = ~5-6 min

inline std::vector<Woodies30MinBar> v9_build_5min_bars(
    SCStudyInterfaceRef sc, int max_bars)
{
    std::vector<Woodies30MinBar> bars;
    bars.reserve(max_bars + 1);
    int total_chart = sc.Index + 1;
    int usable = total_chart - (total_chart % WOODIES_5MIN_PERIOD);
    int start_from = v9_max_i(0, usable - max_bars * WOODIES_5MIN_PERIOD);
    start_from = start_from - (start_from % WOODIES_5MIN_PERIOD);
    if (start_from < 0) start_from = 0;

    for (int b = start_from; b + WOODIES_5MIN_PERIOD - 1 <= sc.Index; b += WOODIES_5MIN_PERIOD) {
        Woodies30MinBar bar;
        bar.chart_bar_start = b;
        bar.open   = sc.Open[b];
        bar.high   = sc.High[b];
        bar.low    = sc.Low[b];
        bar.close  = sc.Close[b + WOODIES_5MIN_PERIOD - 1];
        bar.volume = 0; bar.ask_vol = 0; bar.bid_vol = 0;
        for (int i = b; i < b + WOODIES_5MIN_PERIOD && i <= sc.Index; i++) {
            bar.high    = v9_max(bar.high, sc.High[i]);
            bar.low     = v9_min(bar.low, sc.Low[i]);
            bar.volume += sc.Volume[i];
            bar.ask_vol += sc.AskVolume[i];
            bar.bid_vol += sc.BidVolume[i];
        }
        bar.timestamp = (long long)time(nullptr);
        bars.push_back(bar);
    }
    return bars;
}

inline std::string v9_woodies_5min_to_json(SCStudyInterfaceRef sc, int max_history,
                                            float proj_hi = 0, float proj_lo = 0)
{
    std::vector<Woodies30MinBar> bars = v9_build_5min_bars(sc, max_history + 10);
    int n = (int)bars.size();

    // Pre-compute CCI-14 history for ZLR/HFE detection
    std::vector<float> cci14_hist;
    cci14_hist.reserve(n);
    for (int i = 0; i < n; i++) {
        cci14_hist.push_back(v9_calc_cci(bars, i, 14));
    }

    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "woodies_5min", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "bar_period_minutes", 5);
    json_int(j, "total_bars", n);

    int history_start = v9_max_i(0, n - max_history);
    j << ",\"history\":[";

    for (int bi = history_start; bi < n; bi++) {
        if (bi > history_start) j << ",";

        float cci14     = v9_calc_cci(bars, bi, 14);
        float cci6      = v9_calc_cci(bars, bi, 6);
        float ema34     = v9_calc_ema(bars, bi, 34);
        float lsma25    = v9_calc_lsma(bars, bi, 25);
        float cci14_prev = (bi > 0) ? v9_calc_cci(bars, bi - 1, 14) : 0;
        float cci14_3ago = (bi >= 3) ? v9_calc_cci(bars, bi - 3, 14) : 0;
        float swi       = v9_calc_sidewinder(cci14, cci14_3ago);
        float czi       = v9_calc_chopzone(bars, bi, ema34);
        float predictor = v9_cci_predictor(cci14, cci14_prev);
        const char* trend = v9_woodies_trend_state(cci14, cci14_prev, swi);
        ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), bi + 1, 12);
        HFEResult hfe = v9_detect_hfe(cci14_hist.data(), bi + 1, 12);

        j << "{";
        json_long(j, "ts", bars[bi].timestamp, false);
        j << ",\"ohlc\":{";
        json_float(j, "o", bars[bi].open, false);
        json_float(j, "h", bars[bi].high);
        json_float(j, "l", bars[bi].low);
        json_float(j, "c", bars[bi].close);
        json_float(j, "vol", bars[bi].volume);
        j << "}";
        json_float(j, "cci_14", cci14);
        json_float(j, "cci_6_tcci", cci6);
        json_float(j, "lsma_value", lsma25);
        json_bool(j, "lsma_above_price", lsma25 > bars[bi].close);
        json_float(j, "swi_value", swi);
        json_float(j, "czi_value", czi);
        json_float(j, "ema_34", ema34);
        json_str(j, "trend_state", trend);
        json_float(j, "predictor_next_cci", predictor);
        json_bool(j, "zlr_detected", zlr.detected);
        json_str(j, "zlr_direction", zlr.direction);
        json_bool(j, "hfe_detected", hfe.detected);
        json_str(j, "hfe_direction", hfe.direction);
        json_int(j, "hfe_extreme_bars_ago", hfe.extreme_bars_ago);
        v9_woodies_json_hud_fields(j, bars, bi);
        j << "}";
    }
    j << "]";

    // current_bar (last)
    if (n > 0) {
        int ci = n - 1;
        float cci14     = v9_calc_cci(bars, ci, 14);
        float cci6      = v9_calc_cci(bars, ci, 6);
        float ema34     = v9_calc_ema(bars, ci, 34);
        float lsma25    = v9_calc_lsma(bars, ci, 25);
        float cci14_prev = (ci > 0) ? v9_calc_cci(bars, ci - 1, 14) : 0;
        float cci14_3ago = (ci >= 3) ? v9_calc_cci(bars, ci - 3, 14) : 0;
        float swi       = v9_calc_sidewinder(cci14, cci14_3ago);
        float czi       = v9_calc_chopzone(bars, ci, ema34);
        float predictor = v9_cci_predictor(cci14, cci14_prev);
        const char* trend = v9_woodies_trend_state(cci14, cci14_prev, swi);
        ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), (int)cci14_hist.size(), 12);
        HFEResult hfe = v9_detect_hfe(cci14_hist.data(), (int)cci14_hist.size(), 12);

        j << ",\"current_bar\":{";
        json_long(j, "ts", bars[ci].timestamp, false);
        j << ",\"ohlc\":{";
        json_float(j, "o", bars[ci].open, false);
        json_float(j, "h", bars[ci].high);
        json_float(j, "l", bars[ci].low);
        json_float(j, "c", bars[ci].close);
        json_float(j, "vol", bars[ci].volume);
        j << "}";
        json_float(j, "cci_14", cci14);
        json_float(j, "cci_6_tcci", cci6);
        json_float(j, "lsma_value", lsma25);
        json_bool(j, "lsma_above_price", lsma25 > bars[ci].close);
        json_float(j, "swi_value", swi);
        json_float(j, "czi_value", czi);
        json_float(j, "ema_34", ema34);
        json_str(j, "trend_state", trend);
        json_float(j, "predictor_next_cci", predictor);
        json_bool(j, "zlr_detected", zlr.detected);
        json_str(j, "zlr_direction", zlr.direction);
        json_bool(j, "hfe_detected", hfe.detected);
        json_str(j, "hfe_direction", hfe.direction);
        json_int(j, "hfe_extreme_bars_ago", hfe.extreme_bars_ago);
        json_float(j, "cci_14_prev", cci14_prev);
        json_float(j, "cci_14_3ago", cci14_3ago);
        v9_woodies_json_hud_fields(j, bars, ci);
        // G1: Daily Projected High-Low (from Sierra study, passed by caller)
        if (proj_hi != 0) json_float(j, "proj_hi", proj_hi);
        else { j << ",\"proj_hi\":null"; }
        if (proj_lo != 0) json_float(j, "proj_lo", proj_lo);
        else { j << ",\"proj_lo\":null"; }
        j << "}";
    }

    j << "}";
    return j.str();
}

// ══════════════════════════════════════════════════════════════
// Legacy export: woodies_30min.json (kept for replay)
// ══════════════════════════════════════════════════════════════

inline std::string v9_woodies_30min_to_json(SCStudyInterfaceRef sc, int max_history)
{
    std::vector<Woodies30MinBar> bars = v9_build_30min_bars(sc, max_history + 10);
    int n = (int)bars.size();

    // Pre-compute CCI-14 history for ZLR detection
    std::vector<float> cci14_hist;
    cci14_hist.reserve(n);
    for (int i = 0; i < n; i++) {
        cci14_hist.push_back(v9_calc_cci(bars, i, 14));
    }

    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "woodies_30min", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "bar_period_minutes", 30);
    json_int(j, "total_bars", n);

    // History + current_bar
    int history_start = v9_max_i(0, n - max_history);
    j << ",\"history\":[";

    for (int bi = history_start; bi < n; bi++) {
        if (bi > history_start) j << ",";

        float cci14     = v9_calc_cci(bars, bi, 14);
        float cci6      = v9_calc_cci(bars, bi, 6);
        float ema34     = v9_calc_ema(bars, bi, 34);
        float lsma25    = v9_calc_lsma(bars, bi, 25);
        float cci14_prev = (bi > 0) ? v9_calc_cci(bars, bi - 1, 14) : 0;
        float cci14_3ago = (bi >= 3) ? v9_calc_cci(bars, bi - 3, 14) : 0;
        float swi       = v9_calc_sidewinder(cci14, cci14_3ago);
        float czi       = v9_calc_chopzone(bars, bi, ema34);
        float predictor = v9_cci_predictor(cci14, cci14_prev);
        const char* trend = v9_woodies_trend_state(cci14, cci14_prev, swi);

        // ZLR detection using history up to this bar (no copy — pointer + count)
        ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), bi + 1, 12);
        // HFE detection (pattern #9)
        HFEResult hfe = v9_detect_hfe(cci14_hist.data(), bi + 1, 12);

        j << "{";
        json_long(j, "ts", bars[bi].timestamp, false);
        j << ",\"ohlc\":{";
        json_float(j, "o", bars[bi].open, false);
        json_float(j, "h", bars[bi].high);
        json_float(j, "l", bars[bi].low);
        json_float(j, "c", bars[bi].close);
        json_float(j, "vol", bars[bi].volume);
        j << "}";
        json_float(j, "cci_14", cci14);
        json_float(j, "cci_6_tcci", cci6);
        json_float(j, "lsma_value", lsma25);
        json_bool(j, "lsma_above_price", lsma25 > bars[bi].close);
        json_float(j, "swi_value", swi);
        json_float(j, "czi_value", czi);
        json_float(j, "ema_34", ema34);
        json_str(j, "trend_state", trend);
        json_float(j, "predictor_next_cci", predictor);
        json_bool(j, "zlr_detected", zlr.detected);
        json_str(j, "zlr_direction", zlr.direction);
        json_bool(j, "hfe_detected", hfe.detected);
        json_str(j, "hfe_direction", hfe.direction);
        json_int(j, "hfe_extreme_bars_ago", hfe.extreme_bars_ago);
        j << "}";
    }
    j << "]";

    // Current bar summary (last in array)
    if (n > 0) {
        int ci = n - 1;
        float cci14     = v9_calc_cci(bars, ci, 14);
        float cci6      = v9_calc_cci(bars, ci, 6);
        float ema34     = v9_calc_ema(bars, ci, 34);
        float lsma25    = v9_calc_lsma(bars, ci, 25);
        float cci14_prev = (ci > 0) ? v9_calc_cci(bars, ci - 1, 14) : 0;
        float cci14_3ago = (ci >= 3) ? v9_calc_cci(bars, ci - 3, 14) : 0;
        float swi       = v9_calc_sidewinder(cci14, cci14_3ago);
        float czi       = v9_calc_chopzone(bars, ci, ema34);
        float predictor = v9_cci_predictor(cci14, cci14_prev);
        const char* trend = v9_woodies_trend_state(cci14, cci14_prev, swi);
        ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), (int)cci14_hist.size(), 12);
        HFEResult hfe = v9_detect_hfe(cci14_hist.data(), (int)cci14_hist.size(), 12);

        j << ",\"current_bar\":{";
        json_long(j, "ts", bars[ci].timestamp, false);
        j << ",\"ohlc\":{";
        json_float(j, "o", bars[ci].open, false);
        json_float(j, "h", bars[ci].high);
        json_float(j, "l", bars[ci].low);
        json_float(j, "c", bars[ci].close);
        json_float(j, "vol", bars[ci].volume);
        j << "}";
        json_float(j, "cci_14", cci14);
        json_float(j, "cci_6_tcci", cci6);
        json_float(j, "lsma_value", lsma25);
        json_bool(j, "lsma_above_price", lsma25 > bars[ci].close);
        json_float(j, "swi_value", swi);
        json_float(j, "czi_value", czi);
        json_float(j, "ema_34", ema34);
        json_str(j, "trend_state", trend);
        json_float(j, "predictor_next_cci", predictor);
        json_bool(j, "zlr_detected", zlr.detected);
        json_str(j, "zlr_direction", zlr.direction);
        json_bool(j, "hfe_detected", hfe.detected);
        json_str(j, "hfe_direction", hfe.direction);
        json_int(j, "hfe_extreme_bars_ago", hfe.extreme_bars_ago);
        json_float(j, "cci_14_prev", cci14_prev);
        json_float(j, "cci_14_3ago", cci14_3ago);
        j << "}";
    }

    j << "}";
    return j.str();
}
