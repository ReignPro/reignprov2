import subprocess
import pathlib

# Paths - update these to your actual paths
PARSER_SCRIPT = pathlib.Path("developerparser.py")           # latest parser script
ZIP_FILE = pathlib.Path("archive_exports/illusion.zip")      # updated zip export location
OUTPUT_CSV = pathlib.Path("illusion_parsed.csv")              # output CSV file

def run_parser():
    cmd = [
        "python",
        str(PARSER_SCRIPT),
        str(ZIP_FILE),
        "-o",
        str(OUTPUT_CSV),
        "-v"
    ]
    print(f"Running parser with command:\n{' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("Parser stdout:")
    print(result.stdout)
    if result.stderr:
        print("Parser stderr:")
        print(result.stderr)

    if result.returncode == 0:
        print(f"[OK] Parsing complete. Output saved to {OUTPUT_CSV}")
    else:
        print("[ERROR] Parsing failed.")

if __name__ == "__main__":
    run_parser()
