#!/usr/bin/env python3
"""
trade_parser.py v2.5  –  universal, order-agnostic, chart-aware
---------------------------------------------------------------
• catches Illusion, Jotham, Sn06, Xvek, Khalil, Tyler (and future mix-ups)
• ENTRY / TP / SL can appear in any order (or on separate lines)
• accepts EP | ENTRY | CMP | LIMIT  –  TP/TP1/TARGET/T🎯  –  SL/S/STOP/INVALID
• range "0.18-0.16", single numbers, or comma-separated lists
• ignores emojis, "(2.8 %)", duplicated Discord messages
• if an image is attached, adds  chart=<url>  field
usage:
    python trade_parser.py export.zip                    # pretty JSON to console
    python trade_parser.py export.zip -o trades.csv      # CSV file
    python trade_parser.py export.zip --echo 40          # peek 40 raw lines
    python trade_parser.py export.zip -v                 # verbose parse / skip
"""
from __future__ import annotations 
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
import yaml
import itertools
from collections import deque
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import ssl

GROUP_WINDOW = timedelta(seconds=30)

# Download symbols from CoinGecko API, cache locally
def _valid_symbols(cache="symbols.json", max_age=86_400):
    p = pathlib.Path(cache)
    if not p.exists() or time.time() - p.stat().st_mtime > max_age:
        url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        data = json.load(urllib.request.urlopen(url, context=ctx))
        p.write_text(json.dumps([d["symbol"].upper() for d in data]))
    return set(json.loads(p.read_text()))

VALID_SYMBOLS = _valid_symbols()

IGNORE = {"EVERYONE", "SHEIK", "RATS", "LONG", "SHORT", "BTC_USDT", ""}

# Regex patterns
SYMBOL_RE = re.compile(r"\$?([A-Za-z]{2,10})\b")
SIDE_RE   = re.compile(r"\b(long|short|buy|sell)\b", re.I)
ENTRY_RE  = re.compile(r"\b(entry|ep|cmp|limit|buy\s+zone|sell\s+zone)\b", re.I)
TP_RE     = re.compile(r"\b(tp\d?|targets?|🎯|take\s*profit)\b", re.I)
SL_RE     = re.compile(r"\b(sl|s\b|stop(?:\s*loss)?|invalid(?:ation)?)\b", re.I)
NUM_RE    = r"\d+(?:\.\d+)?(?:[eE]-?\d+)?"

UPDATE_RGX = re.compile(r"\b(tp\d?|sl|stop|invalid|cancel|exit|close|update|book|breakeven|break\-even)\b", re.I)

# Helpers
def _mid(a: float, b: float|None) -> float:
    return (a+b)/2 if b is not None else a

def _nums(seg: str) -> list[float]:
    return [float(x) for x in re.findall(NUM_RE, seg)]

def _extract_chart(msg: dict[str,any]) -> str|None:
    for att in msg.get("attachments", []):
        url = att.get("url", "").lower()
        if url.endswith((".png",".jpg",".jpeg",".webp",".gif")):
            return att["url"]
    return None

def parse_message(txt: str) -> dict|None:
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

    def seg(a,b): return txt[a:b]
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

def iter_messages(path: pathlib.Path) -> iter:
    if path.suffix==".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".json"):
                    yield from json.loads(z.read(n).decode("utf-8","ignore")).get("messages",[])
    elif path.suffix==".json":
        yield from json.loads(path.read_bytes().decode("utf-8","ignore")).get("messages",[])
    else:
        raise ValueError("unsupported file")

def _group_messages(msg_iter):
    buf = deque()
    for m in msg_iter:
        buf.append(m)
        while (buf and isoparse(m.get("timestamp")) - isoparse(buf[0].get("timestamp")) > GROUP_WINDOW):
            yield list(buf)
            buf.popleft()
    if buf:
        yield list(buf)

def process(path: pathlib.Path, out: pathlib.Path|None, verbose=False):
    seen = set()
    trades = []
    skipped = 0
    last_trade = None

    for group in _group_messages(iter_messages(path)):
        # Merge grouped messages into one text block to improve multiline detection
        text = "\n".join(m.get("content","") for m in group)
        t = parse_message(text)
        if t:
            ch = _extract_chart(group[-1])
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
            last_trade = t
            if verbose:
                try:
                    print("✅", textwrap.shorten(text, 80))
                except Exception:
                    print("✅", text[:80])
        else:
            if last_trade and UPDATE_RGX.search(text):
                last_trade.setdefault("updates", []).append(text.strip())
                continue
            elif verbose:
                try:
                    print("❌", textwrap.shorten(text, 80))
                except Exception:
                    print("❌", text[:80])

    if out:
        if not trades:
            print("[OK] No trades found, CSV not written.")
            return

        out.parent.mkdir(exist_ok=True)
        headers = []
        for t in trades:
            for k in t.keys():
                if k not in headers:
                    headers.append(k)

        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            rows = []
            for t in trades:
                row = t.copy()
                if "updates" in row:
                    row["updates"] = " | ".join(row["updates"])
                if "tp" in row:
                    row["tp"] = " | ".join(map(str, row["tp"]))
                rows.append(row)
            writer.writerows(rows)

        print(f"[OK] wrote {len(trades)} trades → {out.name}")
    else:
        print(json.dumps(trades, indent=2))
        print(f"[OK] trades: {len(trades)}  skipped: {skipped}")

if __name__ == "__main__":
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
