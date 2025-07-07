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

IGNORE = {"EVERYONE", "SHEIK", "RATS", "LONG", "SHORT", "BTC_USDT", ""}

# Regex patterns
import re

# Symbols (tickers): Allow 2-10 letters, with optional $ prefix
SYMBOL_RE = re.compile(r"\$?([A-Za-z]{2,10})\b")

# Trade side: Include long/short plus buy/sell variants and common shorthand
SIDE_RE = re.compile(
    r"\b(long|short|buy|sell|going\s*long|going\s*short|entry\s*long|entry\s*short|"
    r"longer|shorter|longish|shortish|bullish|bearish|go\s*long|go\s*short|"
    r"buying|selling)\b",
    re.I
)

# Entry keywords: lots of variations and synonyms
ENTRY_RE = re.compile(
    r"\b(entry|ep|e\.p\.|cmp|limit|buy\s*zone|sell\s*zone|open|open\s*price|"
    r"trigger|entry\s*zone|zone\s*at|range|dip\s*zone|in\s*at|scaling\s*in\s*at|"
    r"initiate|buy\s*between|buy\s*from|long\s*from|short\s*from|take\s*entry|"
    r"consider|get\s*in\s*around|watch\s*for\s*reclaim|floor|bottom)\b",
    re.I
)

# Take Profit (TP) keywords with variations, emojis, and shorthand
TP_RE = re.compile(
    r"\b(tp\d?|t\.p\.?|targets?|target|take\s*profit|profit\s*target|"
    r"first\s*target|second\s*target|final\s*target|scale\s*out|trim\s*at|"
    r"close\s*partial|exit\s*at|objectives|tgt|🎯|pt|partial)\b",
    re.I
)

# Stop Loss (SL) keywords and common variants
SL_RE = re.compile(
    r"\b(sl|s\b|stop(?:\s*loss)?|invalid(?:ation)?|risk|cut|exit\s*if\s*below|"
    r"exit\s*if\s*under|close\s*if\s*below|invalidate\s*below|risk\s*under|"
    r"stop\s*under|loss\s*if\s*below|protect\s*at|drop\s*below|flush\s*below|"
    r"pullback\s*under|manual\s*sl|tight\s*sl|tight\s*stop|stoploss|stoplosses)\b",
    re.I
)

# Numbers - including scientific notation
NUM_RE = r"\d+(?:\.\d+)?(?:[eE]-?\d+)?"



def _mid(a: float, b: float|None) -> float:
    return (a+b)/2 if b is not None else a

def _nums(seg: str):
    return [float(x) for x in re.findall(NUM_RE, seg)]

def _extract_chart(msg):
    for att in msg.get("attachments", []):
        url = att.get("url", "").lower()
        if url.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            return att["url"]
    return None

def parse_message(txt):
    sym_m  = SYMBOL_RE.search(txt)
    side_m = SIDE_RE.search(txt)
    ent_m  = ENTRY_RE.search(txt)
    tp_m   = TP_RE.search(txt)
    sl_m   = SL_RE.search(txt)
    if not (sym_m and side_m and ent_m and tp_m and sl_m):
        return None

    symbol = sym_m.group(1).upper()
    side_word = side_m.group(1).upper()
    side = "LONG" if side_word in ("LONG","BUY") else "SHORT"

    def seg(a, b): return txt[a:b]
    spans = sorted([(ent_m.start(),'E',ent_m.end()),
                    (tp_m.start(),'T',tp_m.end()),
                    (sl_m.start(),'S',sl_m.end())])
    blocks = {k: seg(end, spans[i+1][0] if i+1<len(spans) else len(txt))
              for i,(_,k,end) in enumerate(spans)}

    e_nums = _nums(blocks['E'])
    t_nums = _nums(blocks['T'])
    s_nums = _nums(blocks['S'])
    if not (e_nums and t_nums and s_nums):
        return None

    entry = _mid(e_nums[0], e_nums[1] if len(e_nums)>=2 else None)
    tp    = t_nums
    sl    = s_nums[0]

    if side=="LONG" and sl>=entry:  return None
    if side=="SHORT"and sl<=entry:  return None

    return {"symbol":symbol,"side":side,"entry":round(entry,8),
            "tp":[round(x,8) for x in tp],"sl":round(sl,8)}

def iter_messages(path: pathlib.Path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".json"):
                    try:
                        data = json.loads(z.read(n).decode("utf-8", "ignore"))
                        yield from data.get("messages", [])
                    except json.JSONDecodeError as e:
                        print(f"Warning: Skipping corrupted file {n} in {path.name}: {e}")
    elif path.suffix == ".json":
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                yield from data.get("messages", [])
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON file {path.name}: {e}")
    else:
        raise ValueError("Unsupported file type")

def process(path: pathlib.Path, out: pathlib.Path|None, verbose=False):
    seen = set()
    trades = []
    skipped = 0
    for m in iter_messages(path):
        mid = m.get("id") or ""
        if mid in seen:
            continue
        seen.add(mid)

        t = parse_message(m.get("content",""))
        if t:
            ch = _extract_chart(m)
            if ch:
                t["chart"] = ch

            sym = t["symbol"].upper()
            if sym in IGNORE or sym not in VALID_SYMBOLS:
                skipped += 1
                continue

            e = t["entry"]
            t["tp"] = [tp for tp in t["tp"] if 0 < tp < e*10]
            if not t["tp"] or t["sl"] <= 0 or t["sl"] >= e*10:
                skipped += 1
                continue

            trades.append(t)
            if verbose:
                print("✅", textwrap.shorten(m["content"], 80))
        elif verbose:
            print("✗", textwrap.shorten(m["content"], 80))

    if out:
        out.parent.mkdir(exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            if trades:
                csv.DictWriter(f, fieldnames=trades[0].keys()).writeheader()
                csv.writer(f).writerows([t.values() for t in trades])
        print(f"[OK] wrote {len(trades)} trades → {out.name}")
    else:
        print(json.dumps(trades, indent=2))
        print(f"[OK] trades: {len(trades)}  skipped: {skipped}")

if __name__=="__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--echo", type=int, metavar="N")
    a = ap.parse_args()
    fp = pathlib.Path(a.path)
    if a.echo:
        for i,m in enumerate(iter_messages(fp)):
            if i >= a.echo:
                break
            print(textwrap.shorten(m.get("content", ""), 120))
        sys.exit()
    process(fp, pathlib.Path(a.out) if a.out else None, a.verbose)
