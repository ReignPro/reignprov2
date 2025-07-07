import os
from dotenv import load_dotenv; load_dotenv()

MODE = os.getenv("MODE", "demo").lower()

if MODE == "live":
    from blofin_live import get_equity as get_equity_usdt
else:
    from core.blofin_mock import get_equity_usdt