"""OCR processing for attendance sheets using Gemini API"""
import os
from typing import Optional, List, Dict, Tuple
import pandas as pd
from pathlib import Path
import tempfile
import streamlit as st

from ..gemini import gemini_ocr_extract
from .normalizer import AttendanceNormalizer
from .validator import AttendanceValidator


class OCRProcessor:
    def __init__(self, master_list_path: Path, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.normalizer = AttendanceNormalizer()
        self.validator = AttendanceValidator(master_list_path)
        self.temp_dir = Path(tempfile.mkdtemp())

    def process_image(self, image_path: Path) -> Tuple[bool, str, Optional[pd.DataFrame]]:
        """Process an image file and return the extracted attendance data"""
        try:
            # Process image with Gemini OCR
            csv_path = self.temp_dir / "temp_attendance.csv"
            result_path = gemini_ocr_extract(
                str(image_path),
                api_key=self.api_key,
                csv_path=str(csv_path),
                model="gemini-2.5-flash"
            )

            if not result_path or not os.path.exists(result_path):
                return False, "Failed to process image with Gemini OCR", None

            # Load and validate the extracted data
            df = pd.read_csv(result_path)
            if df.empty:
                return False, "No data extracted from the image", None

            # Normalize and validate the data
            df = self._normalize_data(df)
            validation_results = self.validator.validate_batch(df.to_dict('records'))
            
            # Add validation status to the dataframe
            df['is_valid'] = df['Roll'].isin(validation_results['valid_rolls'])
            
            return True, "Successfully processed image", df

        except Exception as e:
            return False, f"Error processing image: {str(e)}", None

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize the extracted data"""
        # Normalize roll numbers
        if 'Roll' in df.columns:
            df['Roll'] = df['Roll'].astype(str).apply(self.normalizer.normalize_roll_number)
        
        # Normalize attendance marks
        attendance_cols = [col for col in df.columns if col.startswith('Att')]
        for col in attendance_cols:
            df[col] = df[col].apply(self.normalizer.normalize_marking)
            
        return df

    def calculate_attendance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate attendance statistics"""
        if df.empty:
            return pd.DataFrame()
            
        attendance_cols = [col for col in df.columns if col.startswith('Att')]
        if not attendance_cols:
            return df
            
        # Count present/absent
        df['Present'] = df[attendance_cols].apply(
            lambda row: sum(1 for x in row if x == 'Present'), axis=1)
        df['Absent'] = df[attendance_cols].apply(
            lambda row: sum(1 for x in row if x == 'Absent'), axis=1)
        df['Total'] = len(attendance_cols)
        df['Percentage'] = (df['Present'] / df['Total']) * 100
        df['Status'] = df['Percentage'].apply(
            lambda x: 'Defaulter' if x < 75 else 'Satisfactory')
            
        return df
