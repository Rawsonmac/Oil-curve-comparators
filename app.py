from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd, sqlite3, os, io
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DB_FILE = 'data.db'
PASSWORD = 'ownerpass123'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, filename TEXT, date TEXT, content BLOB)")
    conn.commit()
    conn.close()
init_db()

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM files ORDER BY date DESC")
    dates = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template('index.html', dates=dates)

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('password') != PASSWORD:
        abort(403)
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        fn = secure_filename(file.filename)
        date = datetime.now().strftime('%Y-%m-%d')
        content = file.read()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO files (filename, date, content) VALUES (?, ?, ?)", (fn, date, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

def fetch_chunk(date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT content, filename FROM files WHERE date=? ORDER BY id DESC", (date,))
    for content, fname in c.fetchall():
        ext = fname.rsplit('.',1)[1].lower()
        stream = io.BytesIO(content)
        try:
            if ext=='csv':
                for chunk in pd.read_csv(stream, encoding_errors='replace', chunksize=5000):
                    return chunk
            else:
                df = pd.read_excel(stream, nrows=5000)
                return df
        except Exception:
            continue
    return None

@app.route('/compare', methods=['POST'])
def compare():
    date1 = request.form.get('date1')
    date2 = request.form.get('date2')
    df1 = fetch_chunk(date1) if date1 else None
    df2 = fetch_chunk(date2) if date2 and date2 != date1 else None
    table1 = df1.to_html(classes='data', index=False) if df1 is not None else None
    table2 = df2.to_html(classes='data', index=False) if df2 is not None else None
    return render_template('compare.html',
                           table1=table1, table2=table2,
                           date1=date1, date2=date2)

if __name__=='__main__':
    app.run()
