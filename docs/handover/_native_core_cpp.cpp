#include <algorithm>
#include <cctype>
#include <cstring>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <queue>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

static unsigned int compare_ohlcv_diff_mask(
    double local_open,
    double local_high,
    double local_low,
    double local_close,
    double local_volume,
    double mexc_open,
    double mexc_high,
    double mexc_low,
    double mexc_close,
    double mexc_volume
) {
    unsigned int mask = 0U;
    if (local_open != mexc_open) mask |= 1U;
    if (local_high != mexc_high) mask |= 2U;
    if (local_low != mexc_low) mask |= 4U;
    if (local_close != mexc_close) mask |= 8U;
    if (local_volume != mexc_volume) mask |= 16U;
    return mask;
}

std::string extract_json_string_field(const std::string &payload, const char *field) {
    const std::string key = std::string("\"") + field + "\"";
    size_t pos = payload.find(key);
    if (pos == std::string::npos) {
        return "";
    }
    pos = payload.find(':', pos + key.size());
    if (pos == std::string::npos) {
        return "";
    }
    pos += 1;
    while (pos < payload.size() && (payload[pos] == ' ' || payload[pos] == '\t' || payload[pos] == '\n' || payload[pos] == '\r')) {
        pos += 1;
    }
    if (pos >= payload.size() || payload[pos] != '"') {
        return "";
    }
    pos += 1;
    std::string out;
    out.reserve(32);
    bool escaped = false;
    for (; pos < payload.size(); ++pos) {
        const char c = payload[pos];
        if (escaped) {
            out.push_back(c);
            escaped = false;
            continue;
        }
        if (c == '\\') {
            escaped = true;
            continue;
        }
        if (c == '"') {
            break;
        }
        out.push_back(c);
    }
    return out;
}

bool extract_json_number_field(const std::string &payload, const char *field, double &out) {
    const std::string key = std::string("\"") + field + "\"";
    size_t pos = payload.find(key);
    if (pos == std::string::npos) {
        return false;
    }
    pos = payload.find(':', pos + key.size());
    if (pos == std::string::npos) {
        return false;
    }
    pos += 1;
    while (pos < payload.size() && std::isspace(static_cast<unsigned char>(payload[pos]))) {
        pos += 1;
    }
    if (pos >= payload.size()) {
        return false;
    }
    const char *start = payload.c_str() + pos;
    char *end = nullptr;
    const double v = std::strtod(start, &end);
    if (end == start) {
        return false;
    }
    out = v;
    return true;
}

bool extract_json_int64_field(const std::string &payload, const char *field, long long &out) {
    double dv = 0.0;
    if (extract_json_number_field(payload, field, dv)) {
        out = static_cast<long long>(dv);
        return true;
    }
    // MEXC sends some integer fields as JSON strings (e.g. "i": "14036086901").
    // Fall back to extracting the quoted string and parsing it as int64.
    const std::string key = std::string("\"") + field + "\"";
    size_t pos = payload.find(key);
    if (pos == std::string::npos) return false;
    pos = payload.find(':', pos + key.size());
    if (pos == std::string::npos) return false;
    pos += 1;
    while (pos < payload.size() && std::isspace(static_cast<unsigned char>(payload[pos]))) pos += 1;
    if (pos >= payload.size() || payload[pos] != '"') return false;
    pos += 1;
    const char *start = payload.c_str() + pos;
    char *end = nullptr;
    const long long v = std::strtoll(start, &end, 10);
    if (end == start) return false;
    out = v;
    return true;
}

