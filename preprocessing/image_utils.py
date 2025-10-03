from typing import Tuple

import cv2
import numpy as np
from PIL import Image


def convert_pil_to_cv(img: Image.Image) -> np.ndarray:
	return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def convert_cv_to_pil(img: np.ndarray) -> Image.Image:
	return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def deskew_image(gray: np.ndarray) -> np.ndarray:
	coords = np.column_stack(np.where(gray > 0))
	if coords.size == 0:
		return gray
	angle = cv2.minAreaRect(coords)[-1]
	if angle < -45:
		angle = -(90 + angle)
	else:
		angle = -angle
	(h, w) = gray.shape[:2]
	center = (w // 2, h // 2)
	M = cv2.getRotationMatrix2D(center, angle, 1.0)
	rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
	return rotated


def preprocess_image(
    img_bgr: np.ndarray,
    resize_width: int = 1500,
    adaptive_block: int = 35,
    adaptive_c: int = 5,
    deskew: bool = True,
    remove_shadow: bool = False,
    clahe_clip: float = 0.0,
    denoise_strength: int = 0,
) -> np.ndarray:
	# Resize proportionally
	h, w = img_bgr.shape[:2]
	scale = resize_width / max(1, w)
	img = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

	# Grayscale
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	# Optional shadow removal (illumination correction)
	if remove_shadow:
		# Estimate background illumination using morphological opening
		kernel_size = max(15, int(min(gray.shape[:2]) * 0.03))
		if kernel_size % 2 == 0:
			kernel_size += 1
		kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
		background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
		# Avoid division by zero
		background = np.clip(background, 1, 255)
		gray = cv2.divide(gray, background, scale=255)

	# Optional CLAHE contrast enhancement
	if clahe_clip and clahe_clip > 0:
		clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))
		gray = clahe.apply(gray)

	# Denoise
	if denoise_strength and denoise_strength > 0:
		blur = cv2.fastNlMeansDenoising(gray, None, h=int(denoise_strength), templateWindowSize=7, searchWindowSize=21)
	else:
		blur = cv2.GaussianBlur(gray, (3, 3), 0)

	# Deskew on binary-friendly version
	if deskew:
		# Use OTSU for angle estimation
		_, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		rot = deskew_image(th)
		# Map rotation back to original gray via same transform is heavy; acceptable to reuse rot
		work = rot
	else:
		work = blur

	# Adaptive threshold for robust binarization
	binary = cv2.adaptiveThreshold(
		work,
		255,
		cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
		cv2.THRESH_BINARY,
		adaptive_block if adaptive_block % 2 == 1 else adaptive_block + 1,
		adaptive_c,
	)

	# Morphological open to remove salt-and-pepper
	kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
	clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

	# Return 3-channel BGR for consistent display pipeline
	return cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR)


def detect_and_crop_table_region(img_bgr: np.ndarray) -> np.ndarray:
	gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
	# Invert for table line emphasis
	inv = 255 - gray
	# Detect lines using morphological operations
	kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
	kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
	grad_h = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel_h)
	grad_v = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel_v)
	mask = cv2.addWeighted(grad_h, 0.5, grad_v, 0.5, 0)

	# Threshold and find contours
	_, th = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
	contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	if not contours:
		return img_bgr

	# Choose the largest contour as table region
	largest = max(contours, key=cv2.contourArea)
	x, y, w, h = cv2.boundingRect(largest)
	# Add small padding
	pad = 10
	y1 = max(0, y - pad)
	y2 = min(img_bgr.shape[0], y + h + pad)
	x1 = max(0, x - pad)
	x2 = min(img_bgr.shape[1], x + w + pad)
	return img_bgr[y1:y2, x1:x2]


