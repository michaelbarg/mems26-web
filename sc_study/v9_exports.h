// v9_exports.h — MEMS26 V9 new export functions
// Each function builds JSON and writes to v9_export/ directory
// ACSIL-safe: uses v9_max/v9_min, not std::max/std::min
#pragma once

#include "sierrachart.h"
#include "v9_types.h"

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
            current.timestamp = (long long)sc.BaseDateTimeIn[i].IsNotEmpty()
                ? (long long)sc.BaseDateTimeIn[i].GetAsDouble() * 86400
                : time(nullptr);
            bars.push_back(current);

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
// 2. Footprint per bar (Bid×Ask per price level)
// ─────────────────────────────────────────────────────────────
// For each chart bar, breaks down volume by price level (tick increments).
// Uses sc.VolumeAtPriceForBars when available, falls back to distribution.

inline FootprintBar v9_build_footprint_bar(
    SCStudyInterfaceRef sc, int bar_idx, float imb_threshold)
{
    FootprintBar fp;
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

    // Try to use VolumeAtPriceForBars for per-level data
    const s_VolumeAtPriceV2* vap = nullptr;
    int vap_count = 0;

    // Use sc.VolumeAtPriceForBars if available
    unsigned int num_vap = 0;
    const s_VolumeAtPriceV2* vap_array = nullptr;
    if (sc.VolumeAtPriceForBars != nullptr) {
        vap_array = sc.VolumeAtPriceForBars->GetVAPArrayAtBarIndex(bar_idx, &num_vap);
    }

    float max_level_vol = 0;
    int consecutive_buy_imb  = 0;
    int consecutive_sell_imb = 0;
    int max_buy_stack  = 0;
    int max_sell_stack = 0;

    if (vap_array != nullptr && num_vap > 0) {
        // Real VAP data available
        for (unsigned int vi = 0; vi < num_vap; vi++) {
            FootprintLevel lvl;
            lvl.price   = vap_array[vi].PriceInTicks * tick;
            lvl.ask_vol = (float)vap_array[vi].AskVolume;
            lvl.bid_vol = (float)vap_array[vi].BidVolume;
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
    SCStudyInterfaceRef sc, int lookback)
{
    std::ostringstream j;
    j << std::fixed << std::setprecision(2);
    j << "{";
    json_str(j, "type", "cumulative_delta", false);
    json_str(j, "version", V9_VERSION);
    json_long(j, "export_ts", (long long)time(nullptr));

    int start = v9_max_i(0, sc.Index - lookback);
    float running = 0;
    float session_delta = 0;
    float peak = 0, trough = 0;
    SCDateTime today = sc.BaseDateTimeIn[sc.Index].GetDate();

    j << ",\"points\":[";
    bool first = true;
    for (int i = start; i <= sc.Index; i++) {
        float d = sc.AskVolume[i] - sc.BidVolume[i];
        running += d;
        if (sc.BaseDateTimeIn[i].GetDate() == today)
            session_delta += d;

        peak   = v9_max(peak, running);
        trough = v9_min(trough, running);

        // Only emit every 5th point to keep file small
        if ((i - start) % 5 == 0 || i == sc.Index) {
            if (!first) j << ",";
            first = false;
            j << "{";
            json_int(j, "i", i, false);
            json_float(j, "d", d);
            json_float(j, "cum", running);
            json_float(j, "p", sc.Close[i]);
            j << "}";
        }
    }
    j << "]";

    json_float(j, "current_delta", running);
    json_float(j, "session_delta", session_delta);
    json_float(j, "peak", peak);
    json_float(j, "trough", trough);

    // Divergence: price up but delta down (or vice versa)
    float price_change = sc.Close[sc.Index] - sc.Close[start];
    bool divergence = (price_change > 0 && running < 0) || (price_change < 0 && running > 0);
    json_bool(j, "divergence", divergence);
    json_str(j, "trend",
        (running > 100) ? "BULLISH" :
        (running < -100) ? "BEARISH" : "NEUTRAL");

    j << "}";
    return j.str();
}