std::vector<std::string> extract_data_objects(const std::string &payload) {
    std::vector<std::string> rows;
    const std::string key = "\"data\"";
    size_t pos = payload.find(key);
    if (pos == std::string::npos) {
        return rows;
    }
    pos = payload.find(':', pos + key.size());
    if (pos == std::string::npos) {
        return rows;
    }
    pos += 1;
    while (pos < payload.size() && std::isspace(static_cast<unsigned char>(payload[pos]))) {
        pos += 1;
    }
    if (pos >= payload.size()) {
        return rows;
    }

    const char first = payload[pos];
    if (first == '{') {
        int depth = 0;
        bool in_string = false;
        bool escaped = false;
        size_t start = pos;
        for (size_t i = pos; i < payload.size(); ++i) {
            const char c = payload[i];
            if (in_string) {
                if (escaped) {
                    escaped = false;
                } else if (c == '\\') {
                    escaped = true;
                } else if (c == '"') {
                    in_string = false;
                }
                continue;
            }
            if (c == '"') {
                in_string = true;
                continue;
            }
            if (c == '{') {
                depth += 1;
            } else if (c == '}') {
                depth -= 1;
                if (depth == 0) {
                    rows.emplace_back(payload.substr(start, i - start + 1));
                    return rows;
                }
            }
        }
        return rows;
    }

    if (first != '[') {
        return rows;
    }

    bool in_string = false;
    bool escaped = false;
    int depth = 0;
    size_t obj_start = std::string::npos;
    for (size_t i = pos + 1; i < payload.size(); ++i) {
        const char c = payload[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (c == '\\') {
                escaped = true;
            } else if (c == '"') {
                in_string = false;
            }
            continue;
        }
        if (c == '"') {
            in_string = true;
            continue;
        }
        if (c == '{') {
            if (depth == 0) {
                obj_start = i;
            }
            depth += 1;
            continue;
        }
        if (c == '}') {
            if (depth > 0) {
                depth -= 1;
                if (depth == 0 && obj_start != std::string::npos) {
                    rows.emplace_back(payload.substr(obj_start, i - obj_start + 1));
                    obj_start = std::string::npos;
                }
            }
            continue;
        }
        if (c == ']' && depth == 0) {
            break;
        }
    }
    return rows;
}

py::tuple extract_frame_meta(py::bytes payload_bytes) {
    const std::string payload = payload_bytes;
    const std::string channel = extract_json_string_field(payload, "channel");
    const std::string symbol = extract_json_string_field(payload, "symbol");
    return py::make_tuple(channel, symbol);
}

static inline long long normalize_ts_ms(long long ts) {
    return ts < 1000000000000LL ? ts * 1000LL : ts;
}


static inline long long interval_ms_from_code(unsigned char code) {
    if (code == 1) return 60000LL;
    if (code == 5) return 300000LL;
    if (code == 15) return 900000LL;
    if (code == 60) return 3600000LL;
    return 0;
}

static inline std::string interval_name_from_code(unsigned char code) {
    if (code == 1) return "Min1";
    if (code == 5) return "Min5";
    if (code == 15) return "Min15";
    if (code == 60) return "Min60";
    return "";
}

static inline unsigned char interval_code_from_name(const std::string &name) {
    if (name == "Min1") return 1;
    if (name == "Min5") return 5;
    if (name == "Min15") return 15;
    if (name == "Min60") return 60;
    return 0;
}

struct StateVal {
    std::string symbol;
    std::string interval;
    long long minute_ms;
    double open_v;
    double high_v;
    double low_v;
    double close_v;
    double volume_v;
    int trades;
    long long open_ts_ms;
    long long close_ts_ms;
    unsigned long long open_order_key;
    unsigned long long close_order_key;
    bool open_has_trade_id;
    bool close_has_trade_id;
};

struct SnapshotVal {
    std::string symbol;
    std::string interval;
    long long minute_ms;
    double open_v;
    double high_v;
    double low_v;
    double close_v;
    double volume_v;
};

struct FpVal {
    double open_v;
    double high_v;
    double low_v;
    double close_v;
    double volume_v;
    bool operator==(const FpVal &o) const {
        return open_v == o.open_v && high_v == o.high_v && low_v == o.low_v && close_v == o.close_v && volume_v == o.volume_v;
    }
};

struct DueKey {
    std::string symbol;
    unsigned char interval_code;
    long long minute_ms;
    bool operator==(const DueKey &o) const {
        return interval_code == o.interval_code && minute_ms == o.minute_ms && symbol == o.symbol;
    }
};

struct DueKeyHash {
    std::size_t operator()(const DueKey &k) const {
        std::size_t h = std::hash<std::string>()(k.symbol);
        h ^= (std::hash<unsigned char>()(k.interval_code) << 1);
        h ^= (std::hash<long long>()(k.minute_ms) << 2);
        return h;
    }
};

struct EngineDueEntry {
    long long due_ms;
    unsigned long long seq;
    DueKey key;
    unsigned long long gen;
};

struct EngineDueCmp {
    bool operator()(const EngineDueEntry &a, const EngineDueEntry &b) const {
        if (a.due_ms != b.due_ms) return a.due_ms > b.due_ms;
        return a.seq > b.seq;
    }
};

struct WarmupCounter {
    int finalized_count = 0;
    bool ready = false;
};

class NativeApplyEngine {
  public:
    NativeApplyEngine() {
        enabled_interval_codes_.insert(1);
        enabled_interval_codes_.insert(5);
        enabled_interval_codes_.insert(15);
        enabled_interval_codes_.insert(60);
    }

