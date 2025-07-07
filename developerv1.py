#!/usr/bin/env python3
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
import codecs

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
SYMBOL_RE = re.compile(r"\$?([A-Za-z]{2,10})\b")
SIDE_RE   = re.compile(r"\b(long|short|buy|sell)\b", re.I)
ENTRY_RE  = re.compile(r"\b(entry|ep|cmp|limit|buy\s+zone|sell\s+zone)\b", re.I)
TP_RE     = re.compile(r"\b(tp\d?|targets?|🎯|take\s*profit)\b", re.I)
SL_RE     = re.compile(r"\b(sl|s\b|stop(?:\s*loss)?|invalid(?:ation)?)\b", re.I)
NUM_RE    = r"\d+(?:\.\d+)?(?:[eE]-?\d+)?"

UPDATE_RGX = re.compile(r"tp\d?|sl|stop|breakeven|exit", re.I)

def _mid(a: float, b: float|None) -> float:
    return (a+b)/2 if b is not None else a

def _nums(seg: str):
    return [float(x) for x in re.findall(NUM_RE, seg)]

def _extract_chart(msg: dict):
    for att in msg.get("attachments", []):
        url = att.get("url","").lower()
        if url.endswith((".png",".jpg",".jpeg",".webp",".gif")):
            return att["url"]
    return None

def parse_message(txt: str):
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
    if path.suffix==".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".json"):
                    yield from json.loads(z.read(n).decode("utf-8","ignore")).get("messages",[])
    elif path.suffix==".json":
        yield from json.loads(path.read_bytes().decode("utf-8","ignore")).get("messages",[])
    else:
        raise ValueError("unsupported file")

def process(fp: pathlib.Path, out: pathlib.Path|None, verbose=False):
    seen=set()
    trades=[]
    skipped=0
    last_trade=None
    for m in iter_messages(fp):
        mid=m.get("id") or ""
        if mid in seen: continue
        seen.add(mid)

        text = m.get("content","")
        t=parse_message(text)
        if t:
            ch=_extract_chart(m)
            if ch: t["chart"]=ch

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
                print("[OK]", textwrap.shorten(text.encode('ascii', 'ignore').decode(), 80))
        else:
            if last_trade and UPDATE_RGX.search(text):
                last_trade.setdefault("updates", []).append(text.strip())
                continue
            elif verbose:
                print("[SKIP]", textwrap.shorten(text.encode('ascii', 'ignore').decode(), 80))

    if out:
        if not trades:
            print("[OK] No trades found, CSV not written.")
            return

        headers = []
        for t in trades:
            for k in t.keys():
                if k not in headers:
                    headers.append(k)

        rows_to_write = []
        for t in trades:
            row = t.copy()
            if "updates" in row:
                row["updates"] = " | ".join(row["updates"])
            if "tp" in row:
                row["tp"] = " | ".join(map(str,row["tp"]))
            rows_to_write.append(row)

        out.parent.mkdir(exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows_to_write)
        print(f"[OK] wrote {len(trades)} trades → {out.name}")
    else:
        print(json.dumps(trades, indent=2))
        print(f"[OK] trades:{len(trades)}  skipped:{skipped}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o","--out")
    ap.add_argument("-v","--verbose", action="store_true")
    ap.add_argument("--echo", type=int, metavar="N")
    a=ap.parse_args()
    fp=pathlib.Path(a.path)
    if a.echo:
        for i,m in enumerate(iter_messages(fp)):
            if i>=a.echo:
                break
            print(textwrap.shorten(m.get("content",""), 120))
        sys.exit()
    process(fp, pathlib.Path(a.out) if a.out else None, a.verbose)
