import uuid, json, pathlib, time
LOG = pathlib.Path("mock_orders.jsonl")

def _log(event): LOG.write_text("") if not LOG.exists() else None; LOG.open("a").write(json.dumps(event)+"\n")

def place_order(symbol, side, qty, price=None):
    e = {"id": str(uuid.uuid4())[:8], "symbol":symbol, "side":side, "qty":qty,
         "price": price or "market", "ts": int(time.time()*1000)}
    _log({"type":"place", **e}); return e

def cancel_order(ord_id): _log({"type":"cancel","id":ord_id})

def move_sl(ord_id,new_sl): _log({"type":"move_sl","id":ord_id,"sl":new_sl})

def get_equity(): return 10_000.0