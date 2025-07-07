import re

def extract_trade_from_message(message: str) -> dict:
    """
    Extracts entry, stop loss, and targets from a raw Discord message string for Fatty's trade signals.
    """

    # Normalize text
    message = message.lower().replace(",", "").replace("`", "")

    # Try to identify trade direction
    direction = None
    if "long" in message:
        direction = "LONG"
    elif "short" in message:
        direction = "SHORT"

    # Match entry price
    entry_match = re.search(r"(entry|buy in|buy at|buy):?\s*(\d+\.\d+)", message)
    entry = float(entry_match.group(2)) if entry_match else None

    # Match stop loss
    sl_match = re.search(r"(stop.?loss|sl|stop):?\s*(\d+\.\d+)", message)
    stop_loss = float(sl_match.group(2)) if sl_match else None

    # Match targets (tp1, tp2, tp3 etc.)
    targets = []
    tp_matches = re.findall(r"(tp\d*|target\d*):?\s*(\d+\.\d+)", message)
    if tp_matches:
        targets = [float(tp[1]) for tp in tp_matches]

    # Match trading pair (e.g., $ETH, ETH/USDT)
    coin_match = re.search(r"(\$?[A-Z]{2,10})(/USDT)?", message)
    coin = coin_match.group(1).replace("$", "") if coin_match else None

    return {
        "entry": entry,
        "stop_loss": stop_loss,
        "targets": targets,
        "direction": direction,
        "coin": coin
    }
