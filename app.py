import os
import io
import zipfile
from typing import List, Optional, Tuple

import streamlit as st
from PIL import Image
from datetime import datetime

from preprocessing.pdf_utils import convert_pdf_to_images
from preprocessing.image_utils import (
	convert_pil_to_cv,
	convert_cv_to_pil,
	preprocess_image,
	detect_and_crop_table_region,
)
from config import PREPROCESSING, APP_NAME


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
				for up in uploaded_files:
					if up.type == "application/pdf" or up.name.lower().endswith(".pdf"):
						images = convert_pdf_to_images(up.read())
						all_input_images.extend(images)
					else:
						img = Image.open(up).convert("RGB")
						all_input_images.append(img)
			st.session_state.input_pages = all_input_images

		if len(st.session_state.input_pages) == 0:
			st.info("कृपया JPG/PNG/PDF फाइलें अपलोड करें।")
		else:
			st.write("Preview: Input Pages")
			cols = st.columns(3)
			for i, img in enumerate(st.session_state.input_pages):
				with cols[i % 3]:
					st.image(img, caption=f"Input {i+1}", use_column_width=True)

		st.markdown("----")
		st.subheader("Preprocess")
		if st.button("Run preprocessing", type="primary"):
			cleaned_images: List[Image.Image] = []
			with st.spinner("Processing images with OpenCV..."):
				for img in st.session_state.input_pages:
					cv_img = convert_pil_to_cv(img)
					cv_processed = preprocess_image(
						cv_img,
						resize_width=settings["resize_width"],
						adaptive_block=settings["threshold_block"],
						adaptive_c=settings["threshold_c"],
						deskew=settings["deskew_enabled"],
					)
					if settings["crop_table"]:
						cv_processed = detect_and_crop_table_region(cv_processed)
					cleaned_images.append(convert_cv_to_pil(cv_processed))

			st.session_state.cleaned_pages = cleaned_images
			st.session_state.last_run = datetime.now()
			st.success(f"Processed {len(cleaned_images)} page(s). Output available in Dashboard tab.")

		if len(st.session_state.cleaned_pages) > 0:
			st.write("Preview: Cleaned Output")
			cols2 = st.columns(3)
			for i, img in enumerate(st.session_state.cleaned_pages):
				with cols2[i % 3]:
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


