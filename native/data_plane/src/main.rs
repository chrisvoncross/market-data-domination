use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::io::{self, BufRead};

#[derive(Debug, Deserialize)]
struct InputEvent {
    #[allow(dead_code)]
    kind: Option<String>,
    channel: Option<String>,
    symbol: Option<String>,
    payload: Option<Value>,
}

#[derive(Debug, Serialize)]
struct OutputEvent {
    route: &'static str,
    event_type: &'static str,
    channel: String,
    symbol: String,
    minute_ms: Option<i64>,
    trade_id: Option<i64>,
    dedupe_status: &'static str,
    order_key: i64,
    interval: Option<String>,
}

#[derive(Debug, Clone)]
struct DealAgg {
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
    trade_count: i64,
}

#[derive(Debug, Clone)]
struct KlineSnapshot {
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
    trade_count: i64,
}

fn as_i64(v: &Value) -> Option<i64> {
    if let Some(x) = v.as_i64() {
        return Some(x);
    }
    if let Some(s) = v.as_str() {
        return s.parse::<i64>().ok();
    }
    None
}

fn minute_floor_ms(ts: i64) -> i64 {
    (ts / 60_000) * 60_000
}

fn normalize_ts_ms(ts: i64) -> i64 {
    if ts < 1_000_000_000_000 {
        ts * 1000
    } else {
        ts
    }
}

fn first_deal_data(payload: &Value) -> Option<&Value> {
    let data = payload.get("data")?;
    if let Some(arr) = data.as_array() {
        return arr.first();
    }
    if data.is_object() {
        return Some(data);
    }
    None
}

fn first_kline_data(payload: &Value) -> Option<&Value> {
    let data = payload.get("data")?;
    if let Some(arr) = data.as_array() {
        return arr.first();
    }
    if data.is_object() {
        return Some(data);
    }
    None
}

fn as_f64(v: &Value) -> Option<f64> {
    if let Some(x) = v.as_f64() {
        return Some(x);
    }
    if let Some(s) = v.as_str() {
        return s.parse::<f64>().ok();
    }
    None
}

fn finalize_minute(
    symbol: &str,
    interval: &str,
    minute_ms: i64,
    deal_aggs: &mut HashMap<(String, i64), DealAgg>,
    snapshots: &HashMap<(String, String, i64), KlineSnapshot>,
    emitted: &mut HashSet<(String, String, i64)>,
) {
    let out_key = (symbol.to_string(), interval.to_string(), minute_ms);
    if emitted.contains(&out_key) {
        return;
    }

    let Some(snap) = snapshots.get(&out_key) else {
        return;
    };

    let mut decision_kind = "direct_exchange_tf";
    let mut mismatch = false;
    if interval == "Min1" {
        if let Some(deal) = deal_aggs.get(&(symbol.to_string(), minute_ms)) {
            let diff = (deal.high - snap.high).abs() > 1e-9
                || (deal.low - snap.low).abs() > 1e-9
                || (deal.close - snap.close).abs() > 1e-9
                || (deal.volume - snap.volume).abs() > 1e-9;
            if diff {
                mismatch = true;
                decision_kind = "direct_exchange_override_local";
            } else {
                decision_kind = "direct_exchange_match_local";
            }
        }
    }

    let final_event = serde_json::json!({
        "route": "first_pass",
        "event_type": "final_candle",
        "symbol": symbol,
        "interval": interval,
        "minute_ms": minute_ms,
        "open": snap.open,
        "high": snap.high,
        "low": snap.low,
        "close": snap.close,
        "volume": snap.volume,
        "trade_count": snap.trade_count,
        "decision_kind": decision_kind
    });
    println!("{final_event}");

    if mismatch {
        let mismatch_event = serde_json::json!({
            "route": "first_pass",
            "event_type": "mismatch_event",
            "symbol": symbol,
            "interval": interval,
            "minute_ms": minute_ms,
            "reason": "snapshot_value_diff"
        });
        println!("{mismatch_event}");
    }

    emitted.insert(out_key);
}

