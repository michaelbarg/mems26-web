// MES_AI_DataExport_merged.cpp — v9.4.2 monolith for Sierra Chart remote build
// Generated 2026-05-22 21:19:46 by build_monolithic_cpp.sh
// CRITICAL: sierrachart.h + SCDLLName MUST be in first 10 lines

#include "sierrachart.h"

SCDLLName("MES_AI_DataExport")

// ====== v9_types.h (inlined) ======
// v9_types.h — MEMS26 V9 shared types and helpers
// ACSIL-safe: no std::max/min, no STL that Sierra macros break

#include <vector>
#include <map>
#include <string>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <ctime>

// ── ACSIL-safe min/max (Sierra macros clobber std::max/min) ──
inline float v9_max(float a, float b) { return (a > b) ? a : b; }
inline float v9_min(float a, float b) { return (a < b) ? a : b; }
inline int   v9_max_i(int a, int b)   { return (a > b) ? a : b; }
inline int   v9_min_i(int a, int b)   { return (a < b) ? a : b; }
inline float v9_abs(float x)          { return (x < 0) ? -x : x; }

// ── Version ──
static const char* V9_VERSION = "v9.4.2-p30.11";  // P30.11: G1 proj H/L, G2 TPO validation, G4 va_ok+session_date

// ── Export directory ──
static const char* V9_EXPORT_DIR = "/Users/michael/SierraChart_Data/v9_export/";

// ── Tick reversal bar ──
struct TickReversalBar {
    float open;
    float high;
    float low;
    float close;
    float volume;
    float ask_volume;  // buy
    float bid_volume;  // sell
    float delta;       // ask - bid
    int   bar_index;
    int   direction;   // +1 up, -1 down, 0 neutral
    long long timestamp;
};

// ── 5-minute OHLCV bar ──
struct V9FiveMinBar {
    long long ts;       // Unix timestamp, bucket start
    float open;
    float high;
    float low;
    float close;
    float volume;
    float poc_vol;
    float vah;
    float val;
    float cumulative_delta;
};

// ── Footprint price level ──
struct FootprintLevel {
    float price;
    float bid_vol;   // sell
    float ask_vol;   // buy
    float delta;     // ask - bid
    bool  imbalance_buy;   // ask/bid >= 2.5
    bool  imbalance_sell;  // bid/ask >= 2.5
};

// ── Footprint bar ──
struct FootprintBar {
    int   bar_index;
    float open;
    float high;
    float low;
    float close;
    float total_volume;
    float total_delta;
    float poc_price;         // price with max volume
    float poc_volume;
    int   stacked_imb_buy;   // consecutive buy imbalances
    int   stacked_imb_sell;  // consecutive sell imbalances
    std::vector<FootprintLevel> levels;
};

// ── Volume Profile entry ──
struct VolumeProfileEntry {
    float price;
    float volume;
    float pct_of_total;
    bool  is_poc;
    bool  is_vah;
    bool  is_val;
};

// ── JSON helper: write a float with precision ──
inline void json_float(std::ostringstream& j, const char* key, float val, bool comma = true) {
    if (comma) j << ",";
    j << "\"" << key << "\":" << std::fixed << std::setprecision(2) << val;
}

inline void json_int(std::ostringstream& j, const char* key, int val, bool comma = true) {
    if (comma) j << ",";
    j << "\"" << key << "\":" << val;
}

inline void json_str(std::ostringstream& j, const char* key, const char* val, bool comma = true) {
    if (comma) j << ",";
    j << "\"" << key << "\":\"" << val << "\"";
}

inline void json_bool(std::ostringstream& j, const char* key, bool val, bool comma = true) {
    if (comma) j << ",";
    j << "\"" << key << "\":" << (val ? "true" : "false");
}

inline void json_long(std::ostringstream& j, const char* key, long long val, bool comma = true) {
    if (comma) j << ",";
    j << "\"" << key << "\":" << val;
}

// ── File write helper ──
inline bool v9_write_json(const char* dir, const char* filename, const std::string& json) {
    std::string path = std::string(dir) + filename;
    std::ofstream f(path.c_str());
    if (!f.is_open()) return false;
    f << json;
    f.close();
    return true;
}

// ====== v9_exports.h (inlined) ======
// v9_exports.h — MEMS26 V9 new export functions
// Each function builds JSON and writes to v9_export/ directory
// ACSIL-safe: uses v9_max/v9_min, not std::max/std::min


// ─────────────────────────────────────────────────────────────
// 1. Tick Reversal Bars (generic N-tick)
// ─────────────────────────────────────────────────────────────
// Builds reversal bars from the underlying chart bars.
// A reversal bar completes when price reverses N ticks (N * tick_size)
// from the bar's extreme in the current direction.

