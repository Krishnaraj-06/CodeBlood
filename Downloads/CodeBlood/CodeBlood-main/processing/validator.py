"""Validate attendance data"""
from typing import List, Dict, Tuple
import pandas as pd
from pathlib import Path


class AttendanceValidator:
    def __init__(self, master_list_path: Path):
        self.master_df = pd.read_excel(master_list_path)
        self.valid_roll_numbers = set(self.master_df['Roll No'].astype(str))
        self.valid_students = {
            str(row['Roll No']): row['Name']
            for _, row in self.master_df.iterrows()
        }

    def validate_roll_number(self, roll_no: str) -> Tuple[bool, str]:
        if roll_no in self.valid_roll_numbers:
            return True, "Valid"
        return False, "Roll number not found"

    def validate_batch(self, records: List[Dict]) -> Dict:
        valid_records = []
        invalid_records = []
        warnings = []

        for record in records:
            roll_no = record.get('roll_no', '')
            is_valid, msg = self.validate_roll_number(roll_no)
            
            if not is_valid:
                invalid_records.append({**record, 'error': msg})
            else:
                valid_records.append(record)
        
        return {
            'valid': valid_records,
            'invalid': invalid_records,
            'warnings': warnings
        }
