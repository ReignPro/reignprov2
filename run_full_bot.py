import subprocess
import time

def run_process(command, wait=10):
    print(f"Starting: {command}")
    proc = subprocess.Popen(command, shell=True)
    time.sleep(wait)
    return proc

def main():
    # Discord Exporter command - update your token and channel ID
    discord_export_cmd = r'DiscordChatExporter.Cli.exe export -t YOUR_DISCORD_TOKEN -c CHANNEL_ID -o live_exports\illusion\latest.json'
    run_process(discord_export_cmd)

    # Live monitor
    live_monitor_cmd = 'python live_monitor.py'
    run_process(live_monitor_cmd)

    # Parser
    parser_cmd = r'python parserv1_1.py live_exports\illusion\latest.json -o parsed_results\illusion_parsed.csv -v'
    run_process(parser_cmd)

    # Trade enrichment
    enrichment_cmd = r'python enrich_trade.py parsed_results\illusion_parsed.csv'
    run_process(enrichment_cmd)

    # Order router
    order_router_cmd = 'python order_router.py'
    run_process(order_router_cmd)

    # Alert sender
    alert_cmd = 'python send_alert.py'
    run_process(alert_cmd)

    print("All processes started. Monitor logs for output.")

if __name__ == "__main__":
    main()
