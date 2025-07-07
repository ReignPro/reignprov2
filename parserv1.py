import pathlib
import zipfile
import json
import csv
import re
import time
import urllib.request
import textwrap
from difflib import get_close_matches

# Download CoinGecko symbols (or read cached)
def download_coingecko_symbols(cache="symbols.json", max_age=86400):
    p = pathlib.Path(cache)
    if not p.exists() or time.time() - p.stat().st_mtime > max_age:
        url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
        data = json.load(urllib.request.urlopen(url))
        p.write_text(json.dumps([d["symbol"].upper() for d in data]))
    return set(json.loads(p.read_text()))

VALID_SYMBOLS = download_coingecko_symbols()

IGNORE = {"EVERYONE", "SHEIK", "RATS", "LONG", "SHORT", "BTC_USDT", ""}

SYMBOL_RE = re.compile(r"\$?([A-Za-z]{2,10})\b")
SIDE_RE   = re.compile(r"\b(long|short|buy|sell)\b", re.I)
ENTRY_RE  = re.compile(r"\b(entry|ep|cmp|limit|buy\s+zone|sell\s+zone)\b", re.I)
TP_RE     = re.compile(r"\b(tp\d?|targets?|🎯|take\s*profit)\b", re.I)
SL_RE     = re.compile(r"\b(sl|s\b|stop(?:\s*loss)?|invalid(?:ation)?)\b", re.I)
NUM_RE    = r"\d+(?:\.\d+)?(?:[eE]-?\d+)?"

def _mid(a: float, b: float|None) -> float:
    return (a+b)/2 if b is not None else a

def _nums(seg: str):
    return [float(x) for x in re.findall(NUM_RE, seg)]

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

def _extract_chart(msg):
    for att in msg.get("attachments", []):
        url = att.get("url","").lower()
        if url.endswith((".png",".jpg",".jpeg",".webp",".gif")):
            return att["url"]
    return None

def iter_messages_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.endswith(".json"):
                data = json.loads(z.read(n).decode("utf-8","ignore"))
                yield from data.get("messages", [])

def process_trades_for_trader(zip_path, trader_name, output_dir):
    parsed_trades = []
    edge_cases = []
    seen = set()

    for msg in iter_messages_from_zip(zip_path):
        mid = msg.get("id", "")
        if mid in seen:
            continue
        seen.add(mid)

        if msg.get("author", {}).get("name") != trader_name:
            continue

        content = msg.get("content", "")
        parsed = parse_message(content)
        if parsed:
            chart_url = _extract_chart(msg)
            if chart_url:
                parsed["chart"] = chart_url
            sym = parsed["symbol"].upper()
            if sym in IGNORE or sym not in VALID_SYMBOLS:
                edge_cases.append({"id": mid, "content": content})
                continue

            e = parsed["entry"]
            parsed["tp"] = [tp for tp in parsed["tp"] if 0 < tp < e*10]
            if not parsed["tp"] or parsed["sl"] <= 0 or parsed["sl"] >= e*10:
                edge_cases.append({"id": mid, "content": content})
                continue

            parsed_trades.append(parsed)
        else:
            edge_cases.append({"id": mid, "content": content})

    output_dir.mkdir(parents=True, exist_ok=True)

    trades_file = output_dir / f"{trader_name}_parsed_trades.csv"
    edges_file = output_dir / f"{trader_name}_edge_cases.csv"

    if parsed_trades:
        with trades_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=parsed_trades[0].keys())
            writer.writeheader()
            writer.writerows(parsed_trades)

    if edge_cases:
        with edges_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "content"])
            writer.writeheader()
            writer.writerows(edge_cases)

    print(f"[{trader_name}] Parsed trades: {len(parsed_trades)} | Edge cases: {len(edge_cases)}")

def batch_process_traders(export_folder, trader_names, output_folder):
    export_folder = pathlib.Path(export_folder)
    output_folder = pathlib.Path(output_folder)
    for trader in trader_names:
        zip_path = export_folder / f"{trader}.zip"
        if zip_path.exists():
            print(f"Processing {trader}...")
            process_trades_for_trader(zip_path, trader, output_folder)
        else:
            print(f"Missing zip for {trader}: {zip_path}")

if __name__ == "__main__":
    import pathlib

    EXPORT_FOLDER = "./archive_exports"  # Your zipped export folder here
    OUTPUT_FOLDER = "./parsed_results"
    TRADERS = [
        "_illusiontrading436", "jotham", "khalil", "sn06", "tyler", "unkn0wn", "xvek"
    ]

    batch_process_traders(EXPORT_FOLDER, TRADERS, OUTPUT_FOLDER)
