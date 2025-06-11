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

# Initialize DB
conn = sqlite3.connect(DB_FILE)
conn.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, filename TEXT, date TEXT, content BLOB)")
conn.commit()
conn.close()

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    dates = [row[0] for row in conn.execute("SELECT DISTINCT date FROM files ORDER BY date DESC")]
    conn.close()
    return render_template('index.html', dates=dates)

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('password') != PASSWORD:
        abort(403)
    file = request.files.get('file')
    date = request.form.get('filedate')
    if file and date and allowed_file(file.filename):
        fn = secure_filename(file.filename)
        content = file.read()
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO files(filename,date,content) VALUES(?,?,?)", (fn, date, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

def fetch_table(date):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT content,filename FROM files WHERE date=? ORDER BY id DESC", (date,)).fetchone()
    conn.close()
    if not row: return None
    buf = io.BytesIO(row[0]); fn = row[1]
    ext = fn.rsplit('.',1)[1].lower()
    try:
        if ext == 'csv':
            df = pd.read_csv(buf, encoding_errors='replace', nrows=100)
        else:
            df = pd.read_excel(buf, nrows=100)
        return df
    except:
        return None

@app.route('/compare', methods=['POST'])
def compare():
    d1 = request.form.get('date1')
    d2 = request.form.get('date2')
    df1 = fetch_table(d1) if d1 else None
    df2 = fetch_table(d2) if d2 and d2 != d1 else None
    table1 = df1.to_html(index=False) if df1 is not None else None
    table2 = df2.to_html(index=False) if df2 is not None else None
    return render_template('compare.html', table1=table1, table2=table2, date1=d1, date2=d2)

if __name__=='__main__':
    app.run()
