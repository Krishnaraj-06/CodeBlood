from typing import List, Optional

import io
from PIL import Image


def _get_poppler_path() -> Optional[str]:
	import os
	return os.environ.get("POPPLER_PATH") or None


def convert_pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
	from pdf2image import convert_from_bytes
	images = convert_from_bytes(pdf_bytes, dpi=dpi, poppler_path=_get_poppler_path())
	# Ensure RGB mode
	return [img.convert("RGB") for img in images]