inline std::vector<TickReversalBar> v9_build_tick_reversal_bars(
    SCStudyInterfaceRef sc, int num_ticks, int lookback_bars)
{
    std::vector<TickReversalBar> bars;
    float tick_size = sc.TickSize;
    float reversal_amount = num_ticks * tick_size;

    if (sc.Index < 2 || tick_size <= 0) return bars;
    bars.reserve(lookback_bars / 4);  // pre-alloc: ~1 reversal bar per 4 chart bars

    int start = v9_max_i(0, sc.Index - lookback_bars);

    // State: current building bar
    TickReversalBar current;
    current.open = sc.Open[start];
    current.high = sc.Open[start];
    current.low  = sc.Open[start];
    current.close = sc.Close[start];
    current.volume = 0;
    current.ask_volume = 0;
    current.bid_volume = 0;
    current.delta = 0;
    current.bar_index = 0;
    current.direction = 0;
    current.timestamp = 0;

    for (int i = start; i <= sc.Index; i++)
    {
        float h = sc.High[i];
        float l = sc.Low[i];
        float c = sc.Close[i];
        float v = sc.Volume[i];
        float av = sc.AskVolume[i];
        float bv = sc.BidVolume[i];

        // Update current bar extremes
        current.high = v9_max(current.high, h);
        current.low  = v9_min(current.low, l);
        current.close = c;
        current.volume += v;
        current.ask_volume += av;
        current.bid_volume += bv;

        // Determine direction from open
        if (current.direction == 0) {
            if (c > current.open + tick_size) current.direction = 1;
            else if (c < current.open - tick_size) current.direction = -1;
        }

        // Check reversal
        bool reversed = false;
        if (current.direction == 1) {
            // Up bar: reversal = price drops reversal_amount from high
            if (current.high - c >= reversal_amount) reversed = true;
        } else if (current.direction == -1) {
            // Down bar: reversal = price rises reversal_amount from low
            if (c - current.low >= reversal_amount) reversed = true;
        }

        if (reversed) {
            current.delta = current.ask_volume - current.bid_volume;
            current.timestamp = (long long)time(nullptr);
            bars.push_back(current);

            // v9.2.0 safety cap: prevent unbounded tick reversal accumulation
            if (bars.size() >= 200) break;

            // Start new bar
            int new_dir = (current.direction == 1) ? -1 : 1;
            current.open = c;
            current.high = c;
            current.low  = c;
            current.close = c;
            current.volume = 0;
            current.ask_volume = 0;
            current.bid_volume = 0;
            current.delta = 0;
            current.bar_index = (int)bars.size();
            current.direction = new_dir;
            current.timestamp = 0;
        }
    }

    // Include the building bar as "current"
    current.delta = current.ask_volume - current.bid_volume;
    current.timestamp = time(nullptr);
    bars.push_back(current);

    return bars;
}

inline std::string v9_tick_reversal_to_json(
    const std::vector<TickReversalBar>& bars, int num_ticks)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "tick_reversal", false);
    json_int(j, "tick_count", num_ticks);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "bar_count", (int)bars.size());
    j << ",\"bars\":[";

    for (size_t i = 0; i < bars.size(); i++) {
        if (i > 0) j << ",";
        const TickReversalBar& b = bars[i];
        j << "{";
        json_int(j, "idx", b.bar_index, false);
        json_float(j, "o", b.open);
        json_float(j, "h", b.high);
        json_float(j, "l", b.low);
        json_float(j, "c", b.close);
        json_float(j, "vol", b.volume);
        json_float(j, "ask_vol", b.ask_volume);
        json_float(j, "bid_vol", b.bid_volume);
        json_float(j, "delta", b.delta);
        json_int(j, "dir", b.direction);
        json_long(j, "ts", b.timestamp);
        j << "}";
    }
    j << "]}";
    return j.str();
}

// ─────────────────────────────────────────────────────────────
// 1b. Canonical 5-minute OHLCV bars (System 2 history feed)
// ─────────────────────────────────────────────────────────────
// Builds real 5-minute buckets from the chart bars and writes the contract
// expected by bridge/v9_streams/bars_5min_stream.py.

inline long long v9_sc_datetime_to_unix(SCDateTime dt)
{
    // Sierra SCDateTime uses the same day-serial epoch as Excel/OLE.
    double serial = dt.GetAsDouble();
    return (long long)((serial - 25569.0) * 86400.0 + 0.5);
}

inline std::vector<V9FiveMinBar> v9_build_5min_ohlcv_bars(
    SCStudyInterfaceRef sc, int lookback_bars)
{
    std::vector<V9FiveMinBar> bars;
    if (sc.Index < 0) return bars;

    int start = v9_max_i(0, sc.Index - lookback_bars);
    long long current_bucket = -1;
    V9FiveMinBar current;

    for (int i = start; i <= sc.Index; i++)
    {
        long long raw_ts = v9_sc_datetime_to_unix(sc.BaseDateTimeIn[i]);
        if (raw_ts <= 0) continue;
        long long bucket = raw_ts - (raw_ts % 300);

        float o = sc.Open[i];
        float h = sc.High[i];
        float l = sc.Low[i];
        float c = sc.Close[i];
        float v = sc.Volume[i];
        float d = sc.AskVolume[i] - sc.BidVolume[i];

        if (current_bucket != bucket)
        {
            if (current_bucket >= 0) bars.push_back(current);
            current_bucket = bucket;
            current.ts = bucket;
            current.open = o;
            current.high = h;
            current.low = l;
            current.close = c;
            current.volume = v;
            current.poc_vol = 0;
            current.vah = 0;
            current.val = 0;
            current.cumulative_delta = d;
        }
        else
        {
            current.high = v9_max(current.high, h);
            current.low = v9_min(current.low, l);
            current.close = c;
            current.volume += v;
            current.cumulative_delta += d;
        }
    }

    if (current_bucket >= 0) bars.push_back(current);
    return bars;
}

inline std::string v9_5min_bars_to_json(
    const std::vector<V9FiveMinBar>& bars)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "5min", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "bar_count", (int)bars.size());
    j << ",\"bars\":[";

    for (size_t i = 0; i < bars.size(); i++) {
        if (i > 0) j << ",";
        const V9FiveMinBar& b = bars[i];
        j << "{";
        json_long(j, "ts", b.ts, false);
        json_float(j, "o", b.open);
        json_float(j, "h", b.high);
        json_float(j, "l", b.low);
        json_float(j, "c", b.close);
        json_float(j, "vol", b.volume);
        json_float(j, "poc_vol", b.poc_vol);
        json_float(j, "vah", b.vah);
        json_float(j, "val", b.val);
        json_float(j, "cumulative_delta", b.cumulative_delta);
        j << "}";
    }
    j << "]}";
    return j.str();
}

inline std::string v9_5min_to_json(SCStudyInterfaceRef sc, int lookback_bars)
{
    return v9_5min_bars_to_json(v9_build_5min_ohlcv_bars(sc, lookback_bars));
}

