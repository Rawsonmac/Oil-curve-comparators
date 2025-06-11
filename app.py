from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd, sqlite3, os, io, openai
from werkzeug.utils import secure_filename
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DB_FILE = 'data.db'
PASSWORD = 'ownerpass123'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn=sqlite3.connect(DB_FILE); c=conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, filename TEXT, date TEXT, content BLOB)")
    conn.commit(); conn.close()
init_db()

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn=sqlite3.connect(DB_FILE); dates=[r[0] for r in conn.execute("SELECT DISTINCT date FROM files ORDER BY date DESC")]; conn.close()
    return render_template('index.html', dates=dates)

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('password')!=PASSWORD: abort(403)
    f=request.files.get('file'); d=request.form.get('filedate')
    if f and d and allowed_file(f.filename):
        fn=secure_filename(f.filename); content=f.read()
        conn=sqlite3.connect(DB_FILE); conn.execute("INSERT INTO files(filename,date,content) VALUES(?,?,?)",(fn,d,content)); conn.commit(); conn.close()
    return redirect(url_for('index'))

@app.route('/compare', methods=['POST'])
def compare():
    d1=request.form.get('date1'); d2=request.form.get('date2')
    def fetch(date):
        conn=sqlite3.connect(DB_FILE); row=conn.execute("SELECT content,filename FROM files WHERE date=? ORDER BY id DESC",(date,)).fetchone(); conn.close()
        if not row: return None
        content,fn=row; ext=fn.rsplit('.',1)[1].lower(); buf=io.BytesIO(content)
        try:
            return pd.read_csv(buf, encoding_errors='replace') if ext=='csv' else pd.read_excel(buf)
        except:
            return None
    df1=fetch(d1); df2=fetch(d2) if d2 and d2!=d1 else None
    table1=df1.to_html(index=False) if df1 is not None else None
    table2=df2.to_html(index=False) if df2 is not None else None
    # AI analysis optional
    try:
        prompt=f"Dataset1 columns: {list(df1.columns)}\nDataset2 columns: {list(df2.columns) if df2 else 'None'}"
        analysis=openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        ).choices[0].message.content
    except:
        analysis="Analysis unavailable."
    return render_template('compare.html', table1=table1, table2=table2, date1=d1, date2=d2, analysis=analysis)

if __name__=='__main__':
    app.run(debug=True)
