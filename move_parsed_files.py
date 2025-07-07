from pathlib import Path
import shutil

# Set these to your actual folders
EXPORTS_FOLDER = Path("C:/Users/mralo/downloads/reignprov1/live_exports")
PARSED_RESULTS_FOLDER = Path("C:/Users/mralo/downloads/reignprov1/trade_dashboard/parsed_results")

PARSED_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

# Copy all JSON files from live_exports to parsed_results
for json_file in EXPORTS_FOLDER.glob("*.json"):
    dest = PARSED_RESULTS_FOLDER / json_file.name
    shutil.copy2(json_file, dest)
    print(f"Copied {json_file} to {dest}")