// ─────────────────────────────────────────────────────────────
// 2. Footprint per bar (Bid×Ask per price level)
// ─────────────────────────────────────────────────────────────
// For each chart bar, breaks down volume by price level (tick increments).
// Uses sc.VolumeAtPriceForBars when available, falls back to distribution.

// v9.2.0: global budget counter — reset before each export cycle
static size_t v9_footprint_total_levels = 0;
inline void v9_footprint_reset_budget() { v9_footprint_total_levels = 0; }

inline FootprintBar v9_build_footprint_bar(
    SCStudyInterfaceRef sc, int bar_idx, float imb_threshold)
{
    const size_t FOOTPRINT_BUDGET = 10000;  // v9.2.0 safety cap
    FootprintBar fp;
    // v9.2.0: check footprint memory budget
    if (v9_footprint_total_levels >= FOOTPRINT_BUDGET) {
        fp.bar_index = bar_idx;
        fp.open = fp.high = fp.low = fp.close = 0;
        fp.total_volume = fp.total_delta = 0;
        fp.poc_price = fp.poc_volume = 0;
        fp.stacked_imb_buy = fp.stacked_imb_sell = 0;
        return fp;  // budget exceeded — return empty bar
    }

    fp.bar_index = bar_idx;
    fp.open  = sc.Open[bar_idx];
    fp.high  = sc.High[bar_idx];
    fp.low   = sc.Low[bar_idx];
    fp.close = sc.Close[bar_idx];
    fp.total_volume = sc.Volume[bar_idx];
    fp.total_delta  = sc.AskVolume[bar_idx] - sc.BidVolume[bar_idx];
    fp.poc_price  = 0;
    fp.poc_volume = 0;
    fp.stacked_imb_buy  = 0;
    fp.stacked_imb_sell = 0;

    float tick = sc.TickSize;
    if (tick <= 0) tick = 0.25f;

    // Build price levels from bar range
    float bar_ask = sc.AskVolume[bar_idx];
    float bar_bid = sc.BidVolume[bar_idx];
    float range   = fp.high - fp.low;
    int   steps   = (int)(range / tick) + 1;
    if (steps < 1) steps = 1;
    if (steps > 200) steps = 200; // safety cap

    // Use ACSIL VolumeAtPriceForBars API (element-by-element — correct signature)
    const s_VolumeAtPriceV2* p_vap = nullptr;
    int has_vap = sc.VolumeAtPriceForBars->GetVAPElementAtIndex(bar_idx, 0, &p_vap);

    float max_level_vol = 0;
    int consecutive_buy_imb  = 0;
    int consecutive_sell_imb = 0;
    int max_buy_stack  = 0;
    int max_sell_stack = 0;

    if (has_vap != 0 && p_vap != nullptr) {
        // Real VAP data available — iterate price levels (CAPPED v9.2.0)
        const int VAP_MAX_LEVELS = 500;  // v9.2.0 safety cap — MES realistic max ~400
        int vi = 0;
        while (vi < VAP_MAX_LEVELS &&
               sc.VolumeAtPriceForBars->GetVAPElementAtIndex(bar_idx, vi, &p_vap) != 0 && p_vap != nullptr) {
            FootprintLevel lvl;
            lvl.price   = p_vap->PriceInTicks * tick;
            lvl.ask_vol = (float)p_vap->AskVolume;
            lvl.bid_vol = (float)p_vap->BidVolume;
            lvl.delta   = lvl.ask_vol - lvl.bid_vol;

            // Imbalance detection (250% = 2.5x)
            lvl.imbalance_buy  = (lvl.bid_vol > 0 && lvl.ask_vol / lvl.bid_vol >= imb_threshold);
            lvl.imbalance_sell = (lvl.ask_vol > 0 && lvl.bid_vol / lvl.ask_vol >= imb_threshold);

            float total = lvl.ask_vol + lvl.bid_vol;
            if (total > max_level_vol) {
                max_level_vol = total;
                fp.poc_price  = lvl.price;
                fp.poc_volume = total;
            }

            // Stacked imbalance counting
            if (lvl.imbalance_buy) {
                consecutive_buy_imb++;
                consecutive_sell_imb = 0;
                if (consecutive_buy_imb > max_buy_stack)
                    max_buy_stack = consecutive_buy_imb;
            } else if (lvl.imbalance_sell) {
                consecutive_sell_imb++;
                consecutive_buy_imb = 0;
                if (consecutive_sell_imb > max_sell_stack)
                    max_sell_stack = consecutive_sell_imb;
            } else {
                consecutive_buy_imb  = 0;
                consecutive_sell_imb = 0;
            }

            fp.levels.push_back(lvl);
            vi++;
        }
        if (vi >= VAP_MAX_LEVELS) {
            sc.AddMessageToLog("v9.2: VAP cap reached for bar — possible data corruption", 0);
        }
    } else {
        // Fallback: distribute bar volume across price levels proportionally
        float vol_per_step = fp.total_volume / steps;
        float ask_per_step = bar_ask / steps;
        float bid_per_step = bar_bid / steps;

        for (int s = 0; s < steps; s++) {
            FootprintLevel lvl;
            lvl.price   = fp.low + s * tick;
            lvl.ask_vol = ask_per_step;
            lvl.bid_vol = bid_per_step;
            lvl.delta   = lvl.ask_vol - lvl.bid_vol;
            lvl.imbalance_buy  = (lvl.bid_vol > 0 && lvl.ask_vol / lvl.bid_vol >= imb_threshold);
            lvl.imbalance_sell = (lvl.ask_vol > 0 && lvl.bid_vol / lvl.ask_vol >= imb_threshold);

            float total = lvl.ask_vol + lvl.bid_vol;
            if (total > max_level_vol) {
                max_level_vol = total;
                fp.poc_price  = lvl.price;
                fp.poc_volume = total;
            }
            fp.levels.push_back(lvl);
        }
    }

    fp.stacked_imb_buy  = max_buy_stack;
    fp.stacked_imb_sell = max_sell_stack;

    // v9.2.0: track budget usage
    v9_footprint_total_levels += fp.levels.size();

    return fp;
}

