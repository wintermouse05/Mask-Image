from __future__ import annotations
import os
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from .types import MaskConfig, RedactionBox, OCRResult
from .patterns import PatternSet


def configure_tesseract(cfg: MaskConfig):
    if cfg.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
        return
    # Auto-detect common Windows install paths
    possible = [
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
    ]
    for p in possible:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break


def _image_to_data_tiled(image_bgr: np.ndarray, cfg: MaskConfig, max_tile_height: int = 7000, overlap: int = 40) -> Dict[str, List[Any]]:
    """Run Tesseract image_to_data on tall images by slicing into horizontal tiles.
    Returns a merged data dict like pytesseract Output.DICT with top adjusted by tile offsets.
    """
    h, w = image_bgr.shape[:2]
    if h <= max_tile_height:
        return pytesseract.image_to_data(image_bgr, lang=cfg.lang, output_type=Output.DICT)

    keys = [
        'level','page_num','block_num','par_num','line_num','word_num',
        'left','top','width','height','conf','text'
    ]
    merged: Dict[str, List[Any]] = {k: [] for k in keys}

    y = 0
    tile_idx = 0
    step = max_tile_height - overlap
    step = max(step, 1000)
    while y < h:
        y2 = min(y + max_tile_height, h)
        tile = image_bgr[y:y2, :]
        try:
            data = pytesseract.image_to_data(tile, lang=cfg.lang, output_type=Output.DICT)
        except pytesseract.TesseractError:
            # Fallback: downscale tile
            scale = min(1.0, max_tile_height / max(1, tile.shape[0])) * 0.9
            if scale < 1.0:
                tile_small = cv2.resize(tile, (int(tile.shape[1]*scale), int(tile.shape[0]*scale)), interpolation=cv2.INTER_AREA)
                data = pytesseract.image_to_data(tile_small, lang=cfg.lang, output_type=Output.DICT)
                # Need to scale positions back
                sx = tile.shape[1] / max(1, tile_small.shape[1])
                sy = tile.shape[0] / max(1, tile_small.shape[0])
                for i in range(len(data['text'])):
                    data['left'][i] = int(data['left'][i] * sx)
                    data['top'][i] = int(data['top'][i] * sy)
                    data['width'][i] = int(data['width'][i] * sx)
                    data['height'][i] = int(data['height'][i] * sy)
            else:
                raise

        for i in range(len(data['text'])):
            for k in keys:
                v = data[k][i]
                if k == 'top':
                    v = int(v) + y
                merged[k].append(v)
        tile_idx += 1
        if y2 >= h:
            break
        y = y + step

    return merged


def ocr_with_boxes(image_bgr: np.ndarray, cfg: MaskConfig) -> OCRResult:
    data = _image_to_data_tiled(image_bgr, cfg)
    boxes: List[RedactionBox] = []
    lines = {}

    # Group by line number to reconstruct per-line text
    n = len(data['text'])
    for i in range(n):
        text = data['text'][i]
        if not text or text.strip() == '':
            continue
        conf_str = str(data['conf'][i])
        try:
            conf = float(conf_str)
        except Exception:
            conf = -1.0
        if conf < 0:
            continue
        line_id = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        bbox = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
        lines.setdefault(line_id, {'text_parts': [], 'boxes': []})
        lines[line_id]['text_parts'].append(text)
        lines[line_id]['boxes'].append(bbox)

    full_text_lines = []
    for _, info in sorted(lines.items(), key=lambda x: x[0]):
        line_text = ' '.join(info['text_parts'])
        full_text_lines.append(line_text)
    full_text = '\n'.join(full_text_lines)

    return OCRResult(text=full_text, boxes=[])


def detect_sensitive_regions(image_bgr: np.ndarray, ocr_result: OCRResult, patterns: PatternSet, cfg: MaskConfig) -> List[RedactionBox]:
    # Run detailed word-level OCR to get precise boxes (tiled for very tall images)
    data = _image_to_data_tiled(image_bgr, cfg)
    redactions: List[RedactionBox] = []

    n = len(data['text'])
    # Rebuild line mapping to decide which words to mask when a line matches
    line_map = {}
    for i in range(n):
        text = data['text'][i]
        if not text or text.strip() == '':
            continue
        conf_str = str(data['conf'][i])
        try:
            conf = float(conf_str)
        except Exception:
            conf = -1.0
        if conf < 0:
            continue
        line_id = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        bbox = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
        line_map.setdefault(line_id, {'words': [], 'boxes': []})
        line_map[line_id]['words'].append(text)
        line_map[line_id]['boxes'].append(bbox)

    for line_id, info in line_map.items():
        text_line = ' '.join(info['words'])
        # If any sensitive pattern matches the line, mask the entire line box
        matched = patterns.find_matches(text_line)
        if matched:
            # Merge word boxes into a single line rectangle with padding
            xs = [b[0] for b in info['boxes']]
            ys = [b[1] for b in info['boxes']]
            ws = [b[2] for b in info['boxes']]
            hs = [b[3] for b in info['boxes']]
            x1 = max(min(xs) - cfg.mask_padding, 0)
            y1 = max(min(ys) - cfg.mask_padding, 0)
            x2 = max(xs[i] + ws[i] for i in range(len(xs))) + cfg.mask_padding
            y2 = max(ys[i] + hs[i] for i in range(len(ys))) + cfg.mask_padding
            redactions.append(RedactionBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1, label='sensitive'))

    return redactions


def apply_redactions(image_bgr: np.ndarray, redactions: List[RedactionBox], cfg: MaskConfig) -> np.ndarray:
    out = image_bgr.copy()
    for r in redactions:
        x1 = max(r.x, 0)
        y1 = max(r.y, 0)
        x2 = min(r.x + r.w, out.shape[1])
        y2 = min(r.y + r.h, out.shape[0])
        cv2.rectangle(out, (x1, y1), (x2, y2), cfg.mask_color, thickness=-1)
    return out


def mask_image_file(path: str, patterns: PatternSet, cfg: MaskConfig) -> Tuple[str, List[RedactionBox], str]:
    """
    Returns: (masked_image_path, redactions, ocr_text)
    """
    image_bgr = cv2.imread(path)
    if image_bgr is None:
        raise RuntimeError(f"Failed to load image: {path}")

    configure_tesseract(cfg)
    ocr_result = ocr_with_boxes(image_bgr, cfg)
    redactions = detect_sensitive_regions(image_bgr, ocr_result, patterns, cfg)
    masked = apply_redactions(image_bgr, redactions, cfg)

    base, ext = os.path.splitext(path)
    out_path = base + ".masked" + ext
    cv2.imwrite(out_path, masked)
    return out_path, redactions, ocr_result.text
