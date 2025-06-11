from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
    return redirect(url_for('index'))

@app.route('/compare', methods=['POST'])
def compare():
    file1 = request.form.get('file1')
    file2 = request.form.get('file2')

    ext1 = file1.rsplit('.', 1)[1].lower()
    ext2 = file2.rsplit('.', 1)[1].lower()

    if ext1 == 'csv':
        df1 = pd.read_csv(os.path.join(UPLOAD_FOLDER, file1))
    else:
        df1 = pd.read_excel(os.path.join(UPLOAD_FOLDER, file1))

    if ext2 == 'csv':
        df2 = pd.read_csv(os.path.join(UPLOAD_FOLDER, file2))
    else:
        df2 = pd.read_excel(os.path.join(UPLOAD_FOLDER, file2))

    df1['Source'] = file1
    df2['Source'] = file2

    comparison = pd.concat([df1, df2], ignore_index=True)

    return render_template('compare.html', tables=[comparison.to_html(classes='data table table-striped', index=False)], titles=["Comparison Result"])

if __name__ == '__main__':
    app.run()