inline std::string v9_footprint_to_json(
    const std::vector<FootprintBar>& bars, float cumulative_delta)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "footprint", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "bar_count", (int)bars.size());
    json_float(j, "cumulative_delta", cumulative_delta);
    j << ",\"bars\":[";

    for (size_t bi = 0; bi < bars.size(); bi++) {
        if (bi > 0) j << ",";
        const FootprintBar& b = bars[bi];
        j << "{";
        json_int(j, "idx", b.bar_index, false);
        json_float(j, "o", b.open);
        json_float(j, "h", b.high);
        json_float(j, "l", b.low);
        json_float(j, "c", b.close);
        json_float(j, "vol", b.total_volume);
        json_float(j, "delta", b.total_delta);
        json_float(j, "poc_price", b.poc_price);
        json_float(j, "poc_vol", b.poc_volume);
        json_int(j, "stacked_buy", b.stacked_imb_buy);
        json_int(j, "stacked_sell", b.stacked_imb_sell);
        j << ",\"levels\":[";

        for (size_t li = 0; li < b.levels.size(); li++) {
            if (li > 0) j << ",";
            const FootprintLevel& lv = b.levels[li];
            j << "{";
            json_float(j, "p", lv.price, false);
            json_float(j, "bid", lv.bid_vol);
            json_float(j, "ask", lv.ask_vol);
            json_float(j, "d", lv.delta);
            json_bool(j, "ib", lv.imbalance_buy);
            json_bool(j, "is", lv.imbalance_sell);
            j << "}";
        }
        j << "]}";
    }
    j << "]}";
    return j.str();
}

// ─────────────────────────────────────────────────────────────
// 3. Volume Profile per tick reversal bar
// ─────────────────────────────────────────────────────────────

inline std::string v9_volume_profile_to_json(
    const std::vector<FootprintBar>& fp_bars, float va_pct)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "volume_profile", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_float(j, "va_pct", va_pct);
    json_int(j, "bar_count", (int)fp_bars.size());
    j << ",\"profiles\":[";

    for (size_t bi = 0; bi < fp_bars.size(); bi++) {
        if (bi > 0) j << ",";
        const FootprintBar& fb = fp_bars[bi];
        j << "{";
        json_int(j, "bar_idx", fb.bar_index, false);

        // Compute VA from levels
        float total_vol = 0;
        for (size_t li = 0; li < fb.levels.size(); li++)
            total_vol += fb.levels[li].ask_vol + fb.levels[li].bid_vol;

        float va_target = total_vol * (va_pct / 100.0f);

        // Find POC level index
        int poc_idx = 0;
        float max_vol = 0;
        for (size_t li = 0; li < fb.levels.size(); li++) {
            float lv = fb.levels[li].ask_vol + fb.levels[li].bid_vol;
            if (lv > max_vol) { max_vol = lv; poc_idx = (int)li; }
        }

        // Expand from POC to build Value Area
        float va_vol = max_vol;
        int va_top = poc_idx, va_bot = poc_idx;
        while (va_vol < va_target) {
            float up_vol = (va_top + 1 < (int)fb.levels.size())
                ? fb.levels[va_top + 1].ask_vol + fb.levels[va_top + 1].bid_vol : 0;
            float dn_vol = (va_bot - 1 >= 0)
                ? fb.levels[va_bot - 1].ask_vol + fb.levels[va_bot - 1].bid_vol : 0;

            if (up_vol >= dn_vol && va_top + 1 < (int)fb.levels.size()) {
                va_top++;
                va_vol += up_vol;
            } else if (va_bot - 1 >= 0) {
                va_bot--;
                va_vol += dn_vol;
            } else {
                break;
            }
        }

        float vah = (va_top < (int)fb.levels.size()) ? fb.levels[va_top].price : fb.high;
        float val_price = (va_bot >= 0 && va_bot < (int)fb.levels.size()) ? fb.levels[va_bot].price : fb.low;

        json_float(j, "poc", fb.poc_price);
        json_float(j, "poc_vol", fb.poc_volume);
        json_float(j, "vah", vah);
        json_float(j, "val", val_price);
        json_float(j, "total_vol", total_vol);

        j << ",\"levels\":[";
        for (size_t li = 0; li < fb.levels.size(); li++) {
            if (li > 0) j << ",";
            float lv = fb.levels[li].ask_vol + fb.levels[li].bid_vol;
            float pct = (total_vol > 0) ? (lv / total_vol * 100.0f) : 0;
            j << "{";
            json_float(j, "p", fb.levels[li].price, false);
            json_float(j, "v", lv);
            json_float(j, "pct", pct);
            json_bool(j, "poc", (int)li == poc_idx);
            json_bool(j, "va", (int)li >= va_bot && (int)li <= va_top);
            j << "}";
        }
        j << "]}";
    }
    j << "]}";
    return j.str();
}

// ─────────────────────────────────────────────────────────────
// 4. Imbalance flags summary (250%+ ratio)
// ─────────────────────────────────────────────────────────────