    void set_active_symbols(py::list symbols) {
        active_symbols_.clear();
        for (const py::handle item : symbols) {
            std::string s = py::cast<std::string>(item);
            if (!s.empty()) active_symbols_.insert(std::move(s));
        }
    }

    void set_enabled_intervals(py::list intervals) {
        enabled_interval_codes_.clear();
        for (const py::handle item : intervals) {
            std::string v = py::cast<std::string>(item);
            const unsigned char code = interval_code_from_name(v);
            if (code > 0) enabled_interval_codes_.insert(code);
        }
        if (enabled_interval_codes_.empty()) {
            enabled_interval_codes_.insert(1);
            enabled_interval_codes_.insert(5);
            enabled_interval_codes_.insert(15);
            enabled_interval_codes_.insert(60);
        }
    }

    py::list pop_due(long long now_ms, std::size_t max_items) {
        py::list out;
        while (heap_.size() > 0 && out.size() < max_items) {
            const EngineDueEntry &top = heap_.top();
            if (top.due_ms > now_ms) break;
            DueKey key = top.key;
            const unsigned long long gen = top.gen;
            heap_.pop();
            auto git = gens_.find(key);
            if (git == gens_.end() || git->second != gen) continue;
            gens_.erase(git);
            auto sit = states_.find(key);
            if (sit == states_.end()) continue;
            const StateVal v = sit->second;
            states_.erase(sit);
            seen_trade_ids_.erase(key);
            fingerprints_.erase(key);
            if (key.interval_code != 1) {
                snapshots_[key] = SnapshotVal{v.symbol, v.interval, v.minute_ms,
                    v.open_v, v.high_v, v.low_v, v.close_v, v.volume_v};
            }
            out.append(py::make_tuple(v.symbol, v.interval, v.minute_ms, v.open_v, v.high_v, v.low_v, v.close_v, v.volume_v, v.trades));
        }
        ++pop_due_calls_;
        if (pop_due_calls_ % 100 == 0) {
            evict_stale_snapshots(now_ms);
        }
        return out;
    }

    void evict_stale_snapshots(long long now_ms) {
        static constexpr long long kSnapshotTtlMs = 5LL * 60LL * 1000LL;
        const long long cutoff = now_ms - kSnapshotTtlMs;
        for (auto it = snapshots_.begin(); it != snapshots_.end(); ) {
            if (it->first.minute_ms < cutoff) {
                it = snapshots_.erase(it);
            } else {
                ++it;
            }
        }
    }

    py::object get_snapshot(const std::string &symbol, const std::string &interval, long long minute_ms) const {
        const unsigned char code = interval_code_from_name(interval);
        if (code == 0) return py::none();
        DueKey key{symbol, code, minute_ms};
        auto it = snapshots_.find(key);
        if (it == snapshots_.end()) return py::none();
        const SnapshotVal v = it->second;
        return py::make_tuple(v.symbol, v.interval, v.minute_ms, v.open_v, v.high_v, v.low_v, v.close_v, v.volume_v);
    }

    void delete_snapshot(const std::string &symbol, const std::string &interval, long long minute_ms) {
        const unsigned char code = interval_code_from_name(interval);
        if (code == 0) return;
        DueKey key{symbol, code, minute_ms};
        snapshots_.erase(key);
    }

    void remove_symbols(py::list symbols) {
        std::unordered_set<std::string> removed;
        for (const py::handle item : symbols) {
            std::string s = py::cast<std::string>(item);
            if (!s.empty()) {
                removed.insert(s);
                active_symbols_.erase(s);
            }
        }
        if (removed.empty()) return;

        erase_by_symbols(states_, removed);
        erase_by_symbols(snapshots_, removed);
        erase_by_symbols(fingerprints_, removed);
        erase_by_symbols(gens_, removed);
        erase_by_symbols(seen_trade_ids_, removed);
    }

    py::tuple ingest_and_apply(py::list frames) {
        // --- GIL-held: copy Python inputs to C++ types ---
        struct FrameInput { std::string payload; std::string channel; };
        std::vector<FrameInput> inputs;
        inputs.reserve(py::len(frames));
        for (const py::handle item : frames) {
            py::tuple tup = py::cast<py::tuple>(item);
            if (tup.size() < 2) continue;
            inputs.push_back(FrameInput{
                std::string(py::cast<py::bytes>(tup[0])),
                py::cast<std::string>(tup[1]),
            });
        }

        // --- GIL-released: all JSON parsing, normalization, sorting, state application ---
        std::vector<WarmupEntry> warmups;
        unsigned long long applied = 0;
        {
            py::gil_scoped_release release;
            for (const FrameInput &f : inputs) {
                if (f.channel == "push.deal") {
                    ingest_deal_raw_nogil(f.payload, applied);
                } else if (f.channel == "push.kline") {
                    ingest_kline_raw_nogil(f.payload, applied, warmups);
                }
            }
        }

        // --- GIL-held: build Python return objects ---
        py::list warmup_rows;
        for (const WarmupEntry &w : warmups) {
            warmup_rows.append(py::make_tuple(w.symbol, w.interval, w.minute_ms));
        }
        return py::make_tuple(applied, warmup_rows);
    }

