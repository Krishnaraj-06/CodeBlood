"""Normalize attendance markings"""
from typing import List, Dict
import re


class AttendanceNormalizer:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.present_markers = self.config.get("present_markers", ["P", "✓", "•"])
        self.absent_markers = self.config.get("absent_markers", ["A", "×", "X"])

    def normalize_marking(self, marking: str) -> str:
        """Convert marking to Present/Absent"""
        marking = str(marking).strip()
        
        for marker in self.present_markers:
            if marker.lower() in marking.lower():
                return "Present"
        
        for marker in self.absent_markers:
            if marker.lower() in marking.lower():
                return "Absent"
        
        return "Unknown"

    def normalize_roll_number(self, roll_no: str) -> str:
        """Standardize roll number format"""
        roll_no = re.sub(r'[^0-9]', '', str(roll_no))
        return roll_no.zfill(8)

    def normalize_name(self, name: str) -> str:
        """Standardize student name"""
        name = str(name).strip().title()
        return ' '.join(name.split())
