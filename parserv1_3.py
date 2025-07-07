import re
import json
import csv
import sys
import zipfile
import pathlib
import argparse
import textwrap
import urllib.request
import time

# Download symbols from CoinGecko API, cache locally
def _download_symbol_list(cache="symbols.json", max_age=86_400):
    p = pathlib.Path(cache)
    if not p.exists() or time.time() - p.stat().st_mtime > max_age:
        url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
        data = json.load(urllib.request.urlopen(url))
        p.write_text(json.dumps([d["symbol"].upper() for d in data]))
    return set(json.loads(p.read_text()))

VALID_SYMBOLS = _download_symbol_list()  # e.g. {'BTC', 'ETH', ...}

# List of words to ignore as symbols (like chat commands or keywords)
IGNORE = {"EVERYONE", "SHEIK", "RATS", "LONG", "SHORT", "BTC_USDT", ""}

# Map common aliases or suffix variants to canonical symbols
ALIAS_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "PEPE3L": "PEPE",
    "ORDIPERP": "ORDI",
    "GMXUSDT": "GMX",
    "APT-PERP": "APT",
    "RNDRPERP": "RNDR",
    "FLOKIUSDT": "FLOKI",
    # Add more as needed
}

def clean_symbol(symbol: str) -> str:
    # Remove common suffixes
    suffixes = ['USDT', 'BUSD', 'PERP', '3L', '3S', '1X', '2X', '5X']
    for suffix in suffixes:
        if symbol.endswith(suffix):
            symbol = symbol[:-len(suffix)]
    return symbol.upper()

def extract_symbol(text: str, valid_symbols: set, alias_map: dict) -> str | None:
    # Match $SYMBOL or just SYMBOL with 2-5 uppercase letters/numbers
    pattern = r"\$?([A-Z0-9]{2,5})\b"
    matches = re.findall(pattern, text.upper())
    for match in matches:
        cleaned = clean_symbol(match)
        # Check alias map first
        if cleaned in alias_map:
            return alias_map[cleaned]
        # Accept only if in valid symbol whitelist and not in ignore list
        if cleaned in valid_symbols and cleaned not in IGNORE:
            return cleaned
    return None

# Regex patterns for side, entry, TP, SL, numbers
SIDE_RE   = re.compile(r"\b(long|short|buy|sell)\b", re.I)
ENTRY_RE  = re.compile(r"\b(entry|ep|cmp|limit|buy\s+zone|sell\s+zone)\b", re.I)
TP_RE     = re.compile(r"\b(tp\d?|targets?|🎯|take\s*profit)\b", re.I)
SL_RE     = re.compile(r"\b(sl|s\b|stop(?:\s*loss)?|invalid(?:ation)?)\b", re.I)
NUM_RE    = r"\d+(?:\.\d+)?(?:[eE]-?\d+)?"

def _mid(a: float, b: float|None) -> float:
    return (a+b)/2 if b is not None else a

def _nums(seg: str) -> list[float]:
    return [float(x) for x in re.findall(NUM_RE, seg)]

def parse_message(txt: str) -> dict | None:
    # Extract symbol with improved function
    symbol = extract_symbol(txt, VALID_SYMBOLS, ALIAS_MAP)
    if not symbol:
        return None

    # Extract side, entry, tp, sl keywords
    side_m = SIDE_RE.search(txt)
    entry_m = ENTRY_RE.search(txt)
    tp_m = TP_RE.search(txt)
    sl_m = SL_RE.search(txt)

    if not (side_m and entry_m and tp_m and sl_m):
        return None

    side_word = side_m.group(1).upper()
    side = "LONG" if side_word in ("LONG", "BUY") else "SHORT"

    # Define slices regardless of order
    def seg(a, b): return txt[a:b]
    spans = sorted([
        (entry_m.start(), 'E', entry_m.end()),
        (tp_m.start(), 'T', tp_m.end()),
        (sl_m.start(), 'S', sl_m.end()),
    ])
    blocks = {k: seg(end, spans[i+1][0] if i+1 < len(spans) else len(txt)) for i, (_, k, end) in enumerate(spans)}

    e_nums = _nums(blocks['E'])
    t_nums = _nums(blocks['T'])
    s_nums = _nums(blocks['S'])
    if not (e_nums and t_nums and s_nums):
        return None

    entry = _mid(e_nums[0], e_nums[1] if len(e_nums) >= 2 else None)
    tp = t_nums
    sl = s_nums[0]

    # Sanity: SL on correct side
    if side == "LONG" and sl >= entry:
        return None
    if side == "SHORT" and sl <= entry:
        return None

    return {
        "symbol": symbol,
        "side": side,
        "entry": round(entry, 8),
        "tp": [round(x, 8) for x in tp],
        "sl": round(sl, 8)
    }

def iter_messages(path: pathlib.Path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".json"):
                    yield from json.loads(z.read(n).decode("utf-8", "ignore")).get("messages", [])
    elif path.suffix == ".json":
        yield from json.loads(path.read_bytes().decode("utf-8", "ignore")).get("messages", [])
    else:
        raise ValueError("Unsupported file")

def process(path: pathlib.Path, out: pathlib.Path | None, verbose=False):
    seen = set()
    trades = []
    skipped = 0
    for m in iter_messages(path):
        mid = m.get("id") or ""
        if mid in seen:
            continue
        seen.add(mid)

        content = m.get("content", "")
        t = parse_message(content)
        if t:
            # Optional chart extraction
            attachments = m.get("attachments", [])
            for att in attachments:
                url = att.get("url", "").lower()
                if url.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                    t["chart"] = att["url"]
                    break

            sym = t["symbol"].upper()
            if sym in IGNORE or sym not in VALID_SYMBOLS:
                skipped += 1
                continue

            e = t["entry"]
            t["tp"] = [tp for tp in t["tp"] if 0 < tp < e * 10]
            if not t["tp"] or t["sl"] <= 0 or t["sl"] >= e * 10:
                skipped += 1
                continue

            trades.append(t)
            if verbose:
                print("✅", textwrap.shorten(content, 80))
        elif verbose:
            print("✗", textwrap.shorten(content, 80))

    if out:
        out.parent.mkdir(exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            if trades:
                csv.DictWriter(f, fieldnames=trades[0].keys()).writeheader()
                csv.writer(f).writerows([t.values() for t in trades])
            else:
                f.write("")  # create empty file if no trades found
        print(f"[OK] wrote {len(trades)} trades → {out.name}")
    else:
        print(json.dumps(trades, indent=2))
        print(f"[OK] trades: {len(trades)}  skipped: {skipped}")

# CLI entrypoint
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--echo", type=int, metavar="N")
    args = ap.parse_args()
    path = pathlib.Path(args.path)

    if args.echo:
        for i, m in enumerate(iter_messages(path)):
            if i >= args.echo:
                break
            print(textwrap.shorten(m.get("content", ""), 120))
        sys.exit()

    process(path, pathlib.Path(args.out) if args.out else None, args.verbose)