    // Phase 3: native finalize decision kernel
    void set_warmup_targets(py::dict targets) {
        warmup_targets_.clear();
        for (const auto &item : targets) {
            std::string interval = py::cast<std::string>(item.first);
            int target = py::cast<int>(item.second);
            unsigned char code = interval_code_from_name(interval);
            if (code > 0 && target > 0) warmup_targets_[code] = target;
        }
    }

    void set_verdict_cap(std::size_t cap) {
        verdict_cap_ = cap > 0 ? cap : 300000;
    }

    py::tuple finalize_decision(
        const std::string &symbol,
        const std::string &interval,
        long long minute_ms,
        double local_open,
        double local_high,
        double local_low,
        double local_close,
        double local_volume,
        int local_trades,
        bool allow_missing
    ) {
        // Pure C++ decision logic -- result fields captured for Python tuple construction
        int r_action = 0;
        std::string r_stage, r_kind;
        unsigned int r_mask = 0U;
        bool r_override = false, r_matched = false;
        double r_ov[5] = {}, r_sv[5] = {};
        bool r_snap = false, r_dup = false;
        int r_si = 0, r_st = 0;

        {
            py::gil_scoped_release release;
            r_action = finalize_decision_impl(
                symbol, interval, minute_ms,
                local_open, local_high, local_low, local_close, local_volume,
                local_trades, allow_missing,
                r_stage, r_kind, r_mask, r_override, r_matched,
                r_ov, r_sv, r_snap, r_dup, r_si, r_st
            );
        }

        return py::make_tuple(
            r_action, r_stage, r_kind,
            r_mask, r_override, r_matched,
            r_ov[0], r_ov[1], r_ov[2], r_ov[3], r_ov[4],
            r_snap, r_sv[0], r_sv[1], r_sv[2], r_sv[3], r_sv[4],
            r_dup, r_si, r_st
        );
    }

    unsigned long long verdict_dup_drops() const { return verdict_dup_drops_; }

    void reset_warmup_for_symbol(const std::string &symbol) {
        for (auto it = warmup_counters_.begin(); it != warmup_counters_.end();) {
            if (it->first.symbol == symbol) {
                it = warmup_counters_.erase(it);
            } else {
                ++it;
            }
        }
    }

    long long next_due_ms() const {
        if (heap_.empty()) return -1;
        return heap_.top().due_ms;
    }

    std::size_t state_size() const {
        return states_.size();
    }

  private:
    template <typename T>
    static void erase_by_symbols(std::unordered_map<DueKey, T, DueKeyHash> &m, const std::unordered_set<std::string> &removed) {
        for (auto it = m.begin(); it != m.end();) {
            if (removed.count(it->first.symbol) > 0) {
                it = m.erase(it);
            } else {
                ++it;
            }
        }
    }

    void schedule_due(const DueKey &key, long long due_ms) {
        const auto it = gens_.find(key);
        const unsigned long long next_gen = (it == gens_.end()) ? 1ULL : (it->second + 1ULL);
        gens_[key] = next_gen;
        heap_.push(EngineDueEntry{due_ms, ++seq_, key, next_gen});
    }

    static bool should_replace_open(
        const StateVal &v,
        long long ts_ms,
        unsigned long long order_key,
        bool has_trade_id
    ) {
        if (ts_ms < v.open_ts_ms) return true;
        if (ts_ms > v.open_ts_ms) return false;
        if (has_trade_id != v.open_has_trade_id) return has_trade_id;
        return order_key < v.open_order_key;
    }

    static bool should_replace_close(
        const StateVal &v,
        long long ts_ms,
        unsigned long long order_key,
        bool has_trade_id
    ) {
        if (ts_ms > v.close_ts_ms) return true;
        if (ts_ms < v.close_ts_ms) return false;
        if (has_trade_id != v.close_has_trade_id) return has_trade_id;
        return order_key > v.close_order_key;
    }

    struct WarmupEntry { std::string symbol; std::string interval; long long minute_ms; };

