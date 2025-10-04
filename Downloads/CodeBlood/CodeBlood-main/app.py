import os
import io
import zipfile
from typing import List, Optional, Tuple
from pathlib import Path

import streamlit as st
import pandas as pd
from PIL import Image
from datetime import datetime

from preprocessing.pdf_utils import convert_pdf_to_images
from preprocessing.image_utils import (
    convert_pil_to_cv,
    convert_cv_to_pil,
    preprocess_image,
    detect_and_crop_table_region,
)
from processing.ocr_processor import OCRProcessor
from config import PREPROCESSING, APP_NAME, DATA_DIR


def ensure_page_config() -> None:
	st.set_page_config(
		page_title=f"{APP_NAME} - Attendance Processing Dashboard",
		page_icon="📄",
		layout="wide",
	)


def sidebar_settings() -> dict:
	st.sidebar.header("Settings")
	default_poppler = os.environ.get("POPPLER_PATH", "")
	poppler_path = st.sidebar.text_input(
		"Poppler bin path (Windows only, needed for PDF)",
		value=default_poppler,
		help="Example: C\\\Program Files\\\poppler-24.08.0\\\Library\\\bin",
	)
	if poppler_path:
		os.environ["POPPLER_PATH"] = poppler_path

	resize_width = st.sidebar.number_input(
		"Resize width (px)", min_value=600, max_value=3000, value=PREPROCESSING["resize_width"], step=50
	)
	threshold_block = st.sidebar.slider(
		"Adaptive threshold block size",
		min_value=11,
		max_value=101,
		value=PREPROCESSING["adaptive_block"],
		step=2,
	)
	threshold_c = st.sidebar.slider(
		"Adaptive threshold C",
		min_value=-20,
		max_value=20,
		value=PREPROCESSING["adaptive_c"],
		step=1,
	)
	deskew_enabled = st.sidebar.checkbox("Deskew image", value=PREPROCESSING["deskew"])
	crop_table = st.sidebar.checkbox("Detect & crop table region", value=PREPROCESSING["crop_table"])

	return dict(
		poppler_path=poppler_path,
		resize_width=resize_width,
		threshold_block=threshold_block,
		threshold_c=threshold_c,
		deskew_enabled=deskew_enabled,
		crop_table=crop_table,
	)


def save_images_to_zip(images: List[Image.Image]) -> bytes:
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
		for idx, img in enumerate(images, start=1):
			img_bytes = io.BytesIO()
			img.save(img_bytes, format="PNG")
			zipf.writestr(f"cleaned_page_{idx:02d}.png", img_bytes.getvalue())
	buffer.seek(0)
	return buffer.read()


