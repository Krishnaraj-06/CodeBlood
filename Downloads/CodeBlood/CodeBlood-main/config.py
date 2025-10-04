"""Configuration file for AudtiFlow"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"
RUNS_DIR = STATIC_DIR / "runs"

# Create directories
for directory in [DATA_DIR, OUTPUT_DIR, RUNS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Application settings
APP_NAME = "AudtiFlow"
APP_VERSION = "1.0.0"
DEPARTMENT = "Computer Engineering"
ACADEMIC_YEAR = "2025-2026"

# Preprocessing settings
PREPROCESSING = {
    "resize_width": 2000,
    "adaptive_block": 51,
    "adaptive_c": 10,
    "clahe_clip": 2.0,
    "denoise_strength": 5,
    "deskew": True,
    "crop_table": False,  # Keep full image
    "remove_shadow": True,
}

# Attendance settings
ATTENDANCE = {
    "threshold_percentage": 75.0,
    "present_markers": ["P", "p", "✓", "√", "•", "·", "present"],
    "absent_markers": ["A", "a", "×", "X", "absent"],
}

# Anomaly detection
ANOMALY = {
    "enable_duplicate_detection": True,
    "enable_proxy_detection": True,
    "signature_similarity_threshold": 0.85,
}
