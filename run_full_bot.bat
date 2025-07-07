@echo off
REM Activate Python virtual environment if needed
REM call path\to\venv\Scripts\activate.bat

echo Starting DiscordChatExporter to export latest JSONs...
REM Replace YOUR_DISCORD_TOKEN and CHANNEL_ID with your actual values
start /b DiscordChatExporter.Cli.exe export -t YOUR_DISCORD_TOKEN -c CHANNEL_ID -o live_exports\illusion\latest.json

timeout /t 10

echo Starting live monitor...
start /b python live_monitor.py

timeout /t 10

echo Starting parser...
start /b python parserv1_1.py live_exports\illusion\latest.json -o parsed_results\illusion_parsed.csv -v

timeout /t 10

echo Starting trade enrichment...
start /b python enrich_trade.py parsed_results\illusion_parsed.csv

timeout /t 10

echo Starting order router...
start /b python order_router.py

timeout /t 10

echo Starting alert sender...
start /b python send_alert.py

echo All processes started. Check logs for details.
pause