    // GIL-free deal ingest: JSON parse -> sort -> apply (no Python objects touched)
    void ingest_deal_raw_nogil(const std::string &payload, unsigned long long &applied) {
        const std::string fallback_symbol = extract_json_string_field(payload, "symbol");
        const std::vector<std::string> rows = extract_data_objects(payload);
        struct RawDeal {
            std::string symbol;
            long long ts;
            double price;
            double qty;
            long long trade_id;
        };
        std::vector<RawDeal> entries;
        entries.reserve(rows.size());
        for (const std::string &row : rows) {
            std::string symbol = extract_json_string_field(row, "symbol");
            if (symbol.empty()) symbol = fallback_symbol;
            double price = 0.0, qty = 0.0;
            long long ts = 0, trade_id = 0;
            const bool ok_price = extract_json_number_field(row, "p", price);
            bool ok_qty = extract_json_number_field(row, "v", qty);
            if (!ok_qty) ok_qty = extract_json_number_field(row, "q", qty);
            const bool ok_ts = extract_json_int64_field(row, "t", ts);
            bool ok_trade_id = extract_json_int64_field(row, "i", trade_id);
            if (!ok_trade_id) ok_trade_id = extract_json_int64_field(row, "trade_id", trade_id);
            if (!ok_trade_id || trade_id < 0) trade_id = 0;
            if (!symbol.empty() && ok_price && ok_qty && ok_ts && price > 0.0 && qty > 0.0 && ts > 0) {
                entries.push_back(RawDeal{std::move(symbol), ts, price, qty, trade_id});
            }
        }
        std::stable_sort(entries.begin(), entries.end(), [](const RawDeal &a, const RawDeal &b) {
            if (a.ts != b.ts) return a.ts < b.ts;
            const bool a_has = a.trade_id > 0;
            const bool b_has = b.trade_id > 0;
            if (a_has != b_has) return a_has;
            return a.trade_id < b.trade_id;
        });
        for (const RawDeal &e : entries) {
            apply_deal_direct(e.symbol, e.ts, e.trade_id, e.price, e.qty, applied);
        }
    }

    // GIL-free kline ingest: JSON parse -> sort -> apply (no Python objects touched)
    void ingest_kline_raw_nogil(const std::string &payload, unsigned long long &applied, std::vector<WarmupEntry> &warmups) {
        const std::string fallback_symbol = extract_json_string_field(payload, "symbol");
        const std::vector<std::string> rows = extract_data_objects(payload);
        struct RawKline {
            std::string symbol;
            std::string interval;
            unsigned char interval_code;
            long long ts;
            double open_v, high_v, low_v, close_v, volume_v;
        };
        std::vector<RawKline> entries;
        entries.reserve(rows.size());
        for (const std::string &row : rows) {
            std::string symbol = extract_json_string_field(row, "symbol");
            if (symbol.empty()) symbol = fallback_symbol;
            const std::string interval = extract_json_string_field(row, "interval");
            double open_v = 0.0, high_v = 0.0, low_v = 0.0, close_v = 0.0, volume_v = 0.0;
            long long ts = 0;
            const bool ok_open = extract_json_number_field(row, "o", open_v);
            const bool ok_high = extract_json_number_field(row, "h", high_v);
            const bool ok_low = extract_json_number_field(row, "l", low_v);
            const bool ok_close = extract_json_number_field(row, "c", close_v);
            // MEXC "ro"/"rh"/"rl"/"rc" are the real OHLC (first/last trade of
            // the minute).  "o"/"c" are carry-forward values (prev close = next
            // open).  Prefer real values when present.
            double rv = 0.0;
            if (extract_json_number_field(row, "ro", rv) && rv > 0.0) open_v = rv;
            if (extract_json_number_field(row, "rh", rv) && rv > 0.0) high_v = rv;
            if (extract_json_number_field(row, "rl", rv) && rv > 0.0) low_v = rv;
            if (extract_json_number_field(row, "rc", rv) && rv > 0.0) close_v = rv;
            bool ok_vol = extract_json_number_field(row, "q", volume_v);
            if (!ok_vol) ok_vol = extract_json_number_field(row, "v", volume_v);
            bool ok_ts = extract_json_int64_field(row, "t", ts);
            if (!ok_ts) ok_ts = extract_json_int64_field(row, "timestamp", ts);
            const unsigned char ic = interval_code_from_name(interval);
            if (
                !symbol.empty() && !interval.empty() && ic > 0 &&
                ok_open && ok_high && ok_low && ok_close && ok_vol && ok_ts &&
                open_v > 0.0 && high_v > 0.0 && low_v > 0.0 && close_v > 0.0 && ts > 0
            ) {
                entries.push_back(RawKline{std::move(symbol), interval, ic, ts, open_v, high_v, low_v, close_v, volume_v});
            }
        }
        std::stable_sort(entries.begin(), entries.end(), [](const RawKline &a, const RawKline &b) {
            if (a.symbol != b.symbol) return a.symbol < b.symbol;
            if (a.interval != b.interval) return a.interval < b.interval;
            return a.ts < b.ts;
        });
        for (const RawKline &e : entries) {
            apply_kline_direct_nogil(e.symbol, e.interval, e.interval_code, e.ts,
                               e.open_v, e.high_v, e.low_v, e.close_v, e.volume_v,
                               applied, warmups);
        }
    }