inline std::string v9_imbalance_flags_to_json(
    const std::vector<FootprintBar>& fp_bars)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "imbalance_flags", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));

    int total_buy_imb = 0, total_sell_imb = 0;
    int bars_with_imb = 0;

    j << ",\"bars\":[";
    bool first_bar = true;
    for (size_t bi = 0; bi < fp_bars.size(); bi++) {
        const FootprintBar& fb = fp_bars[bi];
        bool has_imb = false;
        for (size_t li = 0; li < fb.levels.size(); li++) {
            if (fb.levels[li].imbalance_buy || fb.levels[li].imbalance_sell) {
                has_imb = true;
                if (fb.levels[li].imbalance_buy) total_buy_imb++;
                if (fb.levels[li].imbalance_sell) total_sell_imb++;
            }
        }
        if (!has_imb) continue;

        bars_with_imb++;
        if (!first_bar) j << ",";
        first_bar = false;
        j << "{";
        json_int(j, "bar_idx", fb.bar_index, false);
        json_float(j, "price", fb.close);
        json_int(j, "stacked_buy", fb.stacked_imb_buy);
        json_int(j, "stacked_sell", fb.stacked_imb_sell);
        j << ",\"levels\":[";

        bool first_lvl = true;
        for (size_t li = 0; li < fb.levels.size(); li++) {
            const FootprintLevel& lv = fb.levels[li];
            if (!lv.imbalance_buy && !lv.imbalance_sell) continue;
            if (!first_lvl) j << ",";
            first_lvl = false;
            j << "{";
            json_float(j, "p", lv.price, false);
            json_float(j, "bid", lv.bid_vol);
            json_float(j, "ask", lv.ask_vol);
            float ratio = (lv.imbalance_buy && lv.bid_vol > 0)
                ? lv.ask_vol / lv.bid_vol
                : (lv.imbalance_sell && lv.ask_vol > 0) ? lv.bid_vol / lv.ask_vol : 0;
            json_float(j, "ratio", ratio);
            json_str(j, "side", lv.imbalance_buy ? "BUY" : "SELL");
            j << "}";
        }
        j << "]}";
    }
    j << "]";
    json_int(j, "total_buy_imbalances", total_buy_imb);
    json_int(j, "total_sell_imbalances", total_sell_imb);
    json_int(j, "bars_with_imbalances", bars_with_imb);
    j << "}";
    return j.str();
}

// ─────────────────────────────────────────────────────────────
// 5. Stacked imbalance counts (3+ consecutive)
// ─────────────────────────────────────────────────────────────

inline std::string v9_stacked_imbalances_to_json(
    const std::vector<FootprintBar>& fp_bars, int min_stack)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "stacked_imbalances", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));
    json_int(j, "min_stack", min_stack);

    int total_stacked = 0;
    j << ",\"stacks\":[";
    bool first = true;

    for (size_t bi = 0; bi < fp_bars.size(); bi++) {
        const FootprintBar& fb = fp_bars[bi];
        if (fb.stacked_imb_buy < min_stack && fb.stacked_imb_sell < min_stack)
            continue;

        total_stacked++;
        if (!first) j << ",";
        first = false;

        j << "{";
        json_int(j, "bar_idx", fb.bar_index, false);
        json_float(j, "price", fb.close);
        json_int(j, "buy_stack", fb.stacked_imb_buy);
        json_int(j, "sell_stack", fb.stacked_imb_sell);
        json_str(j, "dominant",
            (fb.stacked_imb_buy >= min_stack && fb.stacked_imb_sell >= min_stack) ? "BOTH"
            : (fb.stacked_imb_buy >= min_stack) ? "BUY" : "SELL");
        json_float(j, "poc", fb.poc_price);
        j << "}";
    }
    j << "]";
    json_int(j, "total_stacked_bars", total_stacked);
    j << "}";
    return j.str();
}

// ─────────────────────────────────────────────────────────────
// 6. Cumulative Delta running total
// ─────────────────────────────────────────────────────────────

inline std::string v9_cumulative_delta_to_json(
    SCStudyInterfaceRef sc, int /*lookback — ignored, session-anchored now*/)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "cumulative_delta", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));

    // Session-anchored: find first bar of today's session
    SCDateTime today = sc.BaseDateTimeIn[sc.Index].GetDate();
    int session_start = 0;
    for (int i = sc.Index; i >= 0; i--) {
        if (sc.BaseDateTimeIn[i].GetDate() < today) {
            session_start = i + 1;
            break;
        }
    }

    float running = 0;
    float peak = 0, trough = 0;

    // SCDateTime → unix epoch (UTC): excel days since 1899-12-30,
    // 25569 days between 1899-12-30 and 1970-01-01.
    auto sc_to_unix = [&](int idx) -> long long {
        double scdt = sc.BaseDateTimeIn[idx].GetAsDouble();
        return (long long)((scdt - 25569.0) * 86400.0);
    };

    j << ",\"points\":[";
    bool first = true;
    // P30 (2026-05-20): emit ONE point per host-chart bar (not every 5th).
    // Cockpit CVD pane needs 5-min granularity because the host chart is a
    // 5-min Globex 24h chart; the old `% 5 == 0` filter produced 25-min
    // candles that the user reported as "wrong period". File-size cost is
    // ~5× (≈10 KB for a 24h Globex session) — negligible vs the alignment win.
    // Also emit explicit `t` (unix UTC sec) per point so the backend stops
    // having to guess `output_interval` (was V9_CVD_PERIOD_S fallback).
    for (int i = session_start; i <= sc.Index; i++) {
        float d = sc.AskVolume[i] - sc.BidVolume[i];
        running += d;

        peak   = v9_max(peak, running);
        trough = v9_min(trough, running);

        if (!first) j << ",";
        first = false;
        j << "{";
        json_int(j, "i", i, false);
        json_long(j, "t", sc_to_unix(i));
        json_float(j, "d", d);
        json_float(j, "cum", running);
        json_float(j, "p", sc.Close[i]);
        j << "}";
    }
    j << "]";

    // Top-level cadence hint for the frontend (300 = 5 min host bar).
    json_int(j, "output_interval", 300);

    json_float(j, "current_delta", running);
    json_float(j, "session_delta", running);  // same as current — all session-anchored
    json_float(j, "peak", peak);
    json_float(j, "trough", trough);

    // Divergence: price up but delta down (or vice versa)
    float price_change = sc.Close[sc.Index] - sc.Close[session_start];
    bool divergence = (price_change > 0 && running < 0) || (price_change < 0 && running > 0);
    json_bool(j, "divergence", divergence);
    json_str(j, "trend",
        (running > 100) ? "BULLISH" :
        (running < -100) ? "BEARISH" : "NEUTRAL");

    j << "}";
    return j.str();
}

