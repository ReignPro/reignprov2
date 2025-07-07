import os
import json
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CONFIG
EXPORT_FOLDER = "live_exports"
RUN_MODE = "LIVE"  # Set to "DEMO" or "LIVE"

# Logger Setup (emoji-safe)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Bot")

def process_trade_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            trades = json.load(f)
        logger.info(f"📝 Loaded {len(trades)} trade(s) from {filepath}")
        for trade in trades:
            trader = trade.get("trader")
            symbol = trade.get("symbol")
            direction = trade.get("direction")
            entry = trade.get("entry")
            stop = trade.get("stop")
            tp1 = trade.get("tp1")
            logger.info(f"📈 Trade from {trader}: {direction} {symbol} at {entry}, SL: {stop}, TP1: {tp1}")
            # Future: Add trade execution or routing logic here
    except Exception as e:
        logger.error(f"❌ Failed to process {filepath}: {e}")

class TradeFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith("latest.json"):
            return
        logger.info(f"📂 Detected update: {event.src_path}")
        process_trade_file(event.src_path)

def watch_folder(folder_path):
    abs_path = os.path.abspath(folder_path)
    logger.info(f"[Bot] Running in {RUN_MODE} mode")
    logger.info(f"[Bot] Watching folder: {abs_path}")
    logger.info("[Bot] Watching for new exports...")

    event_handler = TradeFileHandler()
    observer = Observer()
    observer.schedule(event_handler, abs_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    watch_folder(EXPORT_FOLDER)
