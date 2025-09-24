from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ImagePlacement:
    sheet_name: str
    cell: str  # anchor cell like 'B3'
    left: int  # pixel offset from cell left within sheet
    top: int   # pixel offset from cell top within sheet
    width: int
    height: int
    image_id: str  # unique identifier per sheet


@dataclass
class ExtractedImage:
    placement: ImagePlacement
    image_path: str  # temp path to extracted image file


@dataclass
class RedactionBox:
    x: int
    y: int
    w: int
    h: int
    label: str


@dataclass
class OCRResult:
    text: str
    boxes: List[RedactionBox]


@dataclass
class MaskConfig:
    lang: str = "eng"
    mask_color: Tuple[int, int, int] = (0, 0, 0)  # BGR for OpenCV
    mask_padding: int = 4
    tesseract_cmd: Optional[str] = None
