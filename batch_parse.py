import subprocess
import pathlib
import csv

ARCHIVE_DIR = pathlib.Path("archive_exports")
OUTPUT_DIR = pathlib.Path("parsed_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

def run_parser(zip_path: pathlib.Path):
    out_csv = OUTPUT_DIR / f"{zip_path.stem}_parsed.csv"
    cmd = [
        "python",
        "developerv1.py",
        str(zip_path),
        "-o",
        str(out_csv),
        "-v",
    ]
    print(f"Parsing {zip_path.name} -> {out_csv.name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Error parsing {zip_path.name}:")
        print(proc.stderr)
        return None
    return out_csv

def count_trades(csv_path: pathlib.Path):
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)

def main():
    results = []
    for zip_file in ARCHIVE_DIR.glob("*.zip"):
        csv_file = run_parser(zip_file)
        if csv_file and csv_file.exists():
            count = count_trades(csv_file)
            print(f"Parsed {count} trades from {zip_file.name}")
            results.append((zip_file.name, count))
        else:
            results.append((zip_file.name, 0))

    print("\nSummary:")
    for trader, count in results:
        print(f"{trader}: {count} trades parsed")

if __name__ == "__main__":
    main()
