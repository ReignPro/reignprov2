import pathlib
import subprocess

JSON_DIR = pathlib.Path("archive_exports/unkn0wn")
OUTPUT_DIR = pathlib.Path("parsed_outputs/unkn0wn")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_parser(json_path: pathlib.Path):
    out_csv = OUTPUT_DIR / f"{json_path.stem}_parsed.csv"
    cmd = [
        "python",
        "developerv2.py",
        str(json_path),
        "-o",
        str(out_csv),
        "-v"
    ]
    print(f"Parsing {json_path.name} -> {out_csv.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error parsing {json_path.name}:")
        print(result.stderr)
    else:
        print(f"Parsed {json_path.name} successfully.")

def main():
    for json_file in sorted(JSON_DIR.glob("*.json")):
        run_parser(json_file)
    print("All done.")

if __name__ == "__main__":
    main()