// ====== v9_woodies_export.h (inlined) ======
// v9_woodies_export.h — MEMS26 V9 Woodies CCI export (30-min synthetic bars)
// Version: v9.3.1-p30.10
// Updated: 2026-05-19 (P30.10 HUD: ccidiff H/mid/L, predictor H/L, prev_ohlc, low angle)
// ProjHigh/ProjLow: require Sierra study subgraphs — see docs/handoff export matrix.
// Computes CCI-14, TCCI-6, LSMA-25, EMA-34, Sidewinder, ChopZone,
// trend state, CCI predictor, ZLR + HFE detection from 3-min chart bars.
// ACSIL-safe: uses v9_max/v9_min/v9_abs, no std::max/min.


// ── Sierra study readings for current bar (replaces computed values) ──
struct WoodiesSierraStudies {
    bool valid;         // true if read from Sierra succeeded
    float cci_14;       // Study ID:4 (CCI period=14) SG0
    float cci_6;        // Study ID:10 (CCI period=6 / TCCI) SG0
    float ema_34;       // Study ID:3 (Woodies EMA) SG0
    float lsma_25;      // Study ID:2 (LSMA / Moving Average - Linear Regression) SG0
    float sidewinder;   // Study ID:6 (Sidewinder) SG0
    float chopzone;     // Study ID:7 (Chop Zone) SG0
    float proj_hi;      // Study ID:9 (Woodies Panel) SG1 — projected high
    float proj_lo;      // Study ID:9 (Woodies Panel) SG2 — projected low
    float predictor_hi; // computed from Sierra CCI values
    float predictor_lo; // computed from Sierra CCI values
    float cci_14_prev;  // CCI-14 one bar back (for predictor + trend)
};

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
        {
            long long raw_ts = v9_sc_datetime_to_unix(sc.BaseDateTimeIn[b]);
            bar.timestamp = raw_ts > 0 ? (raw_ts - (raw_ts % 300)) : (long long)time(nullptr);
        }
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
static const int WOODIES_5MIN_PERIOD = 1;  // 1:1 with chart bar (5-min chart)

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
        {
            long long raw_ts = v9_sc_datetime_to_unix(sc.BaseDateTimeIn[b]);
            bar.timestamp = raw_ts > 0 ? (raw_ts - (raw_ts % 300)) : (long long)time(nullptr);
        }
        bars.push_back(bar);
    }
    return bars;
}

