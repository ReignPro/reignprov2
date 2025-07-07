# ── signal_parser.py ──
import re

# regex picks up:  LONG BTC entry 65000 tp1 66000 tp2 67000 sl 64000
SL_WORDS  = r"(?:sl|s\.l\.|stop|stop ?loss|stoploss)"
TP_WORDS  = r"(?:tp|target)"
ENTRY_RE  = r"(?:entry|@|at)"

TRADE_RE = re.compile(
    rf"(?P<side>LONG|SHORT)\s+"
    rf"(?P<symbol>[A-Z]+)\s*"
    rf"{ENTRY_RE}\s*[:\-]?\s*(?P<entry>\d+[\d.]+)"
    rf".*?{TP_WORDS}1?\s*[:\-]?\s*(?P<tp1>\d+[\d.]+)"
    rf".*?{TP_WORDS}2?\s*[:\-]?\s*(?P<tp2>\d+[\d.]+)"
    rf".*?{SL_WORDS}\s*[:\-]?\s*(?P<sl>\d+[\d.]+)",
    re.IGNORECASE | re.DOTALL
)


def parse_message(msg_text: str):
    """
    Return dict {'symbol','side','entry','sl','tp':[tp1,tp2]} or None.
    """
    m = TRADE_RE.search(msg_text)
    if not m:
        return None
    d = m.groupdict()
    return {
        "symbol": f"{d['symbol']}-USDT",
        "side":   d['side'].upper(),          # LONG / SHORT
        "entry":  float(d['entry']),
        "sl":     float(d['sl']),
        "tp": [float(d['tp1']), float(d['tp2'])],  # ← fixed line
    }

