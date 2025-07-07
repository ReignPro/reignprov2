# ReignProBot v2

Discord-based automated trading bot that:
- Parses trade signals from multiple traders
- Executes trades via BloFin API
- Sends alerts and tracks performance
- Supports modular parser logic per trader

## Folder Structure
- `core/` – execution logic and exchange interfacing
- `configs/` – bot config files (risk, cooldown, parsing rules)
- `parsers/` – signal parsing logic per trader
- `exports/` – auto-exported Discord logs
- `scripts/` – helpers, manual runners, tools
- `utils/` – logging and shared helpers
