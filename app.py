from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd, sqlite3, os, io, openai
from werkzeug.utils import secure_filename
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'; DB_FILE = 'data.db'
PASSWORD = 'ownerpass123'; ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Init DB
conn = sqlite3.connect(DB_FILE)
conn.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, filename TEXT, date TEXT, content BLOB)")
conn.commit(); conn.close()

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
    if request.form.get('password') != PASSWORD: abort(403)
    f = request.files.get('file'); d = request.form.get('filedate')
    if f and d and allowed_file(f.filename):
        fn = secure_filename(f.filename); content = f.read()
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO files(filename,date,content) VALUES(?,?,?)", (fn, d, content))
        conn.commit(); conn.close()
    return redirect(url_for('index'))

def fetch_df(date):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT content,filename FROM files WHERE date=? ORDER BY id DESC", (date,)).fetchone()
    conn.close()
    if not row: return None
    buf = io.BytesIO(row[0]); ext = row[1].rsplit('.',1)[1].lower()
    try:
        return pd.read_csv(buf, encoding_errors='replace') if ext=='csv' else pd.read_excel(buf)
    except:
        return None

def analyze_data(df1, df2=None):
    if not openai.api_key:
        return "AI analysis unavailable: OPENAI_API_KEY not set."
    desc1 = df1.describe().to_dict() if df1 is not None else {}
    desc2 = df2.describe().to_dict() if df2 is not None else {}
    prompt = f"Dataset1 summary: {desc1}\n"
    if df2 is not None:
        prompt += f"Dataset2 summary: {desc2}\nCompare these datasets."
    else:
        prompt += "Provide insights on this dataset."
    try:
        resp = openai.ChatCompletion.create(model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}])
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"

@app.route('/compare', methods=['POST'])
def compare():
    d1 = request.form.get('date1'); d2 = request.form.get('date2')
    df1 = fetch_df(d1); df2 = fetch_df(d2) if d2 and d2!=d1 else None
    table1 = df1.to_html(index=False) if df1 is not None else None
    table2 = df2.to_html(index=False) if df2 is not None else None
    analysis = analyze_data(df1, df2)
    return render_template('compare.html', table1=table1, table2=table2,
        date1=d1, date2=d2, analysis=analysis)

if __name__=='__main__':
    app.run()
