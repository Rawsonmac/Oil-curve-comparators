from flask import Flask, request, render_template, redirect, url_for, abort
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
UPLOAD_PASSWORD = 'ownerpass123'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
        stored_name = f"{date_prefix}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_name))
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    date1 = request.args.get('date1')
    date2 = request.args.get('date2')
    dates = [d for d in [date1, date2] if d]

    dataframes = []
    for fname in os.listdir(UPLOAD_FOLDER):
        for d in dates:
            if fname.startswith(d):
                fpath = os.path.join(UPLOAD_FOLDER, fname)
                ext = fname.rsplit('.', 1)[1].lower()
                df = pd.read_csv(fpath) if ext == 'csv' else pd.read_excel(fpath)
                df['Source'] = fname
                dataframes.append(df)

    if not dataframes:
        return render_template('results.html', tables=[], query=", ".join(dates))

    combined = pd.concat(dataframes, ignore_index=True)
    return render_template('results.html', tables=[combined.to_html(classes='data table table-striped', index=False)], query=", ".join(dates))

if __name__ == '__main__':
    app.run()
