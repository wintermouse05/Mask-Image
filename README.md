# Masking Image by OCR

A Python tool that scans an Excel workbook for embedded images, runs OCR to extract text, detects sensitive headers (e.g., Host, Authorization, X-API-Key), and masks the corresponding regions in the images. The tool outputs a new Excel workbook with masked images preserved in their original positions.

## Features
- Read embedded images from .xlsx workbooks (via openpyxl) and .xls/.xlsm via COM (optional, Windows only).
- OCR with Tesseract via pytesseract.
- Redact predefined sensitive headers using simple rules + regex.
- Reinsert masked images at the same cell positions.

## Requirements
- Windows (for best compatibility with Excel COM, though .xlsx works cross-platform).
- Python 3.10+
- Tesseract OCR installed and in PATH. Download: https://github.com/UB-Mannheim/tesseract/wiki

## Quick start
1. Ensure Tesseract is installed and accessible from PATH (or configure path via `--tesseract-cmd`).
2. Install dependencies.
3. Run the masking script.

```powershell
# From the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Optional: create a sample workbook with an image
python .\samples\make_sample.py

# Run as a module (ensures package imports work)
python -m src.main --input .\samples\input.xlsx --output .\out\masked.xlsx --sheets all --headers "Authorization,Host,X-API-Key"
```

## Configuration
- Choose which headers to mask (recommended and simplest):
	- Inline: `--headers "Authorization,Host,X-API-Key"`
	- From file: `--headers-file .\\headers.txt` (newline-separated) or JSON `["Authorization","Host"]`
	- Add built-ins too: `--include-default-headers`
- Power users can provide custom regex patterns via `--patterns` (comma-separated regex), or a JSON file via `--patterns-file`.
- Control OCR language with `--lang` (default: eng).

## Limitations
- OCR bounding boxes are approximate; masking may include extra padding. Fine-tune via `--mask-padding`.
- Detecting where text sits in an image is OCR-dependent; complex backgrounds may reduce accuracy.
- Reading embedded images from legacy .xls may require Excel to be installed (COM automation).

## Project structure
- `src/main.py` — CLI entry point
- `src/excel_io.py` — Read/write images and positions in Excel
- `src/ocr_mask.py` — OCR and masking utilities
- `src/patterns.py` — Sensitive pattern management
- `src/types.py` — Shared dataclasses
- `requirements.txt` — Python dependencies

## Testing
A small smoke test is available:
```powershell
python -m pytest -q
```

## Troubleshooting
- If pytesseract can't find Tesseract, set the path:
```powershell
python src\main.py --input input.xlsx --output masked.xlsx --tesseract-cmd "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```
- The tool attempts auto-detection of Tesseract on Windows in common install paths.
- If Excel isn't closed when using COM, pass `--no-com` to force openpyxl-only path (xlsx only).
