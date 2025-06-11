from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
from io import BytesIO

app = Flask(__name__)
UPLOAD_PASSWORD = 'ownerpass123'
DB_FILE = 'uploads.db'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            filename TEXT,
            content BLOB,
            filetype TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT DISTINCT date FROM uploads ORDER BY date DESC')
    dates = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', dates=dates)

@app.route('/upload', methods=['POST'])
def upload():
    password = request.form.get('password')
    if password != UPLOAD_PASSWORD:
        abort(403)
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filetype = filename.rsplit('.', 1)[1].lower()
        date = datetime.now().strftime('%Y-%m-%d')
        content = file.read()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO uploads (date, filename, content, filetype) VALUES (?, ?, ?, ?)',
                  (date, filename, content, filetype))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    date1 = request.args.get('date1')
    date2 = request.args.get('date2')
    dates = [d for d in [date1, date2] if d]
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    dataframes = []
    for d in dates:
        c.execute('SELECT filename, content, filetype FROM uploads WHERE date = ?', (d,))
        rows = c.fetchall()
        for filename, content, filetype in rows:
            df = pd.read_csv(BytesIO(content)) if filetype == 'csv' else pd.read_excel(BytesIO(content))
            df['Source'] = f"{d}_{filename}"
            dataframes.append(df)
    conn.close()

    if not dataframes:
        return render_template('results.html', tables=[], query=", ".join(dates))

    combined = pd.concat(dataframes, ignore_index=True)
    return render_template('results.html', tables=[combined.to_html(classes='data table table-striped', index=False)], query=", ".join(dates))

if __name__ == '__main__':
    init_db()
    app.run()
