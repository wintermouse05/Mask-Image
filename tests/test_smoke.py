import os
import shutil
import tempfile
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image, ImageDraw, ImageFont

import pytest
import pytesseract

from src.main import main as cli_main


def has_tesseract() -> bool:
    try:
        # This will raise if tesseract is not found
        _ = pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def make_sample_xlsx(path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws['A1'] = 'Sample with image headers'

    # Create an image with a sensitive header
    img = Image.new('RGB', (600, 120), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"
    d.text((10, 40), text, fill=(0, 0, 0))
    img_path = os.path.join(os.path.dirname(path), 'sample.png')
    img.save(img_path)

    xli = XLImage(img_path)
    xli.width = 600
    xli.height = 120
    ws.add_image(xli, 'B3')

    wb.save(path)


@pytest.mark.skipif(not has_tesseract(), reason="Tesseract OCR is not installed or not on PATH")
def test_smoke(tmp_path):
    input_xlsx = tmp_path / 'input.xlsx'
    make_sample_xlsx(str(input_xlsx))

    output_xlsx = tmp_path / 'output.xlsx'
    # Run CLI
    import sys
    argv_backup = list(sys.argv)
    try:
        sys.argv = ['prog', '--input', str(input_xlsx), '--output', str(output_xlsx)]
        cli_main()
    finally:
        sys.argv = argv_backup

    assert output_xlsx.exists()
