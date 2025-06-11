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
    f = request.files.get('file')
    date = request.form.get('filedate')
    if f and date and allowed_file(f.filename):
        fn = secure_filename(f.filename)
        content = f.read()
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO files(filename,date,content) VALUES(?,?,?)", (fn, date, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

def fetch_df(date):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT content,filename FROM files WHERE date=? ORDER BY id DESC", (date,)).fetchone()
    conn.close()
    if not row:
        return None
    buf = io.BytesIO(row[0])
    ext = row[1].rsplit('.',1)[1].lower()
    try:
        return pd.read_csv(buf, encoding_errors='replace').dropna(how='all', axis=0).dropna(how='all', axis=1)
    except:
        try:
            return pd.read_excel(buf).dropna(how='all', axis=0).dropna(how='all', axis=1)
        except:
            return None

@app.route('/compare', methods=['POST'])
def compare():
    date1 = request.form.get('date1')
    date2 = request.form.get('date2')
    category = request.form.get('category')
    unit = request.form.get('unit')
    df1 = fetch_df(date1) if date1 else None
    df2 = fetch_df(date2) if date2 and date2 != date1 else None

    # Prepare chart
    chart = None
    if category and df1 is not None:
        values = []
        labels = []
        values.append(df1[category].mean() if category in df1.columns else 0)
        labels.append(date1)
        if df2 is not None and category in df2.columns:
            values.append(df2[category].mean())
            labels.append(date2)
        fig, ax = plt.subplots()
        ax.bar(labels, values)
        ax.set_ylabel(unit)
        ax.set_title(f"{category} Comparison")
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        chart = base64.b64encode(buf.read()).decode('utf-8')

    # Tables
    table1 = df1.to_html(index=False, na_rep='') if df1 is not None else None
    table2 = df2.to_html(index=False, na_rep='') if df2 is not None else None

    # Columns for filter dropdown
    columns = list(df1.columns) if df1 is not None else []

    return render_template('compare.html', dates=[], table1=table1, table2=table2,
                           date1=date1, date2=date2,
                           category=category, unit=unit,
                           columns=columns, chart=chart)

if __name__=='__main__':
    app.run()
