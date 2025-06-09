from flask import Flask, request, render_template, redirect, send_file, url_for, flash, jsonify
import os
import uuid
import csv
import pandas as pd  # pandas to handle Excel files
import io
 
import requests
from requests.auth import HTTPBasicAuth
from utils.file_utils import create_splunk_app, extract_zip, rezip_app, save_file, is_valid_splunk_conf
 
app = Flask(__name__)
app.secret_key = 'your_secret_key'
 
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
APPS_DIR = r'C:\Program Files\Splunk\etc\apps'
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')

# This is fine to create only if it doesn't exist
os.makedirs(UPLOADS_DIR, exist_ok=True)

 
SPLUNK_HOST = '127.0.0.1'
SPLUNK_PORT = '8089'
SPLUNK_USER = 'MTL1013'
SPLUNK_PASSWORD = 'MTL@1013'
 
def splunk_session():
    session = requests.Session()
    session.auth = HTTPBasicAuth(SPLUNK_USER, SPLUNK_PASSWORD)
    session.verify = False  # For self-signed certs (disable in prod)
    return session
 
def create_splunk_index(index_name):
    url = f'https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/data/indexes'
    try:
        session = splunk_session()
        response = session.post(url, data={'name': index_name})
        response.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)
 
@app.route('/')
def index():
    return render_template('splunk_index.html')
 
@app.route('/splunk_indexes')
def splunk_indexes():
    try:
        session = splunk_session()
        url = f'https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/data/indexes?output_mode=json'
        response = session.get(url)
        response.raise_for_status()
        indexes = [entry['name'] for entry in response.json().get('entry', []) if not entry['content'].get('disabled', False)]
        return jsonify(indexes)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
 
import csv
import os
import uuid
from flask import request, flash, redirect, url_for
 
@app.route('/create_app', methods=['POST'])
def create_app():
    app_name = request.form.get('app_name')
    index_name = request.form.get('index_name') or request.form.get('new_index_name')
    me_count = request.form.get('me_count')
 
    if not app_name or not index_name:
        flash('App name and index name are required.', 'error')
        return redirect(url_for('index'))
 
    if request.form.get('new_index_name'):
        success, error = create_splunk_index(index_name)
        if not success:
            flash(f"Failed to create index: {error}", 'error')
            return redirect(url_for('index'))
 
    # Collect sources info
    sources = []
 
    if me_count is None:
        flash('Please specify how many sources.', 'error')
        return redirect(url_for('index'))
 
    if me_count.isdigit():
        count = int(me_count)
        for i in range(1, count + 1):
            source_name = request.form.get(f'source{i}_name')
            log_path = request.form.get(f'source{i}_logpath')
            if not source_name or not log_path:
                flash(f'Missing source name or log path for source {i}.', 'error')
                return redirect(url_for('index'))
            sources.append({'name': source_name, 'logpath': log_path})
 
 
    elif me_count == 'more':
        print("added the file")
        file = request.files.get('me_file_upload')
 
        if not file:
            flash('Please upload a file with source data.', 'error')
            return redirect(url_for('index'))
 
        try:
            filename = file.filename.lower()
            sources = []  # Make sure this is initialized
 
            if filename.endswith('.csv'):
                # Handle CSV file
                file_contents = file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(file_contents)
 
                for row in reader:
                    source_name = row.get('Source Name') or row.get('source_name') or row.get('sourceName')
                    log_path = row.get('Log Path') or row.get('log_path') or row.get('logPath')
                    if source_name and log_path:
                        sources.append({'name': source_name.strip(), 'logpath': log_path.strip()})
 
            elif filename.endswith('.xlsx'):
                # Handle Excel (.xlsx) file
                df = pd.read_excel(file)
                for _, row in df.iterrows():
                    source_name = row.get('Source Name') or row.get('source_name') or row.get('sourceName')
                    log_path = row.get('Log Path') or row.get('log_path') or row.get('logPath')
                    if source_name and log_path:
                        sources.append({'name': str(source_name).strip(), 'logpath': str(log_path).strip()})
 
            else:
                flash('Unsupported file type. Please upload a CSV or Excel file.', 'error')
                return redirect(url_for('index'))
 
            if not sources:
                flash('No valid source data found in the uploaded file.', 'error')
                return redirect(url_for('index'))
 
        except Exception as e:
            flash(f'Failed to process uploaded file: {str(e)}', 'error')
            return redirect(url_for('index'))
 
    else:
        flash('Invalid sources count selection.', 'error')
        return redirect(url_for('index'))
 
    # Create app_id and path
    app_id = f"{app_name}"
    app_path = os.path.join(APPS_DIR, app_id)
 
 
    create_splunk_app(app_path, app_name, index_name, sources=sources)
 
    return redirect(url_for('browse_files', app_id=app_id))
 
 