inline std::string v9_woodies_5min_to_json(SCStudyInterfaceRef sc, int max_history,
                                            const WoodiesSierraStudies* sierra = nullptr,
                                            int woodies_chart = 0, int proj_study_id = 0)
{
    std::vector<Woodies30MinBar> bars = v9_build_5min_bars(sc, max_history + 10);
    int n = (int)bars.size();

    // ── Sierra study arrays for ALL bars ──
    // Key: use GetContainingIndexForDateTimeIndex to map DLL bar index → chart #12 bar index
    int wc = (woodies_chart > 0) ? woodies_chart : 0;
    SCFloatArray s_cci14_arr, s_cci6_arr, s_ema34_arr, s_lsma25_arr;
    SCFloatArray s_swi_arr, s_czi_arr, s_proj_hi_arr, s_proj_lo_arr;
    SCFloatArray s_trend_up_arr, s_trend_down_arr, s_trend_neutral_arr;
    SCFloatArray s_pred_hi_arr, s_pred_lo_arr;
    bool have_sierra = false;
    if (wc > 0) {
        sc.GetStudyArrayFromChartUsingID(wc, 4, 0, s_cci14_arr);    // CCI-14
        sc.GetStudyArrayFromChartUsingID(wc, 10, 0, s_cci6_arr);    // TCCI
        sc.GetStudyArrayFromChartUsingID(wc, 3, 0, s_ema34_arr);    // EMA-34
        sc.GetStudyArrayFromChartUsingID(wc, 2, 0, s_lsma25_arr);   // LSMA
        sc.GetStudyArrayFromChartUsingID(wc, 6, 5, s_swi_arr);      // Sidewinder
        sc.GetStudyArrayFromChartUsingID(wc, 7, 2, s_czi_arr);      // ChopZone
        sc.GetStudyArrayFromChartUsingID(wc, 1, 1, s_trend_up_arr); // TrendUp
        sc.GetStudyArrayFromChartUsingID(wc, 1, 2, s_trend_down_arr);
        sc.GetStudyArrayFromChartUsingID(wc, 1, 3, s_trend_neutral_arr);
        sc.GetStudyArrayFromChartUsingID(wc, 11, 0, s_pred_hi_arr); // CCI Predictor SG0
        sc.GetStudyArrayFromChartUsingID(wc, 11, 1, s_pred_lo_arr); // CCI Predictor SG1
        have_sierra = (s_cci14_arr.GetArraySize() > 0);
        if (proj_study_id > 0) {
            sc.GetStudyArrayFromChartUsingID(wc, proj_study_id, 1, s_proj_hi_arr);
            sc.GetStudyArrayFromChartUsingID(wc, proj_study_id, 2, s_proj_lo_arr);
        }
    }

    // Helper: read Sierra float at mapped index, 0 if unavailable
    #define S_VAL(arr, idx) ((idx) >= 0 && (idx) < (arr).GetArraySize() ? (arr)[(idx)] : 0.0f)

    // Map DLL bar index → Woodies chart bar index using Sierra's cross-chart mapping
    // GetContainingIndexForDateTimeIndex maps a datetime index from THIS chart to target chart
    auto mapIdx = [&](int dll_bar_idx) -> int {
        if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
        return sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
    };

    // Pre-compute CCI-14 history for ZLR/HFE detection — Sierra when available
    std::vector<float> cci14_hist;
    cci14_hist.reserve(n);
    for (int i = 0; i < n; i++) {
        int mi = mapIdx(bars[i].chart_bar_start);
        float sv = S_VAL(s_cci14_arr, mi);
        cci14_hist.push_back((have_sierra && sv != 0) ? sv : v9_calc_cci(bars, i, 14));
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

        int mi = mapIdx(bars[bi].chart_bar_start);  // mapped index in Woodies chart

        // Sierra native values with local fallback
        float cci14, cci6, ema34, lsma25, swi, czi;
        if (have_sierra) {
            float sv;
            sv = S_VAL(s_cci14_arr, mi);  cci14  = (sv != 0) ? sv : v9_calc_cci(bars, bi, 14);
            sv = S_VAL(s_cci6_arr, mi);   cci6   = (sv != 0) ? sv : v9_calc_cci(bars, bi, 6);
            sv = S_VAL(s_ema34_arr, mi);  ema34  = (sv != 0) ? sv : v9_calc_ema(bars, bi, 34);
            sv = S_VAL(s_lsma25_arr, mi); lsma25 = (sv != 0) ? sv : v9_calc_lsma(bars, bi, 25);
            swi = S_VAL(s_swi_arr, mi);
            czi = S_VAL(s_czi_arr, mi);
        } else {
            cci14  = v9_calc_cci(bars, bi, 14);
            cci6   = v9_calc_cci(bars, bi, 6);
            ema34  = v9_calc_ema(bars, bi, 34);
            lsma25 = v9_calc_lsma(bars, bi, 25);
            swi    = v9_calc_sidewinder(cci14, (bi >= 3) ? v9_calc_cci(bars, bi-3, 14) : 0);
            czi    = v9_calc_chopzone(bars, bi, ema34);
        }
        float cci14_prev = (bi > 0) ? cci14_hist[bi - 1] : 0;
        // CCI Predictor from Sierra Study ID:11 (SG0=high, SG1=low)
        float pred_hi = S_VAL(s_pred_hi_arr, mi);
        float pred_lo = S_VAL(s_pred_lo_arr, mi);
        float predictor = (pred_hi != 0) ? pred_hi : v9_cci_predictor(cci14, cci14_prev);

        // Trend from Sierra native (Study ID:1 TrendUp/Down/Neutral)
        const char* trend;
        if (have_sierra && s_trend_up_arr.GetArraySize() > mi) {
            float tu = S_VAL(s_trend_up_arr, mi);
            float td = S_VAL(s_trend_down_arr, mi);
            float tn = S_VAL(s_trend_neutral_arr, mi);
            if (tu != 0)      trend = "RED";
            else if (td != 0) trend = "YELLOW";
            else if (tn != 0) trend = "BLUE";
            else               trend = "GRAY";
        } else {
            trend = v9_woodies_trend_state(cci14, cci14_prev, swi);
        }

        ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), bi + 1, 12);
        HFEResult hfe = v9_detect_hfe(cci14_hist.data(), bi + 1, 12);

        // Proj from Pivot Points (daily = same value for all bars today)
        float phi = S_VAL(s_proj_hi_arr, mi);
        float plo = S_VAL(s_proj_lo_arr, mi);

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
        if (pred_hi != 0) json_float(j, "predictor_cci_high", pred_hi);
        if (pred_lo != 0) json_float(j, "predictor_cci_low", pred_lo);
        json_bool(j, "zlr_detected", zlr.detected);
        json_str(j, "zlr_direction", zlr.direction);
        json_bool(j, "hfe_detected", hfe.detected);
        json_str(j, "hfe_direction", hfe.direction);
        json_int(j, "hfe_extreme_bars_ago", hfe.extreme_bars_ago);
        if (phi != 0) json_float(j, "proj_hi", phi);
        else { j << ",\"proj_hi\":null"; }
        if (plo != 0) json_float(j, "proj_lo", plo);
        else { j << ",\"proj_lo\":null"; }
        v9_woodies_json_hud_fields(j, bars, bi);
        j << "}";
    }
    j << "]";

    // current_bar (last) — use Sierra study values when available
    if (n > 0) {
        int ci = n - 1;
        // Computed values (fallback)
        float cci14     = v9_calc_cci(bars, ci, 14);
        float cci6      = v9_calc_cci(bars, ci, 6);
        float ema34     = v9_calc_ema(bars, ci, 34);
        float lsma25    = v9_calc_lsma(bars, ci, 25);
        float cci14_prev = (ci > 0) ? v9_calc_cci(bars, ci - 1, 14) : 0;
        float cci14_3ago = (ci >= 3) ? v9_calc_cci(bars, ci - 3, 14) : 0;
        float swi       = v9_calc_sidewinder(cci14, cci14_3ago);
        float czi       = v9_calc_chopzone(bars, ci, ema34);
        float predictor = v9_cci_predictor(cci14, cci14_prev);

        // Override with Sierra native study values when available
        float s_proj_hi = 0, s_proj_lo = 0;
        float s_ccidiff = 0;
        if (sierra && sierra->valid) {
            if (sierra->cci_14 != 0)    cci14  = sierra->cci_14;
            if (sierra->cci_6 != 0)     cci6   = sierra->cci_6;
            if (sierra->ema_34 != 0)    ema34  = sierra->ema_34;
            if (sierra->lsma_25 != 0)   lsma25 = sierra->lsma_25;
            if (sierra->sidewinder != 0) swi   = sierra->sidewinder;
            if (sierra->chopzone != 0)  czi    = sierra->chopzone;
            // proj from Woodies Panel — usually 0; prefer Pivot Points study below
            s_proj_hi = sierra->proj_hi;
            s_proj_lo = sierra->proj_lo;
            // CCIDiff from Sierra = CCI14 - CCI6 (exact Sierra values)
            s_ccidiff = sierra->cci_14 - sierra->cci_6;
            // Predictor from Sierra CCI (linear extrapolation)
            if (sierra->cci_14_prev != 0) {
                cci14_prev = sierra->cci_14_prev;
                predictor = v9_cci_predictor(cci14, cci14_prev);
            }
        }

        // Trend + proj from Sierra via mapped index
        int cb_mi = mapIdx(bars[ci].chart_bar_start);
        const char* trend;
        if (have_sierra && s_trend_up_arr.GetArraySize() > cb_mi) {
            float tu = S_VAL(s_trend_up_arr, cb_mi);
            float td = S_VAL(s_trend_down_arr, cb_mi);
            float tn = S_VAL(s_trend_neutral_arr, cb_mi);
            if (tu != 0)      trend = "RED";
            else if (td != 0) trend = "YELLOW";
            else if (tn != 0) trend = "BLUE";
            else               trend = "GRAY";
        } else {
            trend = v9_woodies_trend_state(cci14, cci14_prev, swi);
        }
        if (s_proj_hi == 0) {
            s_proj_hi = S_VAL(s_proj_hi_arr, cb_mi);
            s_proj_lo = S_VAL(s_proj_lo_arr, cb_mi);
        }

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
        // Override CCIDiff with Sierra-accurate values when available
        if (sierra && sierra->valid && s_ccidiff != 0) {
            json_float(j, "ccidiff", s_ccidiff);
            json_float(j, "ccidiff_h", s_ccidiff);
            json_float(j, "ccidiff_l", s_ccidiff);
        }
        // Projected High-Low (from Woodies Panel study)
        if (s_proj_hi != 0) json_float(j, "proj_hi", s_proj_hi);
        else { j << ",\"proj_hi\":null"; }
        if (s_proj_lo != 0) json_float(j, "proj_lo", s_proj_lo);
        else { j << ",\"proj_lo\":null"; }
        json_bool(j, "sierra_source", sierra != nullptr && sierra->valid);
        // Debug: array sizes and trend arrays availability
        json_int(j, "_dbg_cci14_arr_size", s_cci14_arr.GetArraySize());
        json_int(j, "_dbg_trend_up_arr_size", s_trend_up_arr.GetArraySize());
        json_int(j, "_dbg_chart_bar_idx", bars[ci].chart_bar_start);
        json_int(j, "_dbg_total_chart_bars", sc.Index + 1);

        // ── DEBUG: dump raw Sierra subgraph values for current bar ──
        // Remove after subgraph mapping is confirmed correct.
        if (wc > 0) {
            int dbg_idx = bars[ci].chart_bar_start;
            j << ",\"_debug\":{";
            // Study ID:1 (Woodies CCI Trend) — dump SG0 through SG9
            j << "\"study1_woodies_trend\":{";
            for (int sg = 0; sg <= 9; sg++) {
                SCFloatArray dbg_arr;
                sc.GetStudyArrayFromChartUsingID(wc, 1, sg, dbg_arr);
                float val = (dbg_idx >= 0 && dbg_idx < dbg_arr.GetArraySize()) ? dbg_arr[dbg_idx] : -999;
                if (sg > 0) j << ",";
                j << "\"SG" << sg << "\":" << val;
            }
            j << "}";
            // Study ID:9 (Woodies Panel) — dump SG0 through SG5
            j << ",\"study9_panel\":{";
            for (int sg = 0; sg <= 5; sg++) {
                SCFloatArray dbg_arr;
                sc.GetStudyArrayFromChartUsingID(wc, 9, sg, dbg_arr);
                float val = (dbg_idx >= 0 && dbg_idx < dbg_arr.GetArraySize()) ? dbg_arr[dbg_idx] : -999;
                if (sg > 0) j << ",";
                j << "\"SG" << sg << "\":" << val;
            }
            j << "}";
            // Study ID:12 (Pivot Points-Daily) — dump SG0 through SG9
            j << ",\"study12_pivot\":{";
            for (int sg = 0; sg <= 9; sg++) {
                SCFloatArray dbg_arr;
                sc.GetStudyArrayFromChartUsingID(wc, 12, sg, dbg_arr);
                float val = (dbg_idx >= 0 && dbg_idx < dbg_arr.GetArraySize()) ? dbg_arr[dbg_idx] : -999;
                if (sg > 0) j << ",";
                j << "\"SG" << sg << "\":" << val;
            }
            j << "}";
            j << "}";
        }

        j << "}";
    }

    #undef S_VAL

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

