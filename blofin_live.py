import os
import hmac
import time
import json
import base64
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode

# API Configuration
BASE_URL = "https://api.blofin.com"
API_KEY = os.getenv("BLOFIN_API_KEY", "")
API_SECRET = os.getenv("BLOFIN_API_SECRET", "").encode()
PASSPHRASE = os.getenv("BLOFIN_PASSPHRASE", "")

def _get_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """Generate BloFin API signature"""
    message = timestamp + method + request_path + body
    mac = hmac.new(API_SECRET, message.encode(), digestmod='sha256')
    return base64.b64encode(mac.digest()).decode()

def _make_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """Make authenticated API request with error handling"""
    try:
        url = f"{BASE_URL}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        body = json.dumps(data) if data else ""
        
        headers = {
            "BL-ACCESS-KEY": API_KEY,
            "BL-ACCESS-SIGN": _get_signature(timestamp, method, endpoint, body),
            "BL-ACCESS-TIMESTAMP": timestamp,
            "BL-ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }
        
        response = requests.request(method, url, headers=headers, params=params, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error: {str(e)}")
        return None

def get_equity() -> Optional[float]:
    """Get account equity in USDT"""
    try:
        response = _make_request("GET", "/api/v1/account/balance")
        if response and "data" in response:
            for balance in response["data"]:
                if balance["currency"] == "USDT":
                    return float(balance["equity"])
        return None
    except Exception as e:
        print(f"Error getting equity: {str(e)}")
        return None

def place_order(symbol: str, side: str, qty: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Place a market or limit order"""
    try:
        data = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT" if price else "MARKET",
            "size": str(qty)
        }
        if price:
            data["price"] = str(price)
            
        return _make_request("POST", "/api/v1/trade/order", data=data)
    except Exception as e:
        print(f"Error placing order: {str(e)}")
        return None

def cancel_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Cancel an existing order"""
    try:
        return _make_request("DELETE", f"/api/v1/trade/order/{order_id}")
    except Exception as e:
        print(f"Error canceling order: {str(e)}")
        return None

def move_sl(order_id: str, new_sl: float) -> Optional[Dict[str, Any]]:
    """Move stop loss by canceling and recreating the order"""
    try:
        # First get the original order details
        order_info = _make_request("GET", f"/api/v1/trade/order/{order_id}")
        if not order_info or "data" not in order_info:
            return None
            
        order = order_info["data"]
        
        # Cancel the original order
        if not cancel_order(order_id):
            return None
            
        # Create new order with updated SL
        return place_order(
            symbol=order["symbol"],
            side=order["side"],
            qty=float(order["size"]),
            price=float(order["price"]) if order["type"] == "LIMIT" else None
        )
    except Exception as e:
        print(f"Error moving stop loss: {str(e)}")
        return None 