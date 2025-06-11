from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_PASSWORD = 'ownerpass123'  # Change this to your own password

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    password = request.form.get('password')
    if password != UPLOAD_PASSWORD:
        abort(403)
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        date_prefix = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_prefix}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    query_date = request.args.get('date')
    matched_files = []
    for f in os.listdir(UPLOAD_FOLDER):
        if f.startswith(query_date) and allowed_file(f):
            matched_files.append(f)

    dataframes = []
    for f in matched_files:
        ext = f.rsplit('.', 1)[1].lower()
        path = os.path.join(UPLOAD_FOLDER, f)
        df = pd.read_csv(path) if ext == 'csv' else pd.read_excel(path)
        df['Source'] = f
        dataframes.append(df)

    if not dataframes:
        return render_template('results.html', tables=[], query=query_date)

    combined = pd.concat(dataframes, ignore_index=True)
    return render_template('results.html', tables=[combined.to_html(classes='data table table-striped', index=False)], query=query_date)

if __name__ == '__main__':
    app.run()
