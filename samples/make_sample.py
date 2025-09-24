import os
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image, ImageDraw


def main(out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws['A1'] = 'Sample with image headers'

    # Create an image with sensitive headers
    img = Image.new('RGB', (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    lines = [
        'GET /resource HTTP/1.1',
        'Host: api.example.com',
        'Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789',
        'X-API-Key: 12345-ABCDE-67890-FGHIJ',
    ]
    y = 20
    for line in lines:
        d.text((20, y), line, fill=(0, 0, 0))
        y += 40
    img_path = os.path.join(os.path.dirname(out_path), 'sample.png')
    img.save(img_path)

    xli = XLImage(img_path)
    xli.width = 800
    xli.height = 200
    ws.add_image(xli, 'B3')

    wb.save(out_path)
    print(f"Sample workbook written to {out_path}")


if __name__ == '__main__':
    main(os.path.join(os.path.dirname(__file__), 'input.xlsx'))
