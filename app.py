"""
Web-Based CSV Splitter (Using shutil for Fast Zipping!)

This version uses Python's built-in `shutil` helper module. 
Instead of adding files to a ZIP archive one by one, `shutil.make_archive` 
acts like an automatic cardboard box wrapper—it takes an entire folder full of files 
and zips them up all at once in a single command!

Key Upgrades in this version:
1. `import shutil`: Brings in Python's high-powered digital moving crew.
2. `shutil.make_archive(...)`: Automatically compresses the whole output folder.
3. Clean verification: Ensures the finished archive file is ready on disk.
"""

# Step 1: Gathering our tools (Importing libraries)

import os          # Helps Python navigate folders and check if files exist
import threading   # Gives Python extra hands so it can work on big tasks in the background
import math        # Used for math functions (like rounding numbers UP)
import time        # Reads the system clock to create unique timestamp IDs
import shutil      # 📦 NEW! Powerful file manager that zips whole folders instantly
import logging     # Keeps a written journal of application events and errors

# Flask turns Python into a web server that communicates with browser visitors
from flask import Flask, request, render_template, send_file, jsonify, url_for
import pandas as pd # Ultra-fast spreadsheet tool for cutting up CSV files
from werkzeug.utils import secure_filename # Cleans file names so nobody can upload harmful characters


# Step 2: Application Configuration

app = Flask(__name__) # Fires up our web application engine

# Store uploaded and processed files in an "uploads" folder
app.config['UPLOAD_FOLDER'] = 'uploads'

# Maximum upload size limit: 1 Gigabyte (1,024 MB)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  

# Create the "uploads" folder automatically if it doesn't exist yet
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 📝 LOGGING SETUP: Print helpful status logs (INFO level) to the terminal
logging.basicConfig(level=logging.INFO)

# A master notebook (dictionary) keeping track of every active split job
tasks = {}



# Step 3: The SplitTask Worker Class
# Think of this class like a order ticket that tracks every detail of a job.

class SplitTask:
    def __init__(self, filename, rows_per_file):
        """Prepares a new job tracking card when a user uploads a file."""
        self.filename = filename              # The original uploaded file name
        self.rows_per_file = rows_per_file    # Row limit for each small file
        self.progress = 0                     # Starts at 0%
        self.status = 'pending'               # Statuses: 'pending', 'processing', 'done', 'error'
        self.error = None                     # Stores error text if something fails
        self.zip_path = None                  # Keeps track of the final ZIP location
        self.total_parts = 0                  # How many small files will be created
        self.processed_parts = 0              # How many small files are completed

    def run(self):
        """This function does the heavy lifting: counting rows, slicing CSVs, and zipping!"""
        try:
            self.status = 'processing' # Mark job as actively working
            
            # Full path to the uploaded file on our hard drive
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], self.filename)
            
            # Strip off the extension (e.g. "data.csv" -> "data")
            base_name = self.filename.rsplit('.', 1)[0]
            
            # Make a dedicated output subfolder for the chopped pieces
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"split_{base_name}")
            os.makedirs(output_dir, exist_ok=True)

            # --- Step A: Count the data rows in the uploaded CSV ---
            total_rows = 0
            with open(input_path, 'r', encoding='utf-8') as f:
                next(f, None) # Skip the header row (column names)
                for _ in f:
                    total_rows += 1 # Count each remaining row

            # Abort if the file contains no data rows
            if total_rows == 0:
                self.status = 'error'
                self.error = "CSV file has no data rows."
                return

            # --- Step B: Calculate total output parts ---
            # math.ceil rounds UP so no remainder rows get left behind!
            self.total_parts = math.ceil(total_rows / self.rows_per_file)
            self.processed_parts = 0

            # --- Step C: Slice the large CSV into smaller chunk files ---
            for i, chunk in enumerate(pd.read_csv(input_path, chunksize=self.rows_per_file, low_memory=False)):
                # Format file numbers with padded zeroes (e.g., part_0001.csv, part_0002.csv)
                part_filename = f"part_{i+1:04d}.csv"
                out_path = os.path.join(output_dir, part_filename)
                chunk.to_csv(out_path, index=False)
                
                # Update progress tracking for the progress bar
                self.processed_parts = i + 1
                self.progress = int((self.processed_parts / self.total_parts) * 100)

            # --- Step D: Create ZIP archive using shutil ---
            # 📦 `shutil.make_archive` takes 3 parameters:
            # 1. Base path for the output file (without extension)
            # 2. Format ('zip')
            # 3. The target folder containing the files to compress (`output_dir`)
            zip_base = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}_split")
            archive_path = shutil.make_archive(zip_base, 'zip', output_dir)

            # 🛡️ Verify that shutil successfully generated the file on disk
            if not os.path.exists(archive_path):
                raise Exception("Archive creation failed – file not found.")

            # Record success!
            self.zip_path = archive_path
            self.status = 'done'
            self.progress = 100
            
            # Log the successful ZIP path
            logging.info(f"ZIP created: {archive_path}")

        except Exception as e:
            # Catch crashes, store error message, and log the failure
            self.status = 'error'
            self.error = str(e)
            logging.error(f"Task failed: {e}")



# Step 4: Web Application Routes (Server Endpoints)

# --- Main Page ---
@app.route('/', methods=['GET'])
def index():
    """Serves the front-end user interface (index.html)."""
    return render_template('index.html')


# --- File Upload Endpoint ---
@app.route('/upload', methods=['POST'])
def upload():
    """Receives the uploaded file and starts the background splitting worker."""
    
    # 1. Verify a file was sent
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # 2. Verify row limit input is valid
    rows_per_file = request.form.get('rows', type=int)
    if not rows_per_file or rows_per_file <= 0:
        return jsonify({'error': 'Invalid row count'}), 400

    # 3. Secure the filename and save to uploads folder
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 4. Create a unique task ticket ID using current timestamp
    task_id = str(int(time.time() * 1000))
    task = SplitTask(filename, rows_per_file)
    tasks[task_id] = task

    # ⚡ Launch worker on a separate background thread so server stays responsive
    thread = threading.Thread(target=task.run)
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})


# --- Status Polling Endpoint ---
@app.route('/status/<task_id>', methods=['GET'])
def status(task_id):
    """The webpage continuously checks this route for progress updates."""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    response = {
        'status': task.status,
        'progress': task.progress,
        'total_parts': task.total_parts,
        'processed_parts': task.processed_parts,
        'error': task.error,
    }
    
    # Provide download link only when complete and ZIP file exists on disk
    if task.status == 'done' and task.zip_path and os.path.exists(task.zip_path):
        response['download_url'] = url_for('download', task_id=task_id)
        
    return jsonify(response)


# --- File Download Endpoint ---
@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    """Delivers the finished ZIP archive to the browser download prompt."""
    task = tasks.get(task_id)
    if not task:
        return 'Task not found', 404
    if task.status != 'done':
        return 'File not ready', 404
    if not task.zip_path or not os.path.exists(task.zip_path):
        return 'ZIP file not found – try re‑running the split.', 404
        
    return send_file(task.zip_path, as_attachment=True)


# Step 5: Start Server Engine

if __name__ == '__main__':
    # Launch application server at http://localhost:5000/
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))