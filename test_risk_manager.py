import json
import os
import sys
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import risk_manager

def run_all_tests():
    print("[DEBUG] Starting test_risk_manager.py")
    print("[DEBUG] Running all tests...\n")
    test_get_per_trader_risk()
    test_check_daily_loss_cap()
    test_staged_entry_qty()

def test_get_per_trader_risk():
    print("[TEST] Running test_get_per_trader_risk")
    for trader in ["fatty", "illusion", "jotham", "khalil", "unknown"]:
        risk = risk_manager.get_per_trader_risk(trader)
        print(f"[DEBUG] Trader: {trader}, Risk: {risk}")
    print("[TEST] test_get_per_trader_risk completed.\n")

def test_check_daily_loss_cap():
    print("[TEST] Running test_check_daily_loss_cap")
    capped = risk_manager.check_daily_loss_cap()
    print(f"[DEBUG] Daily loss cap status: {capped}")
    print("[TEST] test_check_daily_loss_cap completed.\n")

def test_staged_entry_qty():
    print("[TEST] Running test_staged_entry_qty")
    trade = {
        "entry": 0.5,
        "trader": "illusion",
        "symbol": "BTC/USDT"
    }
    live_price = 0.48
    equity = 2000.0
    print(f"[DEBUG] Mocked equity = {equity}")
    print(f"[DEBUG] trade['trader'] type: {type(trade['trader'])}, value: {trade['trader']}")
    try:
        qty = risk_manager.staged_entry_qty(trade, live_price, equity)
        print(f"[TEST] Calculated qty: {qty}")
    except Exception as e:
        print("[ERROR] test_staged_entry_qty failed:")
        traceback.print_exc()
    print("[TEST] test_staged_entry_qty completed.\n")

if __name__ == "__main__":
    run_all_tests()
