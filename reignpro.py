import os
import json
import re
import random
import time

# === CONFIGURATION === #
EXPORT_FOLDER = "./exports/"
MARGIN_ALLOCATION = 1.0  # percent of total balance per trade
BALANCE = 1000  # simulated account balance
MOCK_PRICE_RANGE = 0.98, 1.02  # mock current price fluctuation (±2%)

# === Signal Pattern === #
SIGNAL_REGEX = re.compile(
    r"(?:entry|buy|long)[\s:]*([\d.]+).*?(?:tp\d?|target)[\s:]*([\d.]+).*?(?:sl|stop)[\s:]*([\d.]+)",
    re.IGNORECASE | re.DOTALL
)

# === Trade Simulator === #
def simulate_trade(entry, target, stoploss, symbol="BTC/USDT"):
    current_price = entry * random.uniform(*MOCK_PRICE_RANGE)
    print(f"\n📈 Simulating Trade for {symbol}")
    print(f"Mock Price: {current_price:.4f} | Entry: {entry} | TP: {target} | SL: {stoploss}")

    distance = abs(current_price - entry) / entry

    if distance >= 0.01:
        amount = BALANCE * (MARGIN_ALLOCATION / 100) * 0.20
        method = "Partial Entry (20%) - Market"
    elif distance <= 0.005:
        amount = BALANCE * (MARGIN_ALLOCATION / 100) * 0.50
        method = "Partial Entry (50%) - Market + 50% Limit"
    else:
        amount = BALANCE * (MARGIN_ALLOCATION / 100)
        method = "Full Entry (1%) - Market"

    print(f"📊 Strategy: {method} | Allocated Amount: ${amount:.2f}")

# === Parser for JSON Signal Files === #
def parse_signals(folder):
    for file in os.listdir(folder):
        if file.endswith(".json"):
            with open(os.path.join(folder, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                for msg in data.get("messages", []):
                    text = msg.get("content", "")
                    match = SIGNAL_REGEX.search(text)
                    if match:
                        entry = float(match.group(1))
                        tp = float(match.group(2))
                        sl = float(match.group(3))
                        user = msg["author"]["name"]
                        print(f"\n🧠 Signal From: {user}")
                        simulate_trade(entry, tp, sl)

# === MAIN === #
if __name__ == "__main__":
    print("🟢 Starting Trade Logic Simulator...\n")
    parse_signals(EXPORT_FOLDER)
    print("\n✅ Simulation Complete.")
