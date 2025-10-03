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

	# Simple but effective shadow removal
	if remove_shadow:
		try:
			# Use single kernel for reliable shadow removal
			kernel_size = max(25, int(min(gray.shape[:2]) * 0.05))
			if kernel_size % 2 == 0:
				kernel_size += 1
			kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
			background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
			# Ensure minimum background value
			background = np.maximum(background, 5)
			# Apply illumination correction
			normalized = cv2.divide(gray, background, scale=255)
			normalized = np.clip(normalized, 0, 255)
			# Conservative blending
			gray = cv2.addWeighted(normalized, 0.7, gray, 0.3, 0).astype(np.uint8)
		except:
			pass

	# Moderate CLAHE for better contrast
	if clahe_clip and clahe_clip > 0:
		clip_value = float(clahe_clip)
	else:
		clip_value = 2.0  # Moderate enhancement
	try:
		clahe = cv2.createCLAHE(clipLimit=clip_value, tileGridSize=(8, 8))
		gray = clahe.apply(gray)
	except:
		pass

	# Professional denoising for document quality
	if denoise_strength and denoise_strength > 0:
		try:
			blur = cv2.fastNlMeansDenoising(gray, None, h=int(denoise_strength), templateWindowSize=7, searchWindowSize=21)
		except:
			# Use bilateral filter for better edge preservation
			blur = cv2.bilateralFilter(gray, 5, 50, 50)
	else:
		# Use bilateral filter to preserve text edges
		blur = cv2.bilateralFilter(gray, 5, 50, 50)

	# Deskew on binary-friendly version
	if deskew:
		try:
			# Use OTSU for angle estimation
			_, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
			rot = deskew_image(th)
			work = rot
		except:
			work = blur
	else:
		work = blur

	# Optimized adaptive threshold for crisp text
	try:
		# Use optimized block size for document quality
		block_size = max(11, adaptive_block if adaptive_block % 2 == 1 else adaptive_block + 1)
		binary = cv2.adaptiveThreshold(
			work,
			255,
			cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
			cv2.THRESH_BINARY,
			block_size,
			adaptive_c,
		)
	except:
		# Fallback to OTSU with proper parameters
		_, binary = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

	# Professional morphological cleaning for document quality
	try:
		# Step 1: Remove small noise
		kernel_noise = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
		clean1 = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_noise, iterations=1)
		
		# Step 2: Close small gaps in characters
		kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
		clean = cv2.morphologyEx(clean1, cv2.MORPH_CLOSE, kernel_close, iterations=1)
	except:
		clean = binary
	
	# Professional sharpening for crisp text
	try:
		# Use unsharp masking for professional results
		kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
		sharpened = cv2.filter2D(clean, -1, kernel_sharp)
		sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
		
		# Apply unsharp mask for professional sharpening
		gaussian = cv2.GaussianBlur(sharpened, (0, 0), 1.5)
		unsharp_mask = cv2.addWeighted(sharpened, 1.3, gaussian, -0.3, 0)
		sharpened = np.clip(unsharp_mask, 0, 255).astype(np.uint8)
	except:
		sharpened = clean

	# Return colored output - keep original colors with enhanced clarity
	# Use the original resized image as base and apply processing as enhancement
	enhanced_original = img.copy()
	
	# Convert sharpened to 3-channel for blending
	sharpened_3ch = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
	
	# Blend original colors with enhanced processing (60% original, 40% processed)
	final_output = cv2.addWeighted(enhanced_original, 0.6, sharpened_3ch, 0.4, 0)
	
	# Ensure proper color range
	final_output = np.clip(final_output, 0, 255).astype(np.uint8)
	
	return final_output


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


