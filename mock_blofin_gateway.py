import uuid, time, json, pathlib, datetime as dt, os

MOCK_LOG = pathlib.Path("mock_orders.jsonl")

def _write(event):
    MOCK_LOG.write_text("") if not MOCK_LOG.exists() else None
    with MOCK_LOG.open("a") as f:
        f.write(json.dumps(event) + "\n")

def place_order(symbol, side, qty, price=None):
    """Return a fake BloFin order response."""
    event = {
        "mock": True,
        "ts": int(time.time()*1000),
        "orderId": str(uuid.uuid4())[:8],
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price or "market",
    }
    _write(event)
    return {"data": event}

def get_equity():
    """Get mock equity balance"""
    return 10_000.0

def get_equity_usdt():
    return 10_000.0         # constant fake balance

def cancel_order(order_id):
    """Mock cancel order"""
    event = {
        "mock": True,
        "ts": int(time.time()*1000),
        "action": "cancel",
        "orderId": order_id,
    }
    _write(event)
    return {"data": event}

def move_sl(order_id, new_sl):
    """Mock move stop loss"""
    event = {
        "mock": True,
        "ts": int(time.time()*1000),
        "action": "move_sl",
        "orderId": order_id,
        "new_sl": new_sl,
    }
    _write(event)
    return {"data": event}

from dotenv import load_dotenv ; load_dotenv()
KEY     = os.getenv("BLOFIN_API_KEY")
SECRET  = os.getenv("BLOFIN_API_SECRET", "").encode()
PASSPHRASE = os.getenv("BLOFIN_PASSPHRASE")