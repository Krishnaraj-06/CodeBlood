import os
import io
import uuid
import zipfile
from datetime import datetime
from typing import List
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import pandas as pd

# Load environment variables
load_dotenv()

from preprocessing.pdf_utils import convert_pdf_to_images
from preprocessing.image_utils import (
	convert_pil_to_cv,
	convert_cv_to_pil,
	preprocess_image,
	detect_and_crop_table_region,
)
from config import PREPROCESSING, APP_NAME
from gemini import gemini_ocr_extract


# APP_NAME imported from config
RUNS_DIR = os.path.join("static", "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip', 'jpg', 'jpeg', 'png'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'audtiflow_secret_key_2024'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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
					up.stream.seek(0)
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


def allowed_file(filename):
	"""Check if file has allowed extension"""
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_image_from_zip(zip_path, extract_to):
	"""Extract the first image from a zip file"""
	with zipfile.ZipFile(zip_path, 'r') as zip_ref:
		image_files = [f for f in zip_ref.namelist() 
					  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
		if not image_files:
			return None
		zip_ref.extract(image_files[0], extract_to)
		return os.path.join(extract_to, image_files[0])


@app.route('/ocr-dashboard', methods=['GET'])
def ocr_dashboard():
	"""Render the OCR dashboard page"""
	return render_template('ocr_dashboard.html', app_name=APP_NAME)


@app.route('/upload', methods=['POST'])
def upload_file():
	"""Handle file upload and OCR processing"""
	if 'file' not in request.files:
		flash('No file part', 'error')
		return redirect(url_for('ocr_dashboard'))
	
	file = request.files['file']
	
	if file.filename == '':
		flash('No selected file', 'error')
		return redirect(url_for('ocr_dashboard'))
	
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
		file.save(filepath)
		
		image_path = None
		if filename.lower().endswith('.zip'):
			image_path = extract_image_from_zip(filepath, app.config['UPLOAD_FOLDER'])
			if not image_path:
				flash('No valid image found in the zip file', 'error')
				return redirect(url_for('ocr_dashboard'))
		else:
			image_path = filepath
		
		try:
			api_key = os.getenv('GEMINI_API_KEY')
			output_csv = gemini_ocr_extract(
				image_path,
				api_key=api_key,
				csv_path=os.path.join(app.config['UPLOAD_FOLDER'], 'attendance.csv')
			)
			
			if not output_csv:
				flash('OCR processing failed. Please check your API key and try again.', 'error')
				return redirect(url_for('ocr_dashboard'))
			
			df = pd.read_csv(output_csv)
			table_html = df.to_html(classes='table table-striped table-bordered', index=False)
			
			flash('File successfully processed!', 'success')
			return render_template('ocr_dashboard.html', 
								 app_name=APP_NAME,
								 table=table_html,
								 total_students=len(df))
			
		except Exception as e:
			flash(f'Error processing file: {str(e)}', 'error')
			return redirect(url_for('ocr_dashboard'))
	
	else:
		flash(f'Invalid file type. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'error')
		return redirect(url_for('ocr_dashboard'))


@app.route('/ocr-batch/<run_id>', methods=['GET'])
def ocr_batch(run_id: str):
	"""Run OCR on all cleaned images for a given run and render multi-result dashboard."""
	run_dir = os.path.join(RUNS_DIR, run_id)
	cleaned_dir = os.path.join(run_dir, 'cleaned')
	
	print(f"🔍 OCR batch started for run_id: {run_id}")
	print(f"📁 Cleaned dir: {cleaned_dir}")
	print(f"📁 Dir exists: {os.path.isdir(cleaned_dir)}")
	
	if not os.path.isdir(cleaned_dir):
		flash('Invalid run. Please preprocess images first.', 'error')
		return redirect(url_for('dashboard'))

	csv_dir = os.path.join(run_dir, 'csv')
	os.makedirs(csv_dir, exist_ok=True)

	api_key = os.getenv('GEMINI_API_KEY')
	if not api_key:
		flash('GEMINI_API_KEY not found in environment. Please check your .env file.', 'error')
		return redirect(url_for('dashboard'))
	
	print(f"🔑 API key found: {api_key[:10]}...")
	results = []
	files_list = sorted(os.listdir(cleaned_dir))
	print(f"📝 Found {len(files_list)} files in cleaned directory")
	
	import shutil
	for fname in files_list:
		if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
			continue
		image_path = os.path.join(cleaned_dir, fname)
		csv_name = os.path.splitext(fname)[0] + '.csv'
		csv_path = os.path.join(csv_dir, csv_name)

		print(f"🔄 Processing {fname}...")
		try:
			out_csv = gemini_ocr_extract(image_path, api_key=api_key, csv_path=csv_path)
			print(f"✅ OCR completed for {fname}")
			if not out_csv:
				continue
			# Copy CSV to uploads folder as attendance.csv (overwrite)
			uploads_csv_path = os.path.join(UPLOAD_FOLDER, 'attendance.csv')
			shutil.copyfile(out_csv, uploads_csv_path)
			df = pd.read_csv(out_csv)
			
			# Add Present (P) and Absent (A) counts and Defaulter column
			attendance_cols = df.columns.difference(['Roll', 'StudentID', 'Name'])
			df['Present Count'] = df[attendance_cols].apply(lambda row: (row == 'P').sum(), axis=1)
			df['Absent Count'] = df[attendance_cols].apply(lambda row: (row == 'A').sum(), axis=1)
			# Mark defaulter if absent count > 3 (threshold can be adjusted)
			df['Defaulter'] = df['Absent Count'].apply(lambda x: 'Yes' if x > 3 else 'No')
			
			# Calculate attendance percentage
			total_classes = len(attendance_cols)
			df['Attendance %'] = (df['Present Count'] / total_classes) * 100

			# Save as Excel with conditional formatting for row colors
			import openpyxl
			from openpyxl.styles import PatternFill
			from openpyxl.utils.dataframe import dataframe_to_rows

			excel_path = os.path.splitext(out_csv)[0] + '.xlsx'
			wb = openpyxl.Workbook()
			ws = wb.active
			ws.title = "Attendance"

			# Write dataframe to worksheet
			for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
				for c_idx, value in enumerate(row, 1):
					ws.cell(row=r_idx, column=c_idx, value=value)

			# Define fills
			yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
			orange_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
			red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")

			# Apply conditional formatting to rows based on Attendance %
			att_col_idx = df.columns.get_loc('Attendance %') + 1  # 1-based index
			for row in range(2, ws.max_row + 1):
				att_value = ws.cell(row=row, column=att_col_idx).value
				if att_value is None:
					continue
				if att_value < 30:
					fill = red_fill
				elif att_value < 50:
					fill = orange_fill
				elif 50 <= att_value <= 70:
					fill = yellow_fill
				else:
					fill = None
				if fill:
					for col in range(1, ws.max_column + 1):
						ws.cell(row=row, column=col).fill = fill

			wb.save(excel_path)

			# Save updated CSV and Excel to uploads folder
			import shutil
			uploads_csv_path = os.path.join(UPLOAD_FOLDER, 'attendance.csv')
			uploads_excel_path = os.path.join(UPLOAD_FOLDER, 'attendance.xlsx')
			shutil.copyfile(out_csv, uploads_csv_path)
			shutil.copyfile(excel_path, uploads_excel_path)

			table_html = df.to_html(classes='table table-striped table-bordered', index=False)
			results.append({
				'image_url': '/' + os.path.join(cleaned_dir, fname).replace('\\', '/'),
				'csv_name': csv_name,
				'csv_url': url_for('download_csv_file', run_id=run_id, filename=csv_name),
				'excel_url': url_for('download_excel_file', run_id=run_id, filename=os.path.basename(excel_path)),
				'total_students': len(df),
				'title': fname,
				'table': table_html,
			})
		except Exception as e:
			print(f"❌ OCR error for {fname}: {e}")
			import traceback
			traceback.print_exc()
			continue

	print(f"🎉 OCR batch completed. {len(results)} results generated")
	
	if not results:
		flash('OCR produced no results. Please verify API key and inputs.', 'error')
		return redirect(url_for('dashboard'))

	flash(f'Successfully extracted data from {len(results)} images!', 'success')

	# Load input and cleaned images for dashboard display
	input_dir = os.path.join(run_dir, 'input')
	cleaned_dir = os.path.join(run_dir, 'cleaned')
	input_images = ['/' + os.path.join(input_dir, f).replace('\\', '/') for f in sorted(os.listdir(input_dir)) if f.lower().endswith(('.png', '.jpg', '.jpeg'))] if os.path.isdir(input_dir) else []
	cleaned_images = ['/' + os.path.join(cleaned_dir, f).replace('\\', '/') for f in sorted(os.listdir(cleaned_dir)) if f.lower().endswith(('.png', '.jpg', '.jpeg'))] if os.path.isdir(cleaned_dir) else []

	# Set metrics
	metrics = dict(
		uploaded=len(input_images),
		processed=len(cleaned_images),
		last_run=datetime.now().strftime("%d-%b %Y %I:%M %p"),
	)

	# Default settings (since not saved)
	settings = dict(
		resize_width=1500,
		adaptive_block=35,
		adaptive_c=5,
		deskew=True,
		crop_table=False,
		remove_shadow=True,
		clahe_clip=0,
		denoise_strength=0
	)

	return render_template(
		'dashboard.html',
		app_name=APP_NAME,
		results=results,
		run_id=run_id,
		zip_url=url_for('download_csv_zip', run_id=run_id),
		metrics=metrics,
		input_images=input_images,
		cleaned_images=cleaned_images,
		settings=settings
	)


@app.route('/download/csv/<run_id>/<path:filename>', methods=['GET'])
def download_csv_file(run_id: str, filename: str):
	"""Download a single CSV for a given run."""
	csv_dir = os.path.join(RUNS_DIR, run_id, 'csv')
	if not os.path.isfile(os.path.join(csv_dir, filename)):
		return redirect(url_for('ocr_batch', run_id=run_id))
	return send_from_directory(csv_dir, filename, as_attachment=True)

@app.route('/download/excel/<run_id>/<path:filename>', methods=['GET'])
def download_excel_file(run_id: str, filename: str):
	"""Download a single Excel file for a given run."""
	csv_dir = os.path.join(RUNS_DIR, run_id, 'csv')
	if not os.path.isfile(os.path.join(csv_dir, filename)):
		return redirect(url_for('ocr_batch', run_id=run_id))
	return send_from_directory(csv_dir, filename, as_attachment=True)

@app.route('/download/csv-zip/<run_id>', methods=['GET'])
def download_csv_zip(run_id: str):
	"""Download a ZIP of all CSVs for a given run."""
	csv_dir = os.path.join(RUNS_DIR, run_id, 'csv')
	if not os.path.isdir(csv_dir):
		return redirect(url_for('ocr_batch', run_id=run_id))
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
		for fname in sorted(os.listdir(csv_dir)):
			if not fname.lower().endswith('.csv'):
				continue
			fpath = os.path.join(csv_dir, fname)
			zipf.write(fpath, arcname=fname)
	buffer.seek(0)
	return send_file(buffer, as_attachment=True, download_name=f'{run_id}_csvs.zip', mimetype='application/zip')


from flask import jsonify

@app.route('/attendance-data/<run_id>', methods=['GET'])
def attendance_data(run_id: str):
	csv_dir = os.path.join(RUNS_DIR, run_id, 'csv')
	if not os.path.isdir(csv_dir):
		return jsonify({'error': 'Invalid run ID or no data found'}), 404

	# Find the first CSV file in the csv_dir
	csv_files = [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]
	if not csv_files:
		return jsonify({'error': 'No CSV files found for this run'}), 404

	csv_path = os.path.join(csv_dir, csv_files[0])
	try:
		df = pd.read_csv(csv_path)
		attendance_cols = df.columns.difference(['Roll', 'StudentID', 'Name', 'Present Count', 'Absent Count', 'Defaulter', 'Attendance %'])

		tp=df[attendance_cols].apply(lambda x: (x == 'P').sum()).sum()
		ta=df[attendance_cols].apply(lambda x: (x == 'A').sum()).sum()
		total=240
		total_present = (tp/total)*100
		total_absent = (ta/total)*100
		
		return jsonify({'presentCount': int(total_present), 'absentCount': int(total_absent)})
	except Exception as e:
		return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 8501))
	app.run(host="0.0.0.0", port=port, debug=True)
