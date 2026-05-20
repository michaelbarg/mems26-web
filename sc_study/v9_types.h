// v9_types.h — MEMS26 V9 shared types and helpers
// ACSIL-safe: no std::max/min, no STL that Sierra macros break
#pragma once

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
