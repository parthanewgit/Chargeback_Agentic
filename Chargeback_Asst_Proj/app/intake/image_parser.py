from __future__ import annotations

from pathlib import Path

from PIL import Image


def extract_image_summary(file_path: str | Path) -> dict[str, object]:
    img = Image.open(file_path)
    return {
        'filename': Path(file_path).name,
        'format': img.format,
        'size': img.size,
        'mode': img.mode,
        'text': 'Image upload accepted; OCR/vision extraction is unavailable for the configured model.',
    }
