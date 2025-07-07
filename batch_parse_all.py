import subprocess
import pathlib

EXPORTS_DIR = pathlib.Path("./archive_exports")  # Your exports folder
PARSER_SCRIPT = pathlib.Path("parserv1_1.py")   # Your parser script filename

def main():
    for file_path in EXPORTS_DIR.glob("*.zip"):
        output_csv = EXPORTS_DIR / (file_path.stem + "_parsed.csv")
        print(f"Parsing {file_path.name} -> {output_csv.name} ...")
        subprocess.run([
            "python", str(PARSER_SCRIPT),
            str(file_path),
            "-o", str(output_csv)
        ])

if __name__ == "__main__":
    main()

