@echo off
setlocal enabledelayedexpansion

set PARSER=developerv2.py
set EXPORTS_DIR=archive_exports

rem List of trader zip files (add/remove as needed)
set TRADERS=illusion Jotham Sn06 xvek Khalil Tyler unkn0wn

for %%T in (%TRADERS%) do (
    echo Parsing %%T.zip ...
    python %PARSER% %EXPORTS_DIR%\%%T.zip -o %%T_parsed.csv -v > %%T_parse.log 2>&1
    if errorlevel 1 (
        echo Error parsing %%T.zip, check %%T_parse.log for details
    ) else (
        echo [OK] wrote trades to %%T_parsed.csv
    )
)

echo All parsing done.
pause
