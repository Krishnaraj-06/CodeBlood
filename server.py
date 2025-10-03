import os
import io
import uuid
import zipfile
from datetime import datetime
from typing import List

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify
from PIL import Image

from preprocessing.pdf_utils import convert_pdf_to_images
from preprocessing.image_utils import (
	convert_pil_to_cv,
	convert_cv_to_pil,
	preprocess_image,
	detect_and_crop_table_region,
)
from config import PREPROCESSING, APP_NAME


# APP_NAME imported from config
RUNS_DIR = os.path.join("static", "runs")
os.makedirs(RUNS_DIR, exist_ok=True)


app = Flask(__name__)
app.secret_key = 'audtiflow_secret_key_2024'


def _save_images(images: List[Image.Image], base_dir: str, prefix: str) -> List[str]:
	os.makedirs(base_dir, exist_ok=True)
	paths = []
	for idx, img in enumerate(images, start=1):
		fname = f"{prefix}_{idx:02d}.png"
		fpath = os.path.join(base_dir, fname)
		img.save(fpath)
		paths.append(fpath.replace("\\", "/"))
	return paths


@app.route("/", methods=["GET"]) 
def index():
	return render_template("landing.html", app_name=APP_NAME)

@app.route("/dashboard", methods=["GET"]) 
def dashboard():
	return render_template(
		"dashboard.html",
		app_name=APP_NAME,
		metrics=dict(uploaded=0, processed=0, last_run="—"),
		input_images=[],
		cleaned_images=[],
		run_id=None,
		settings=dict(
			resize_width=PREPROCESSING["resize_width"],
			adaptive_block=PREPROCESSING["adaptive_block"],
			adaptive_c=PREPROCESSING["adaptive_c"],
			deskew=PREPROCESSING["deskew"],
			crop_table=PREPROCESSING["crop_table"],
			remove_shadow=PREPROCESSING["remove_shadow"],
			clahe_clip=PREPROCESSING["clahe_clip"],
			denoise_strength=PREPROCESSING["denoise_strength"]
		),
	)


@app.route("/process", methods=["POST"]) 
def process():
	try:
		files = request.files.getlist("files")
		resize_width = int(request.form.get("resize_width", 1500))
		adaptive_block = int(request.form.get("adaptive_block", 35))
		adaptive_c = int(request.form.get("adaptive_c", 5))
		deskew = request.form.get("deskew") == "on"
		crop_table = request.form.get("crop_table") == "on"
		remove_shadow = request.form.get("remove_shadow", "on") == "on"
		clahe_clip = float(request.form.get("clahe_clip", 0))
		denoise_strength = int(request.form.get("denoise_strength", 0))

		if not files or all(f.filename == '' for f in files):
			flash("Please upload at least one file.", "error")
			return redirect(url_for("dashboard"))

		# Read and expand inputs
		input_pages: List[Image.Image] = []
		for up in files:
			if up.filename == '':
				continue
			filename = (up.filename or "").lower()
			try:
				if filename.endswith(".pdf"):
					input_pages.extend(convert_pdf_to_images(up.read()))
				else:
					up.stream.seek(0)  # Reset stream position
					img = Image.open(up.stream).convert("RGB")
					input_pages.append(img)
			except Exception as e:
				flash(f"Error reading file {up.filename}: {str(e)}", "error")
				continue

		if not input_pages:
			flash("No valid files found.", "error")
			return redirect(url_for("dashboard"))

		# Process
		cleaned_pages: List[Image.Image] = []
		for img in input_pages:
			try:
				cv_img = convert_pil_to_cv(img)
				cv_processed = preprocess_image(
					cv_img,
					resize_width=resize_width,
					adaptive_block=adaptive_block,
					adaptive_c=adaptive_c,
					deskew=deskew,
					remove_shadow=remove_shadow,
					clahe_clip=clahe_clip,
					denoise_strength=denoise_strength,
				)
				# Disable cropping to preserve full image
				# if crop_table:
				#	cv_processed = detect_and_crop_table_region(cv_processed)
				cleaned_pages.append(convert_cv_to_pil(cv_processed))
			except Exception as e:
				flash(f"Image processing error: {str(e)}", "error")
				continue

		if not cleaned_pages:
			flash("No images were successfully processed.", "error")
			return redirect(url_for("dashboard"))

		# Persist run for previews and downloads
		run_id = uuid.uuid4().hex[:8]
		run_dir = os.path.join(RUNS_DIR, run_id)
		input_paths = _save_images(input_pages, os.path.join(run_dir, "input"), "input")
		clean_paths = _save_images(cleaned_pages, os.path.join(run_dir, "cleaned"), "cleaned")

		metrics = dict(
			uploaded=len(input_pages),
			processed=len(cleaned_pages),
			last_run=datetime.now().strftime("%d-%b %Y %I:%M %p"),
		)

		flash(f"Successfully processed {len(cleaned_pages)} pages.", "success")
		return render_template(
			"dashboard.html",
			app_name=APP_NAME,
			metrics=metrics,
			input_images=["/" + p for p in input_paths],
			cleaned_images=["/" + p for p in clean_paths],
			run_id=run_id,
			settings=dict(
				resize_width=resize_width,
				adaptive_block=adaptive_block,
				adaptive_c=adaptive_c,
				deskew=deskew,
				crop_table=crop_table,
				remove_shadow=remove_shadow,
				clahe_clip=clahe_clip,
				denoise_strength=denoise_strength,
			),
		)
	except Exception as e:
		flash(f"Server error: {str(e)}", "error")
		return redirect(url_for("dashboard"))


@app.route("/download/<run_id>.zip", methods=["GET"]) 
def download_zip(run_id: str):
	run_dir = os.path.join(RUNS_DIR, run_id, "cleaned")
	if not os.path.isdir(run_dir):
		return redirect(url_for("index"))
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
		for fname in sorted(os.listdir(run_dir)):
			fpath = os.path.join(run_dir, fname)
			zipf.write(fpath, arcname=fname)
	buffer.seek(0)
	return send_file(buffer, as_attachment=True, download_name="cleaned_attendance_pages.zip", mimetype="application/zip")


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 8501))
	app.run(host="0.0.0.0", port=port, debug=True)