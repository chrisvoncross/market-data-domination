use serde::{Deserialize, Serialize};
use std::io::{self, BufRead};

#[derive(Debug, Deserialize)]
struct InputEvent {
    kind: Option<String>,
    channel: Option<String>,
    symbol: Option<String>,
}

#[derive(Debug, Serialize)]
struct OutputEvent {
    route: &'static str,
    channel: String,
    symbol: String,
}

fn main() {
    // First pass seam: native loop reads NDJSON and routes only deal/kline.
    let stdin = io::stdin();
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

        if channel == "push.deal" || channel == "push.kline" {
            let out = OutputEvent {
                route: "first_pass",
                channel,
                symbol,
            };
            if let Ok(encoded) = serde_json::to_string(&out) {
                println!("{encoded}");
            }
        }
    }
}