// ====== ImbLevel struct (file scope — Bug #16 fix) ======
struct ImbLevel { float price; float buy_vol; float sell_vol; float ratio; };

// ====== MES_AI_DataExport.cpp main function ======
// MES_AI_DataExport.cpp — v9.4.2-p30.11 (G1/G2/G4: proj H/L, TPO validation, va_ok)
// Sierra Chart ACSIL Study — 3 minute chart + V9 tick reversal + footprint exports
// REAL-TIME: exports every N seconds (ExportIntervalSec), NO "last bar only" guard.
// מייצא: MTF, CVD, VWAP, Imbalance, Market Profile, Woodi, Levels
//         + V9: Tick Reversal (15/12), Footprint, Volume Profile,
//               Imbalance Flags, Stacked Imbalances, Cumulative Delta

#include <fstream>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <map>
#include <vector>
#include <algorithm>


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

    if (sc.SetDefaults)
    {
        sc.GraphName        = "MES AI Data Export v9.4.2-p30.11";
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

        // Sierra TPO Value Area Lines subgraph indices (Sierra internal):
        //   SG1 = POC, SG2 = VAH, SG3 = VAL
        // Sierra Initial Balance subgraph indices:
        //   SG1 = IB High, SG2 = IB Low
        // These are 0-based in ACSIL: SG1=0, SG2=1, SG3=2

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
            sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 0, ib_high_arr);
            sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 1, ib_low_arr);
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

        j << ",\"previous_session\":{";
        json_bool(j, "found", y_valid, false);
        json_float(j, "poc", y_poc);
        json_float(j, "vah", y_vah);
        json_float(j, "val", y_val);
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
}