    // Pure C++ finalize decision implementation (called with GIL released)
    int finalize_decision_impl(
        const std::string &symbol, const std::string &interval, long long minute_ms,
        double local_open, double local_high, double local_low,
        double local_close, double local_volume, int local_trades, bool allow_missing,
        std::string &r_stage, std::string &r_kind, unsigned int &r_mask,
        bool &r_override, bool &r_matched,
        double r_ov[5], double r_sv[5],
        bool &r_snap, bool &r_dup, int &r_si, int &r_st
    ) {
        const unsigned char code = interval_code_from_name(interval);
        DueKey verdict_key{symbol, code, minute_ms};

        if (verdict_seen_.count(verdict_key) > 0) {
            verdict_dup_drops_ += 1;
            r_stage = "post_warmup"; r_kind = "verdict_duplicate";
            r_matched = true; r_dup = true;
            return 1;
        }
        verdict_seen_.insert(verdict_key);
        verdict_order_.push_back(verdict_key);
        while (verdict_order_.size() > verdict_cap_) {
            verdict_seen_.erase(verdict_order_.front());
            verdict_order_.pop_front();
        }

        DueKey warmup_key{symbol, code, 0};
        auto &wc = warmup_counters_[warmup_key];
        int target = 1;
        auto tit = warmup_targets_.find(code);
        if (tit != warmup_targets_.end()) target = tit->second;
        bool warmup_phase = wc.finalized_count < target;
        wc.finalized_count += 1;
        if (wc.finalized_count >= target) wc.ready = true;
        r_si = wc.finalized_count;
        r_st = target;
        r_stage = warmup_phase ? "warmup" : "post_warmup";

        DueKey snap_key{symbol, code, minute_ms};
        auto snap_it = snapshots_.find(snap_key);
        bool snap_present = (snap_it != snapshots_.end());

        if (!snap_present) {
            if (!allow_missing) {
                wc.finalized_count -= 1;
                if (wc.finalized_count < target) wc.ready = false;
                verdict_seen_.erase(verdict_key);
                if (!verdict_order_.empty() && verdict_order_.back() == verdict_key) {
                    verdict_order_.pop_back();
                }
                r_kind = warmup_phase ? "warmup_seed_missing_snapshot_pending" : "missing_snapshot_pending";
                return 0;
            }
            r_kind = warmup_phase ? "warmup_seed_missing_snapshot_timeout" : "missing_snapshot_timeout";
            return 1;
        }

        const SnapshotVal &sv = snap_it->second;
        r_mask = compare_ohlcv_diff_mask(
            local_open, local_high, local_low, local_close, local_volume,
            sv.open_v, sv.high_v, sv.low_v, sv.close_v, sv.volume_v
        );
        r_matched = (r_mask == 0U);
        r_snap = true;
        r_sv[0] = sv.open_v; r_sv[1] = sv.high_v; r_sv[2] = sv.low_v;
        r_sv[3] = sv.close_v; r_sv[4] = sv.volume_v;

        if (warmup_phase) {
            r_override = true;
            r_ov[0] = sv.open_v; r_ov[1] = sv.high_v; r_ov[2] = sv.low_v;
            r_ov[3] = sv.close_v; r_ov[4] = sv.volume_v;
            r_kind = "warmup_seeded_from_exchange";
            snapshots_.erase(snap_it);
            return 1;
        }

        r_kind = r_matched ? "exact_match" : "value_diff";
        snapshots_.erase(snap_it);
        return 1;
    }

