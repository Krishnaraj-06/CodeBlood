import os
import base64
import requests
import csv
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _normalize_mark(cell: str) -> str:
    """
    Normalize a single attendance cell to 'P' or 'A' using the requested rules:
    - Absent: x, X, a, ab, /  -> 'A'
    - Present: signature, p, P, empty -> 'P'
    Any other ambiguous value defaults to 'P' (present).
    """
    s = (cell or "").strip()
    if s == "":
        return "P"
    s_lower = s.lower()

    absent_tokens = {"x", "a", "ab", "/"}
    present_tokens = {"p"}  # uppercase handled below

    if s_lower in absent_tokens:
        return "A"
    if s_lower in present_tokens or s == "P":
        return "P"

    # Heuristics: common signature-like or check-like marks
    if any(tok in s_lower for tok in ["sign", "sig", "scribble", "tick", "check", "✓", "✔"]):
        return "P"

    # Default: present
    return "P"


def _fix_columns(cols: List[str]) -> List[str]:
    """
    Ensure exactly 13 columns: Roll, StudentID, Name, Att1..Att10.
    Merge split name fields if needed; normalize 10 attendance marks.
    """
    cols = [c.strip().strip('"') for c in cols]

    if len(cols) < 13:
        cols = cols + [""] * (13 - len(cols))
    elif len(cols) > 13:
        # Assume last 10 fields are attendance; merge extras into Name.
        fixed = []
        fixed.append(cols[0])
        fixed.append(cols[1])
        name_span = len(cols) - 12
        fixed.append(" ".join(cols[2:2 + name_span]))
        fixed.extend(cols[-10:])
        cols = fixed[:13]

    # Normalize IDs
    cols[0] = cols[0].replace(" ", "")
    cols[1] = cols[1].replace(" ", "")

    # Normalize attendance cells
    for i in range(3, 13):
        cols[i] = _normalize_mark(cols[i])

    return cols


def gemini_ocr_extract(
    image_path: str,
    api_key: Optional[str] = None,
    csv_path: str = "attendance.csv",
    model: str = "gemini-2.5-flash"  # Fast, multimodal
) -> str:
    """
    Extract text from an attendance sheet image using Google Gemini (multimodal)
    and export the result as a CSV file with normalized attendance.
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ No API key found. Set GEMINI_API_KEY env var or pass api_key arg.")
        return ""

    try:
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        system_prompt = (
            "Extract the attendance table as TSV with columns exactly: "
            "Roll\tStudentID\tName\tAtt1\tAtt2\tAtt3\tAtt4\tAtt5\tAtt6\tAtt7\tAtt8\tAtt9\tAtt10. "
            "Return only raw TSV content without code fences or explanations ."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": system_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            print(f"❌ Gemini API Error: {resp.status_code}")
            print(resp.text)
            return ""

        data = resp.json()
        text_output = ""
        for cand in data.get("candidates", []):
            content = cand.get("content", {})
            for part in content.get("parts", []):
                if "text" in part:
                    text_output += part["text"]

        if not text_output.strip():
            print("⚠️ No OCR result returned.")
            return ""

        # Parse TSV and normalize
        rows = []
        for line in text_output.splitlines():
            line = line.strip().strip('"')
            if not line:
                continue
            cols = line.split("\t")
            fixed = _fix_columns(cols)
            rows.append(fixed)

        # Write header and rows
        header = ["Roll", "StudentID", "Name"] + [f"Att{i}" for i in range(1, 11)]
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"✅ Attendance exported to {csv_path}")
        return csv_path

    except Exception as e:
        print(f"⚠️ Error during OCR: {e}")
        return ""


if __name__ == "__main__":
    csv_file = gemini_ocr_extract(
        r"file path",
        api_key="api key",
        csv_path="attendance.csv",
        model="gemini-2.5-flash"  # or gemini-1.5-flash-latest
    )
