import argparse
import json
import os
from typing import Iterable, Optional

from .excel_io import extract_images, write_masked_images
from .ocr_mask import mask_image_file
from .patterns import PatternSet
from .types import MaskConfig


def parse_args():
    p = argparse.ArgumentParser(description='Mask sensitive info in Excel-embedded images via OCR')
    p.add_argument('--input', '-i', required=True, help='Path to input Excel file (.xlsx)')
    p.add_argument('--output', '-o', required=True, help='Path to output Excel file')
    p.add_argument('--sheets', nargs='*', default=None, help='Sheet names to process; use "all" for all sheets')
    p.add_argument('--sheet', nargs='*', default=None, help='Alias of --sheets')
    p.add_argument('--lang', default='eng', help='Tesseract OCR language')
    p.add_argument('--tesseract-cmd', default=None, help='Path to tesseract.exe if not in PATH')
    p.add_argument('--mask-padding', type=int, default=4, help='Padding around detected text boxes')
    # Pattern selection options
    p.add_argument('--headers', default=None, help='Comma-separated list of header names to mask (e.g., "Authorization,Host,X-API-Key")')
    p.add_argument('--headers-file', default=None, help='File with headers to mask. JSON [..] or newline-separated')
    p.add_argument('--include-default-headers', action='store_true', help='Include built-in sensitive headers in addition to provided headers')
    # Advanced regex control (for power users)
    p.add_argument('--patterns', default=None, help='Comma-separated regex list for sensitive patterns')
    p.add_argument('--patterns-file', default=None, help='JSON file containing {"patterns": [..]} or [..]')
    p.add_argument('--dump-json', default=None, help='Optional path to dump OCR + redaction metadata JSON')
    return p.parse_args()


def main():
    args = parse_args()

    # Accept --sheet or --sheets
    chosen = args.sheets if args.sheets is not None else args.sheet
    sheets = None if chosen in (None, [], ['all']) else chosen

    # Build patterns (priority: explicit regex > headers > defaults)
    if args.patterns_file:
        pattern_set = PatternSet.from_file(args.patterns_file)
    elif args.patterns:
        pattern_set = PatternSet.from_strings([s.strip() for s in args.patterns.split(',') if s.strip()])
    elif args.headers_file:
        pattern_set = PatternSet.from_headers_file(args.headers_file, include_defaults=args.include_default_headers)
    elif args.headers:
        pattern_set = PatternSet.from_headers([s.strip() for s in args.headers.split(',') if s.strip()], include_defaults=args.include_default_headers)
    else:
        pattern_set = PatternSet.default()

    cfg = MaskConfig(lang=args.lang, mask_padding=args.mask_padding, tesseract_cmd=args.tesseract_cmd)

    print('Extracting images from workbook...')
    extracted = extract_images(args.input, sheet_names=sheets)
    print(f'Found {len(extracted)} images')

    replacements = {}
    report = []
    for item in extracted:
        masked_path, redactions, ocr_text = mask_image_file(item.image_path, pattern_set, cfg)
        replacements[item.placement.image_id] = masked_path
        report.append({
            'image_id': item.placement.image_id,
            'sheet': item.placement.sheet_name,
            'cell': item.placement.cell,
            'original': item.image_path,
            'masked': masked_path,
            'redactions': [r.__dict__ for r in redactions],
            'ocr_text': ocr_text,
        })
        print(f"Masked {item.placement.image_id}: {len(redactions)} regions")

    print('Writing masked images back to workbook...')
    write_masked_images(args.input, args.output, replacements)
    print(f'Wrote output to {args.output}')

    if args.dump_json:
        with open(args.dump_json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f'Metadata written to {args.dump_json}')


if __name__ == '__main__':
    main()