    // Apply a single deal directly from parsed fields (no binary encode/decode)
    void apply_deal_direct(
        const std::string &symbol, long long ts_raw, long long trade_id_raw,
        double price, double qty, unsigned long long &applied
    ) {
        if (price <= 0.0 || qty <= 0.0) return;
        if (symbol.empty() || active_symbols_.count(symbol) == 0) return;
        const long long ts_ms = normalize_ts_ms(ts_raw);
        if (ts_ms <= 0) return;
        const long long minute_ms = (ts_ms / 60000LL) * 60000LL;
        DueKey key{symbol, 1, minute_ms};
        const unsigned long long trade_id_u = static_cast<unsigned long long>(std::max(0LL, trade_id_raw));
        const bool has_trade_id = trade_id_u > 0ULL;
        if (has_trade_id) {
            auto &seen = seen_trade_ids_[key];
            if (!seen.insert(trade_id_u).second) return;
        }
        auto it = states_.find(key);
        const unsigned long long ev_seq = ++deal_seq_;
        const unsigned long long order_key = has_trade_id ? trade_id_u : ev_seq;
        if (it == states_.end()) {
            states_.emplace(key, StateVal{
                symbol, "Min1", minute_ms,
                price, price, price, price, qty, 1,
                ts_ms, ts_ms, order_key, order_key,
                has_trade_id, has_trade_id,
            });
            schedule_due(key, minute_ms + 60000LL);
        } else {
            StateVal &v = it->second;
            if (price > v.high_v) v.high_v = price;
            if (price < v.low_v) v.low_v = price;
            if (should_replace_open(v, ts_ms, order_key, has_trade_id)) {
                v.open_v = price; v.open_ts_ms = ts_ms;
                v.open_order_key = order_key; v.open_has_trade_id = has_trade_id;
            }
            if (should_replace_close(v, ts_ms, order_key, has_trade_id)) {
                v.close_v = price; v.close_ts_ms = ts_ms;
                v.close_order_key = order_key; v.close_has_trade_id = has_trade_id;
            }
            v.volume_v += qty;
            v.trades += 1;
        }
        applied += 1;
    }

    void apply_kline_direct_nogil(
        const std::string &symbol, const std::string &interval, unsigned char interval_code,
        long long ts_raw,
        double open_v, double high_v, double low_v, double close_v, double volume_v,
        unsigned long long &applied, std::vector<WarmupEntry> &warmups
    ) {
        if (open_v <= 0.0 || high_v <= 0.0 || low_v <= 0.0 || close_v <= 0.0) return;
        if (enabled_interval_codes_.count(interval_code) == 0) return;
        const long long interval_ms = interval_ms_from_code(interval_code);
        if (interval_ms <= 0) return;
        if (symbol.empty() || active_symbols_.count(symbol) == 0) return;
        const long long ts_ms = normalize_ts_ms(ts_raw);
        if (ts_ms <= 0) return;
        const long long minute_ms = (ts_ms / interval_ms) * interval_ms;
        DueKey key{symbol, interval_code, minute_ms};
        snapshots_[key] = SnapshotVal{symbol, interval, minute_ms, open_v, high_v, low_v, close_v, volume_v};
        warmups.push_back(WarmupEntry{symbol, interval, minute_ms});
        if (interval_code != 1) {
            const FpVal fp{open_v, high_v, low_v, close_v, volume_v};
            const auto fp_it = fingerprints_.find(key);
            if (fp_it != fingerprints_.end() && fp_it->second == fp) {
                applied += 1;
                return;
            }
            fingerprints_[key] = fp;
            auto sit = states_.find(key);
            if (sit == states_.end()) {
                states_.emplace(key, StateVal{
                    symbol, interval, minute_ms,
                    open_v, high_v, low_v, close_v, volume_v, 0,
                    minute_ms, minute_ms + interval_ms - 1,
                    0ULL, 0ULL, false, false,
                });
                schedule_due(key, minute_ms + interval_ms);
            } else {
                StateVal &v = sit->second;
                v.open_v = open_v; v.high_v = high_v;
                v.low_v = low_v; v.close_v = close_v;
                v.volume_v = volume_v;
            }
        }
        applied += 1;
    }

    std::unordered_set<std::string> active_symbols_;
    std::unordered_set<unsigned char> enabled_interval_codes_;
    std::unordered_map<DueKey, StateVal, DueKeyHash> states_;
    std::unordered_map<DueKey, SnapshotVal, DueKeyHash> snapshots_;
    std::unordered_map<DueKey, FpVal, DueKeyHash> fingerprints_;
    std::unordered_map<DueKey, std::unordered_set<unsigned long long>, DueKeyHash> seen_trade_ids_;
    std::unordered_map<DueKey, unsigned long long, DueKeyHash> gens_;
    std::priority_queue<EngineDueEntry, std::vector<EngineDueEntry>, EngineDueCmp> heap_;
    unsigned long long seq_ = 0ULL;
    unsigned long long deal_seq_ = 0ULL;
    unsigned long long pop_due_calls_ = 0ULL;

