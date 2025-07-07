
# ── risk_manager.py ──
import os
import json
from core.blofin_gateway import get_equity_usdt

STATE_FILE = "state.json"
DAILY_LOSS_LIMIT_PCT = 0.15  # 15% daily cap

# Default margin per trade if trader not specified
TRADER_RISK = {
    "fatty": 0.04,
    "illusion": 0.03,
    "khalil": 0.025,
    "jotham": 0.025,
    "ty": 0.02,
    "default": 0.01
}

TEST_BALANCE_USDT = 5000.0  # fallback if API fails

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"daily_loss": 0.0}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_per_trader_risk(trader_name: str) -> float:
    return TRADER_RISK.get(trader_name.lower(), TRADER_RISK["default"])

def check_daily_loss_cap():
    state = load_state()
    equity = get_equity_usdt() or TEST_BALANCE_USDT
    return state["daily_loss"] < (equity * DAILY_LOSS_LIMIT_PCT)

def update_daily_loss(loss_amount):
    state = load_state()
    state["daily_loss"] += loss_amount
    save_state(state)

def position_size(entry_price: float,
                  balance: float = TEST_BALANCE_USDT,
                  margin_pct: float = TRADER_RISK["default"]) -> float:
    allocation = balance * margin_pct
    qty = allocation / entry_price
    return round(qty, 4)

def staged_entry_qty(entry, current_price, trader_name="default"):
    balance = get_equity_usdt() or TEST_BALANCE_USDT
    margin_pct = get_per_trader_risk(trader_name)
    allocation_usd = balance * margin_pct
    full_qty = allocation_usd / entry

    diff_pct = abs(current_price - entry) / entry * 100

    if diff_pct >= 1.0:
        return {"qty_now": round(full_qty * 0.20, 4), "qty_limit": 0.0}
    elif diff_pct < 0.5:
        return {"qty_now": round(full_qty * 0.50, 4), "qty_limit": round(full_qty * 0.50, 4)}
    else:  # between 0.5–1 %
        return {"qty_now": round(full_qty, 4), "qty_limit": 0.0}
