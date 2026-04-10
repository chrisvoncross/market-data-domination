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
    channel: String,
    symbol: String,
    minute_ms: Option<i64>,
    trade_id: Option<i64>,
    dedupe_status: &'static str,
    order_key: i64,
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

fn first_deal_data(payload: &Value) -> Option<&Value> {
    payload.get("data")?.as_array()?.first()
}

fn main() {
    // First pass seam: native loop reads NDJSON and routes deal/kline.
    // Contract-first behavior:
    // - dedupe key: (symbol, minute_ms, trade_id) when trade_id > 0
    // - order key: trade_id if present, else monotonic event sequence
    let stdin = io::stdin();
    let mut seq: i64 = 0;
    let mut seen_trade_ids: HashMap<String, HashSet<i64>> = HashMap::new();

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

        if channel == "push.deal" || channel == "push.kline" {
            let mut minute_ms: Option<i64> = None;
            let mut trade_id: Option<i64> = None;
            let mut dedupe_status: &'static str = "accepted";
            let mut order_key = seq;

            if channel == "push.deal" {
                if let Some(payload) = ev.payload.as_ref() {
                    if let Some(deal) = first_deal_data(payload) {
                        if let Some(ts) = deal.get("t").and_then(as_i64) {
                            minute_ms = Some(minute_floor_ms(ts));
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
                    }
                }
            } else if channel == "push.kline" {
                if let Some(payload) = ev.payload.as_ref() {
                    if let Some(kline) = payload.get("data").and_then(|x| x.as_array()).and_then(|a| a.first()) {
                        minute_ms = kline.get("t").and_then(as_i64);
                    }
                }
            }

            let out = OutputEvent {
                route: "first_pass",
                channel,
                symbol,
                minute_ms,
                trade_id,
                dedupe_status,
                order_key,
            };
            if let Ok(encoded) = serde_json::to_string(&out) {
                println!("{encoded}");
            }
        }
    }
}