    // Phase 3: finalize kernel state
    std::unordered_map<unsigned char, int> warmup_targets_;
    std::unordered_map<DueKey, WarmupCounter, DueKeyHash> warmup_counters_;
    std::unordered_set<DueKey, DueKeyHash> verdict_seen_;
    std::deque<DueKey> verdict_order_;
    std::size_t verdict_cap_ = 300000;
    unsigned long long verdict_dup_drops_ = 0ULL;
};

// ---------------------------------------------------------------------------
// Native JSON serialization for final candle payloads
// ---------------------------------------------------------------------------

static inline void json_append_key(std::string &buf, const char *key) {
    buf.push_back('"');
    buf.append(key);
    buf.append("\":");
}

static inline void json_append_string(std::string &buf, const char *key, const std::string &val) {
    json_append_key(buf, key);
    buf.push_back('"');
    for (const char c : val) {
        if (c == '"') { buf.push_back('\\'); buf.push_back('"'); }
        else if (c == '\\') { buf.push_back('\\'); buf.push_back('\\'); }
        else { buf.push_back(c); }
    }
    buf.push_back('"');
}

static inline void json_append_int(std::string &buf, const char *key, long long val) {
    json_append_key(buf, key);
    buf.append(std::to_string(val));
}

static inline void json_append_double(std::string &buf, const char *key, double val) {
    json_append_key(buf, key);
    char tmp[64];
    int n = std::snprintf(tmp, sizeof(tmp), "%.15g", val);
    buf.append(tmp, static_cast<std::size_t>(n));
}

py::bytes build_candle_json(
    int symbol_id,
    const std::string &symbol,
    const std::string &interval,
    long long minute_ms,
    double open_v,
    double high_v,
    double low_v,
    double close_v,
    double volume_v,
    int trades,
    long long emitted_at_ms
) {
    std::string buf;
    buf.reserve(256);
    buf.push_back('{');
    json_append_int(buf, "symbol_id", symbol_id);
    buf.push_back(',');
    json_append_string(buf, "symbol", symbol);
    buf.push_back(',');
    json_append_string(buf, "interval", interval);
    buf.push_back(',');
    json_append_int(buf, "minute_ms", minute_ms);
    buf.push_back(',');
    json_append_double(buf, "open", open_v);
    buf.push_back(',');
    json_append_double(buf, "high", high_v);
    buf.push_back(',');
    json_append_double(buf, "low", low_v);
    buf.push_back(',');
    json_append_double(buf, "close", close_v);
    buf.push_back(',');
    json_append_double(buf, "volume", volume_v);
    buf.push_back(',');
    json_append_int(buf, "trades", trades);
    buf.push_back(',');
    json_append_int(buf, "emitted_at_ms", emitted_at_ms);
    buf.push_back('}');
    return py::bytes(buf);
}

PYBIND11_MODULE(_native_core_cpp, m) {
    m.doc() = "Farmer v3 native data-plane core (GIL-released hot paths)";
    m.def("extract_frame_meta", &extract_frame_meta);
    m.def("build_candle_json", &build_candle_json);
    py::class_<NativeApplyEngine>(m, "NativeApplyEngine")
        .def(py::init<>())
        .def("set_active_symbols", &NativeApplyEngine::set_active_symbols)
        .def("set_enabled_intervals", &NativeApplyEngine::set_enabled_intervals)
        .def("ingest_and_apply", &NativeApplyEngine::ingest_and_apply)
        .def("pop_due", &NativeApplyEngine::pop_due)
        .def("get_snapshot", &NativeApplyEngine::get_snapshot)
        .def("delete_snapshot", &NativeApplyEngine::delete_snapshot)
        .def("remove_symbols", &NativeApplyEngine::remove_symbols)
        .def("next_due_ms", &NativeApplyEngine::next_due_ms)
        .def("state_size", &NativeApplyEngine::state_size)
        .def("set_warmup_targets", &NativeApplyEngine::set_warmup_targets)
        .def("set_verdict_cap", &NativeApplyEngine::set_verdict_cap)
        .def("finalize_decision", &NativeApplyEngine::finalize_decision)
        .def("verdict_dup_drops", &NativeApplyEngine::verdict_dup_drops)
        .def("reset_warmup_for_symbol", &NativeApplyEngine::reset_warmup_for_symbol);
}
