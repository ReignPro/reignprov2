import os
from dotenv import load_dotenv; load_dotenv()

MODE = os.getenv("MODE", "demo").lower()

if MODE == "live":
    from blofin_live import place_order, get_equity, cancel_order, move_sl
else:
    from blofin_mock import place_order, get_equity, cancel_order, move_sl 