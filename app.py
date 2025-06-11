from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DB_FILE = 'data.db'
PASSWORD = 'ownerpass123'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, filename TEXT, date TEXT, content BLOB)"
    )
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM files ORDER BY date DESC")
    dates = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', dates=dates)

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('password') != PASSWORD:
        return "Unauthorized", 403
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        date = datetime.now().strftime('%Y-%m-%d')
        content = file.read()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO files (filename, date, content) VALUES (?, ?, ?)", (filename, date, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    date1 = request.args.get('date1')
    date2 = request.args.get('date2')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data_frames = []
    for date in filter(None, [date1, date2]):
        c.execute("SELECT content, filename FROM files WHERE date = ? ORDER BY id DESC", (date,))
        for content, filename in c.fetchall():
            ext = filename.rsplit('.', 1)[1].lower()
            stream = io.BytesIO(content)
            try:
                df = pd.read_csv(stream, encoding_errors='replace') if ext == 'csv' else pd.read_excel(stream)
                df['Source Date'] = date
                df['Source File'] = filename
                data_frames.append(df)
            except Exception:
                continue
    conn.close()
    if not data_frames:
        return render_template('compare.html', tables=[], titles=[f"No data for selected dates: {date1}, {date2}"])
    combined = pd.concat(data_frames, ignore_index=True)
    html_table = combined.to_html(classes='data table table-striped', index=False)
    return render_template('compare.html', tables=[html_table], titles=[f"Data for {date1}" + (f" & {date2}" if date2 else "")])

if __name__ == '__main__':
    app.run(debug=True)