@app.route('/upload_zip', methods=['POST'])
def upload_zip():
    uploaded_file = request.files.get('zip_file')
    if uploaded_file and uploaded_file.filename.endswith('.zip'):
        app_id = str(uuid.uuid4())
        app_path = os.path.join(APPS_DIR, app_id)
        os.makedirs(app_path, exist_ok=True)
        extract_zip(uploaded_file, app_path)
        return redirect(url_for('browse_files', app_id=app_id))
    flash('Please upload a valid .zip file', 'error')
    return redirect(url_for('index'))
 
@app.route('/edit/<app_id>/browse', defaults={'folder_path': ''})
@app.route('/edit/<app_id>/browse/<path:folder_path>')
def browse_files(app_id, folder_path):
    app_root = os.path.join(APPS_DIR, app_id)
    current_folder = os.path.join(app_root, folder_path)
 
    if not os.path.exists(current_folder):
        flash('Folder not found', 'error')
        return redirect(url_for('index'))
 
    folders = []
    files = []
 
    for entry in os.listdir(current_folder):
        full_path = os.path.join(current_folder, entry)
        rel_path = os.path.relpath(full_path, app_root)
        if os.path.isdir(full_path):
            folders.append({'name': entry, 'full_path': rel_path})
        else:
            files.append({'name': entry, 'full_path': rel_path})
 
    parent_path = os.path.dirname(folder_path) if folder_path else None
 
    return render_template('splunk_editor.html',
                           app_id=app_id,
                           folders=folders,
                           files=files,
                           current_path=folder_path,
                           parent_path=parent_path,
                           selected_file=None)
 
import os
import shutil
import subprocess
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request



# Adjust these paths according to your setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
APPS_DIR = r'C:\Users\MTL1013\OneDrive - Middleware Talents Limited\Desktop\appv2 (1)\appv2\apps'  # Your apps folder during dev
SPLUNK_APPS_DIR = r'C:\Program Files\Splunk\etc\apps'  # Production Splunk apps dir

@app.route('/validate/<app_id>', methods=['GET', 'POST'])
def validation_workflow(app_id):
    stage = int(request.args.get('stage', 2))  # default stage = 2 (Config Validation)
    app_path = os.path.join(APPS_DIR, app_id)

    if stage == 2:
        logs = run_btool_check(app_path)
    elif stage == 3:
        logs = send_email_notification(app_id)
    elif stage == 4:
        logs = deploy_splunk_app(app_id, app_path)
    elif stage == 5:
        logs = get_internal_logs()
    else:
        logs = "Unknown stage."

    return render_template(
        'validation_workflow.html',
        app_id=app_id,
        btool_logs=logs,
        stage=stage,
        enumerate=enumerate 
    )


def run_btool_check(app_dir):
    app_name = os.path.basename(app_dir)
    conf_dirs = [os.path.join(app_dir, 'default'), os.path.join(app_dir, 'local')]
    output = ""

    for conf_dir in conf_dirs:
        if not os.path.exists(conf_dir):
            continue
        for conf_file in os.listdir(conf_dir):
            if conf_file.endswith('.conf'):
                conf_name = conf_file.replace('.conf', '')
                try:
                    cmd = [
                        r'C:\Program Files\Splunk\bin\splunk.exe',
                        'btool',
                        conf_name,
                        'list',
                        '--debug',
                        '--app=' + app_name
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    output += f"=== {conf_name}.conf ===\n"
                    if result.returncode == 0:
                        output += result.stdout
                    else:
                        output += result.stderr
                    output += "\n\n"
                except Exception as e:
                    output += f"Error running btool for {conf_name}: {str(e)}\n\n"
    return output.strip()


def send_email_notification(app_id):
    try:
        msg = EmailMessage()
        msg.set_content(f"Splunk App '{app_id}' validation complete and ready for approval.")
        msg['Subject'] = f'Splunk App {app_id} Validation Notification'
        msg['From'] = 'yaswanthkumarch2001@gmail.com'      # Change as needed
        msg['To'] = 'Yaswanth@middlewaretalents.com'           # Change as needed

        with smtplib.SMTP('smtp.gmail.com') as server:
            server.login('yaswanthkumarch2001@gmail.com', 'uqjc bszf djfw bsor')  # Use real SMTP creds
            server.send_message(msg)

        return "Email notification sent successfully."
    except Exception as e:
        return f"Failed to send email: {str(e)}"


def deploy_splunk_app(app_id, app_path):
    try:
        dest_path = os.path.join(SPLUNK_APPS_DIR, app_id)

        # Remove existing app folder in Splunk if exists
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)

        # Copy app files to Splunk apps directory
        shutil.copytree(app_path, dest_path)

        # Optional: restart Splunk service to pick changes
        # subprocess.run(['net', 'stop', 'splunk'], check=True)
        # subprocess.run(['net', 'start', 'splunk'], check=True)

        return f"App '{app_id}' deployed to Splunk successfully."
    except Exception as e:
        return f"Deployment failed: {str(e)}"