fn main() {
    // First pass seam: native loop reads NDJSON and routes deal/kline.
    // Contract-first behavior:
    // - dedupe key: (symbol, minute_ms, trade_id) when trade_id > 0
    // - order key: trade_id if present, else monotonic event sequence
    let stdin = io::stdin();
    let mut seq: i64 = 0;
    let mut seen_trade_ids: HashMap<String, HashSet<i64>> = HashMap::new();
    let mut deal_aggs: HashMap<(String, i64), DealAgg> = HashMap::new();
    let mut kline_snapshots: HashMap<(String, String, i64), KlineSnapshot> = HashMap::new();
    let mut last_minute_by_symbol_tf: HashMap<(String, String), i64> = HashMap::new();
    let mut emitted_final: HashSet<(String, String, i64)> = HashSet::new();

    for line in stdin.lock().lines().flatten() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed: Result<InputEvent, _> = serde_json::from_str(&line);
        let Ok(ev) = parsed else {
            continue;
        };

        let Some(channel) = ev.channel else {
            continue;
        };
        let Some(symbol) = ev.symbol else {
            continue;
        };

        seq += 1;

        if channel.starts_with("push.") {
            let mut minute_ms: Option<i64> = None;
            let mut interval: Option<String> = None;
            let mut trade_id: Option<i64> = None;
            let mut dedupe_status: &'static str = "accepted";
            let mut order_key = seq;

            if channel == "push.deal" {
                if let Some(payload) = ev.payload.as_ref() {
                    if let Some(deal) = first_deal_data(payload) {
                        if let Some(ts) = deal.get("t").and_then(as_i64) {
                            minute_ms = Some(minute_floor_ms(normalize_ts_ms(ts)));
                        }
                        let id = deal
                            .get("i")
                            .and_then(as_i64)
                            .or_else(|| deal.get("trade_id").and_then(as_i64));
                        if let Some(id_val) = id {
                            if id_val > 0 {
                                trade_id = Some(id_val);
                                order_key = id_val;
                                if let Some(mm) = minute_ms {
                                    let key = format!("{}:{}", symbol, mm);
                                    let seen = seen_trade_ids.entry(key).or_default();
                                    if !seen.insert(id_val) {
                                        continue;
                                    }
                                }
                            } else {
                                dedupe_status = "trade_id_missing_or_non_positive";
                            }
                        } else {
                            dedupe_status = "trade_id_missing_or_non_positive";
                        }

                        if let Some(mm) = minute_ms {
                            let price = deal.get("p").and_then(as_f64).unwrap_or(0.0);
                            let qty = deal.get("v").and_then(as_f64).unwrap_or(0.0);
                            let key = (symbol.clone(), mm);
                            deal_aggs
                                .entry(key)
                                .and_modify(|a| {
                                    if a.trade_count == 0 {
                                        a.open = price;
                                        a.high = price;
                                        a.low = price;
                                    } else {
                                        if price > a.high {
                                            a.high = price;
                                        }
                                        if price < a.low {
                                            a.low = price;
                                        }
                                    }
                                    a.close = price;
                                    a.volume += qty;
                                    a.trade_count += 1;
                                })
                                .or_insert(DealAgg {
                                    open: price,
                                    high: price,
                                    low: price,
                                    close: price,
                                    volume: qty,
                                    trade_count: 1,
                                });
                        }
                    }
                }
            } else if channel == "push.kline" {
                if let Some(payload) = ev.payload.as_ref() {
                    if let Some(kline) = first_kline_data(payload) {
                        minute_ms = kline.get("t").and_then(as_i64).map(normalize_ts_ms);
                        interval = kline
                            .get("interval")
                            .and_then(|x| x.as_str())
                            .map(|s| s.to_string())
                            .or_else(|| Some("Min1".to_string()));
                        if let Some(mm) = minute_ms {
                            let snap = KlineSnapshot {
                                open: kline.get("o").and_then(as_f64).unwrap_or(0.0),
                                high: kline.get("h").and_then(as_f64).unwrap_or(0.0),
                                low: kline.get("l").and_then(as_f64).unwrap_or(0.0),
                                close: kline.get("c").and_then(as_f64).unwrap_or(0.0),
                                volume: kline.get("q").and_then(as_f64).unwrap_or(0.0),
                                trade_count: kline.get("n").and_then(as_i64).unwrap_or(0),
                            };
                            let iv = interval.clone().unwrap_or_else(|| "Min1".to_string());
                            kline_snapshots.insert((symbol.clone(), iv, mm), snap);
                        }
                    }
                }
            }

            if let Some(mm) = minute_ms {
                if channel == "push.kline" {
                    let iv = interval.clone().unwrap_or_else(|| "Min1".to_string());
                    let tf_key = (symbol.clone(), iv.clone());
                    if let Some(prev) = last_minute_by_symbol_tf.get(&tf_key).copied() {
                        if mm > prev {
                            finalize_minute(
                                &symbol,
                                &iv,
                                prev,
                                &mut deal_aggs,
                                &kline_snapshots,
                                &mut emitted_final,
                            );
                        }
                    }
                    last_minute_by_symbol_tf.insert(tf_key, mm);
                }
            }

            let out = OutputEvent {
                route: "first_pass",
                event_type: "routed_event",
                channel,
                symbol,
                minute_ms,
                trade_id,
                dedupe_status,
                order_key,
                interval,
            };
            if let Ok(encoded) = serde_json::to_string(&out) {
                println!("{encoded}");
            }
        }
    }

    let pending: Vec<((String, String), i64)> = last_minute_by_symbol_tf.into_iter().collect();
    for ((symbol, interval), minute_ms) in pending {
        finalize_minute(
            &symbol,
            &interval,
            minute_ms,
            &mut deal_aggs,
            &kline_snapshots,
            &mut emitted_final,
        );
    }
}
