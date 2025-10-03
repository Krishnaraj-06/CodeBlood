"""Analyze attendance and detect anomalies"""
from typing import List, Dict
import pandas as pd


class AttendanceAnalyzer:
    def __init__(self, threshold_percentage: float = 75.0):
        self.threshold = threshold_percentage

    def calculate_attendance(self, records: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(records)
        lecture_cols = [col for col in df.columns if col.startswith('lecture_')]
        
        results = []
        for _, row in df.iterrows():
            present = sum(row[col] == 'Present' for col in lecture_cols)
            total = len(lecture_cols)
            percentage = (present / total * 100) if total > 0 else 0
            
            results.append({
                'roll_no': row['roll_no'],
                'name': row['name'],
                'present_count': present,
                'total_lectures': total,
                'attendance_percentage': round(percentage, 2)
            })
        
        return pd.DataFrame(results)

    def identify_defaulters(self, attendance_df: pd.DataFrame) -> pd.DataFrame:
        return attendance_df[
            attendance_df['attendance_percentage'] < self.threshold
        ]

    def detect_duplicate_entries(self, records: List[Dict]) -> List[Dict]:
        df = pd.DataFrame(records)
        duplicates = df[df.duplicated(subset=['roll_no'], keep=False)]
        
        if duplicates.empty:
            return []
        
        return [
            {'roll_no': roll, 'count': len(group)}
            for roll, group in duplicates.groupby('roll_no')
        ]