def get_internal_logs():
    log_path = r'C:\Program Files\Splunk\var\log\splunk\splunkd.log'
    try:
        with open(log_path, 'r') as f:
            # Return last 3000 chars for brevity
            return f.read()[-3000:]
    except Exception as e:
        return f"Could not read Splunk internal logs: {str(e)}"


@app.route('/edit/<app_id>/<path:file_path>', methods=['GET', 'POST'])
def edit_file(app_id, file_path):
    full_path = os.path.join(APPS_DIR, app_id, file_path)
 
    if not os.path.exists(full_path):
        flash('File not found', 'error')
        return redirect(url_for('browse_files', app_id=app_id, folder_path=os.path.dirname(file_path)))
 
    validation_message = None
    recommendations = []
 
    if request.method == 'POST':
        content = request.form['content']
 
        if full_path.endswith('.conf'):
            is_valid, validation_message = is_valid_splunk_conf(content)
            if not is_valid:
                flash(validation_message, 'error')
                return redirect(url_for('edit_file', app_id=app_id, file_path=file_path))
 
        save_file(full_path, content)
        flash('File saved successfully!', 'success')
        return redirect(url_for('validation_workflow', app_id=app_id))
        # return redirect(url_for('edit_file', app_id=app_id, file_path=file_path, mode='read'))
 
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
 
    if os.path.basename(full_path) == 'inputs.conf':
        if '[monitor://' not in content:
            recommendations.append("⚠️ You haven't defined any `[monitor://...]` stanzas.")
        if 'index =' not in content:
            recommendations.append("💡 Add `index = your_index_name` to send data to a Splunk index.")
        if 'disabled = 0' not in content:
            recommendations.append("📝 Use `disabled = 0` to ensure the input is enabled.")
 
    mode = request.args.get('mode', 'read')
    read_only = (mode != 'edit')
 
    app_root = os.path.join(APPS_DIR, app_id)
    current_path = os.path.dirname(file_path)
    parent_path = os.path.dirname(current_path) if current_path else None
 
    folders, files = [], []
    current_folder = os.path.join(app_root, current_path)
    for entry in os.listdir(current_folder):
        full_entry_path = os.path.join(current_folder, entry)
        rel_path = os.path.relpath(full_entry_path, app_root)
        if os.path.isdir(full_entry_path):
            folders.append({'name': entry, 'full_path': rel_path})
        else:
            files.append({'name': entry, 'full_path': rel_path})
 
    return render_template('splunk_editor.html',
                           app_id=app_id,
                           selected_file=file_path,
                           content=content,
                           read_only=read_only,
                           current_path=current_path,
                           parent_path=parent_path,
                           folders=folders,
                           files=files,
                           validation_message=validation_message,
                           recommendations=recommendations)
 
@app.route('/download/<app_id>')
def download_app(app_id):
    app_path = os.path.join(APPS_DIR, app_id)
    zip_path = os.path.join(UPLOADS_DIR, f"{app_id}.zip")
    rezip_app(app_path, zip_path)
    return send_file(zip_path, as_attachment=True)
 
@app.route('/home')
def home():
    return render_template('splunk_index.html')
 
if __name__ == '__main__':
    app.run(debug=True)
 