def main() -> None:
	ensure_page_config()
	settings = sidebar_settings()

	st.title("🎛️ Faculty Dashboard")
	st.caption("Module 1: Upload & Preprocessing — बिना लॉगिन, सीधा उपयोग।")

	# Tabs: Dashboard, Upload & Preprocess, Help
	tab_dashboard, tab_upload, tab_help = st.tabs(["Dashboard", "Upload & Preprocess", "Help"])

	# Initialize session state containers
	if "input_pages" not in st.session_state:
		st.session_state.input_pages = []  # List[PIL.Image]
	if "cleaned_pages" not in st.session_state:
		st.session_state.cleaned_pages = []  # List[PIL.Image]
	if "last_run" not in st.session_state:
		st.session_state.last_run = None

	with tab_upload:
		st.subheader("Upload files")
		uploaded_files = st.file_uploader(
			"Attendance sheets (JPG/PNG/PDF)",
			accept_multiple_files=True,
			type=["jpg", "jpeg", "png", "pdf"],
		)

		if uploaded_files:
			all_input_images: List[Image.Image] = []
			with st.spinner("Reading files..."):
					if up.type == "application/pdf" or up.name.lower().endswith(".pdf"):
						images = convert_pdf_to_images(up.read())
						all_input_images.extend(images)
					else:
						img = Image.open(up).convert("RGB")
						all_input_images.append(img)

	def process_attendance_tab(ocr_processor):
		st.header("Process Attendance")
		
		# File uploader
		uploaded_file = st.file_uploader(
			"Upload a scanned attendance sheet (PDF or image)",
			type=["png", "jpg", "jpeg", "pdf"],
			key="attendance_upload"
		)

		if not uploaded_file:
			st.info("Please upload an attendance sheet to begin processing.")
			return

		# Display the uploaded image
		if uploaded_file.type.startswith('image'):
			st.image(uploaded_file, caption="Uploaded Attendance Sheet")
		
		# Process button
		if st.button("Process Attendance", type="primary"):
			with st.spinner("Processing attendance sheet..."):
				# Save the uploaded file temporarily
				temp_dir = Path("temp")
				temp_dir.mkdir(exist_ok=True)
				temp_path = temp_dir / uploaded_file.name
				
				with open(temp_path, "wb") as f:
					f.write(uploaded_file.getbuffer())
				
				# Process the image
				success, message, df = ocr_processor.process_image(temp_path)
				
				if success and df is not None:
					# Calculate attendance statistics
					df = ocr_processor.calculate_attendance(df)
					
					# Display results
					st.success("Successfully processed attendance sheet!")
					
					# Show summary
					total_students = len(df)
					defaulters = len(df[df['Status'] == 'Defaulter'])
					
					col1, col2 = st.columns(2)
					with col1:
						st.metric("Total Students", total_students)
					with col2:
						st.metric("Defaulters", f"{defaulters} ({defaulters/total_students*100:.1f}%)")
					
					# Show data table
					st.dataframe(df)
					
					# Download button
					csv = df.to_csv(index=False)
					st.download_button(
						label="Download Attendance CSV",
						data=csv,
						file_name="attendance_report.csv",
						mime="text/csv"
					)
				else:
					st.error(f"Error processing attendance: {message}")
				
				# Clean up
				if temp_path.exists():
					temp_path.unlink()

	def main():
		ensure_page_config()
		st.title(f"{APP_NAME} - Attendance Management System")
					st.image(img, caption=f"Cleaned {i+1}", use_column_width=True)

	with tab_dashboard:
		st.subheader("Overview")
		c1, c2, c3 = st.columns(3)
		c1.metric("Uploaded Pages", len(st.session_state.input_pages))
		c2.metric("Processed Pages", len(st.session_state.cleaned_pages))
		last = st.session_state.last_run.strftime("%d-%b %Y %I:%M %p") if st.session_state.last_run else "—"
		c3.metric("Last Run", last)

		st.markdown("---")
		if len(st.session_state.cleaned_pages) == 0:
			st.info("अभी कोई आउटपुट नहीं है। पहले 'Upload & Preprocess' टैब में प्रोसेस चलाएँ।")
		else:
			zip_bytes = save_images_to_zip(st.session_state.cleaned_pages)
			st.download_button(
				label="Download cleaned images (ZIP)",
				data=zip_bytes,
				file_name="cleaned_attendance_pages.zip",
				mime="application/zip",
			)
			st.write("Cleaned thumbnails")
			cols3 = st.columns(4)
			for i, img in enumerate(st.session_state.cleaned_pages):
				with cols3[i % 4]:
					st.image(img, caption=f"Page {i+1}", use_column_width=True)

	with tab_help:
		st.subheader("Help / Notes")
		st.markdown(
			"- PDF कन्वर्ज़न के लिए Windows पर Poppler आवश्यक है।\n"
			"- साइडबार में थ्रेशोल्ड और डेस्क्यू सेटिंग बदल सकते हैं।\n"
			"- आउटपुट ZIP डाउनलोड करने के लिए Dashboard टैब खोलें।"
		)


if __name__ == "__main__":
	main()


