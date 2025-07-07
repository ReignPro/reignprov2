def extract_trade_from_message(message: str) -> dict:
    """
    Extracts entry, stop loss, and targets from a raw Discord message string.
    """
    return {
        "entry": None,
        "stop_loss": None,
        "targets": [],
        "direction": None,
        "coin": None
    }
