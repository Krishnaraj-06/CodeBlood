AudtiFlow — Attendance Preprocessing Dashboard (Module 1)

This app lets faculty upload JPG/PNG/PDF attendance sheets and runs OpenCV preprocessing to clean them for OCR.

Quick start (Streamlit UI)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows PDF (Poppler)

To convert PDF to images, install Poppler for Windows and set the environment variable `POPPLER_PATH` to its bin directory, or paste the path in the app sidebar.

Example path:
- C:\\Program Files\\poppler-24.08.0\\Library\\bin

Features

- Upload multiple JPG/PNG/PDF files
- PDF to images via pdf2image
- OpenCV preprocessing: grayscale, adaptive threshold, deskew, resize
- Optional table region detection and crop
- Preview input vs cleaned pages
- Download cleaned images as ZIP

Notes

- This is Module 1 (Input & Preprocessing). Subsequent modules will handle OCR, normalization, validation, and analytics.

Flask HTML Dashboard (AudtiFlow)

```bash
pip install -r requirements.txt
python server.py
# open http://localhost:8501
```

The Flask app serves a Tailwind-based dashboard with file upload, preprocessing, previews, KPI cards, and ZIP download.
