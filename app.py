from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd, sqlite3, os, io
import matplotlib.pyplot as plt
import base64
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

def fetch_df_units(date):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT content,filename FROM files WHERE date=? ORDER BY id DESC",(date,)).fetchone()
    conn.close()
    if not row:
        return None, []
    content, filename = row
    ext = filename.rsplit('.',1)[1].lower()
    buf = io.BytesIO(content)
    try:
        if ext == 'csv':
            df = pd.read_csv(buf, encoding_errors='replace', skiprows=4).dropna(how='all').dropna(axis=1, how='all')
        else:
            df = pd.read_excel(buf, header=4).dropna(how='all').dropna(axis=1, how='all')
        columns = df.columns.tolist()
        return df, columns
    except Exception:
        return None, []

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    dates = [r[0] for r in conn.execute("SELECT DISTINCT date FROM files ORDER BY date DESC")]
    conn.close()
    # get categories from latest date
    categories = []
    if dates:
        _, categories = fetch_df_units(dates[0])
    return render_template('index.html', dates=dates, categories=categories)

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
        conn.execute("INSERT INTO files (filename, date, content) VALUES (?, ?, ?)", (fn, date, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/compare', methods=['POST'])
def compare():
    d1 = request.form.get('date1'); d2 = request.form.get('date2')
    category = request.form.get('category'); unit = request.form.get('unit')
    df1, cols1 = fetch_df_units(d1) if d1 else (None, [])
    df2, cols2 = fetch_df_units(d2) if d2 and d2 != d1 else (None, [])
    # HTML tables
    table1 = df1.to_html(index=False, na_rep='') if df1 is not None else None
    table2 = df2.to_html(index=False, na_rep='') if df2 is not None else None
    # Chart
    chart = None
    if category and df1 is not None and category in df1.columns:
        values = [df1[category].astype(float).mean()]
        labels = [d1]
        if df2 is not None and category in df2.columns:
            values.append(df2[category].astype(float).mean()); labels.append(d2)
        fig, ax = plt.subplots()
        ax.bar(labels, values)
        ax.set_ylabel(unit); ax.set_title(f"{category} Comparison")
        buf = io.BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight'); plt.close(fig); buf.seek(0)
        chart = base64.b64encode(buf.read()).decode()
    return render_template('compare.html', dates=dates, categories=cols1,
        table1=table1, table2=table2, date1=d1, date2=d2,
        selected_cat=category, units=[unit], chart=chart)

if __name__=='__main__':
    app.run()
