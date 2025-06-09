from flask import Flask, request, render_template, redirect, send_file, url_for, flash, jsonify
import os
import uuid
import csv
import shutil
import subprocess
import requests
from requests.auth import HTTPBasicAuth
from utils.file_utils import create_splunk_app, extract_zip, rezip_app, save_file, is_valid_splunk_conf
from email.message import EmailMessage
import smtplib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret in prod

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
APPS_DIR = r'C:\Program Files\Splunk\etc\apps'
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

SPLUNK_HOST = '127.0.0.1'
SPLUNK_PORT = '8089'
SPLUNK_USER = 'MTL1013'
SPLUNK_PASSWORD = 'MTL@1013'


def splunk_session():
    session = requests.Session()
    session.auth = HTTPBasicAuth(SPLUNK_USER, SPLUNK_PASSWORD)
    session.verify = False  # Disable SSL verification for self-signed certs (not recommended in prod)
    return session


def create_splunk_index(new_index_name):
    url = f'https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/data/indexes'
    try:
        session = splunk_session()
        response = session.post(url, data={'name': new_index_name})
        response.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)


@app.route('/')
def index():
    return render_template('s1_index.html')


@app.route('/splunk_indexes')
def splunk_indexes():
    try:
        session = splunk_session()
        url = f'https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/data/indexes?output_mode=json'
        response = session.get(url)
        response.raise_for_status()
        indexes = [
            entry['name']
            for entry in response.json().get('entry', [])
            if not entry['content'].get('disabled', False)
        ]
        return jsonify(indexes)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

import os
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
import pandas as pd
from werkzeug.utils import secure_filename

from datetime import datetime

# Create a unique app_id using app name and current month-year
timestamp = datetime.now().strftime('%b_%Y').lower()  # e.g. 'jun_2025'

# Set the upload folder and allowed file extensions
UPLOAD_FOLDER = 'apps'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your_secret_key'  # To enable flash messages

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to handle form submission
from datetime import datetime

@app.route('/create_app', methods=['POST'])
def create_app():
    me_count = request.form.get('me_count')
    app_name = request.form.get('app_name')  # New field for app name
    index_name = request.form.get('new_index_name')  # Existing or 'new'
    new_index_name = request.form.get('new_index_name') 
    print("##################################")
    print(f'{index_name}')
    print(f'{new_index_name}')
    print(f'{app_name}')
    print(f'{me_count}')
    print("##################################")
     # If creating a new index
    if request.form.get('new_index_name'):
        success, error = create_splunk_index(index_name)
        if not success:
            flash(f"Failed to create index: {error}", 'error')
            return redirect(url_for('index'))
    # Generate timestamp for app_id
    timestamp = datetime.now().strftime("%b_%Y")  # e.g. Jun_2025

    # Clean app_name for ID
    clean_app_name = app_name.replace(" ", "_") if app_name else "app"

    # Determine final index_name
    if index_name == 'new':
        if not new_index_name:
            flash("Please provide a name for the new index", "error")
            return redirect(request.url)
        index_name = new_index_name.strip()

    # Generate app_id using app_name and timestamp
    app_id = f"{clean_app_name}_{timestamp}"

    sources = []

    # If "more", process uploaded file
    if me_count == 'more':
        if 'me_file_upload' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['me_file_upload']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Read CSV or Excel
            if filename.endswith('.csv'):
                data = pd.read_csv(file_path)
            else:
                data = pd.read_excel(file_path)

            for _, row in data.iterrows():
                source_data = {
                    'config_type': row.get('config_type'),
                    'stanza_type': row.get('stanza_type'),
                    'stanza_value': row.get('stanza_value'),
                    'key': row.get('key'),
                    'value': row.get('value'),
                    'created_time': row.get('created_time', None)
                }
                sources.append(source_data)

        else:
            flash('Invalid file type', 'error')
            return redirect(request.url)

    else:
        # Manual form data
        try:
            count = int(me_count)
        except (ValueError, TypeError):
            count = 0

        for i in range(1, count + 1):
            data = {
                'config_type': request.form.get(f'source{i}_config_type'),
                'stanza_type': request.form.get(f'source{i}_stanza_type'),
                'stanza_value': request.form.get(f'source{i}_stanza_value'),
                'key': request.form.get(f'source{i}_key'),
                'value': request.form.get(f'source{i}_value'),
                'created_time': request.form.get(f'source{i}_created_time', None)
            }
            sources.append(data)

    # Create Splunk app directory and files
    app_path = os.path.join(app.config['UPLOAD_FOLDER'], app_id)
    create_splunk_app(app_path, app_name, index_name, sources)

    # If new index, create index config file
    if request.form.get('index_name') == 'new':
        create_splunk_index(app_path, index_name)

    flash('App created successfully!', 'success')
    return redirect(url_for('browse_files', app_id=app_id))


def create_splunk_app(path, app_name, index_name, sources=None):
    os.makedirs(path, exist_ok=True)
    folders = ['default', 'local', 'metadata', 'bin']
    for folder in folders:
        os.makedirs(os.path.join(path, folder), exist_ok=True)

    # README
    with open(os.path.join(path, 'README.txt'), 'w') as f:
        f.write(f"App: {app_name}\nIndex: {index_name}\n")

    # app.conf
    with open(os.path.join(path, 'default', 'app.conf'), 'w') as f:
        f.write(f"""[install]
state = enabled

[ui]
is_visible = true
label = {app_name}

[launcher]
author = Auto Generator
description = Splunk app created via UI
version = 1.0.0
""")

    if not sources:
        return

    # Group sources by config_type
    grouped = {}
    for row in sources:
        ctype = row.get("config_type", "default").strip().lower()
        grouped.setdefault(ctype, []).append(row)

    for conf_type, rows in grouped.items():
        conf_path = os.path.join(path, 'default', f"{conf_type}.conf")
        stanzas = {}

        for row in rows:
            stanza_type = row.get("stanza_type", "").strip()
            stanza_values = [s.strip() for s in str(row.get("stanza_value", "")).split(',') if s.strip()]
            keys = [k.strip() for k in str(row.get("key", "")).split(',') if k.strip()]
            values = [v.strip() for v in str(row.get("value", "")).split(',') if v.strip()]

            for stanza_value in stanza_values:
                # Build the stanza name
                if conf_type == "inputs" and stanza_type == "monitor":
                    stanza = f"monitor://{stanza_value}"
                elif conf_type == "outputs" and stanza_type == "forwarder":
                    stanza = f"tcpout-server://{stanza_value}"
                elif conf_type == "transforms" and stanza_type == "regex":
                    stanza = stanza_value  # e.g., "drop_warns", not a raw regex

                else:
                    stanza = f"{stanza_type}://{stanza_value}"

                if stanza not in stanzas:
                    stanzas[stanza] = {}

                for k, v in zip(keys, values):
                    stanzas[stanza][k] = v

        # Write to conf file
        with open(conf_path, 'w') as f:
            for stanza, kvs in stanzas.items():
                f.write(f"[{stanza}]\n")
                for k, v in kvs.items():
                    f.write(f"{k} = {v}\n")
                f.write("\n")  # Separate stanzas

# Route to handle file browsing and opening
@app.route('/edit/<app_id>/browse', defaults={'folder_path': ''})
@app.route('/edit/<app_id>/browse/<path:folder_path>')
def browse_files(app_id, folder_path):
    app_root = os.path.join('apps', app_id)
    current_folder = os.path.join(app_root, folder_path)

    if not os.path.exists(current_folder):
        flash('Folder not found', 'error')
        return redirect(url_for('index'))

    # Initialize lists for folders and files
    folders = []
    files = []

    # If it's a directory, list the files inside
    if os.path.isdir(current_folder):
        for entry in os.listdir(current_folder):
            full_path = os.path.join(current_folder, entry)
            rel_path = os.path.relpath(full_path, app_root)

            if os.path.isdir(full_path):
                folders.append({'name': entry, 'full_path': rel_path})
            elif os.path.isfile(full_path):
                files.append({'name': entry, 'full_path': rel_path})
    else:
        # If it's a file (like inputs.conf), don't try to list contents, just handle the file
        files.append({'name': os.path.basename(current_folder), 'full_path': folder_path})

    # Handle the case when a file is selected (e.g., inputs.conf)
    selected_file = None
    content = None
    if folder_path and os.path.isfile(current_folder):
        selected_file_path = current_folder
        with open(selected_file_path, 'r') as file:
            content = file.read()
        selected_file = folder_path  # Store the selected file name

    parent_path = os.path.dirname(folder_path) if folder_path else None

    return render_template('s1_editor.html',
                           app_id=app_id,
                           folders=folders,
                           files=files,
                           current_path=folder_path,
                           parent_path=parent_path,
                           selected_file=selected_file,
                           content=content)


@app.route('/')
def home():
    return render_template('s1_index.html')



# @app.route('/create_app', methods=['POST'])
# def create_app():
#     app_name = request.form.get('app_name')
#     index_name = request.form.get('index_name') or request.form.get('new_index_name')
#     me_count = request.form.get('me_count')

#     if not app_name or not index_name:
#         flash('App name and index name are required.', 'error')
#         return redirect(url_for('index'))

#     # If user wants to create a new index, try to create it in Splunk
#     if request.form.get('new_index_name'):
#         success, error = create_splunk_index(index_name)
#         if not success:
#             flash(f"Failed to create index: {error}", 'error')
#             return redirect(url_for('index'))

#     sources = []

#     if me_count is None:
#         flash('Please specify how many sources.', 'error')
#         return redirect(url_for('index'))

#     if me_count.isdigit():
#         count = int(me_count)
#         for i in range(1, count + 1):
#             source_name = request.form.get(f'source{i}_name')
#             log_path = request.form.get(f'source{i}_logpath')
#             if not source_name or not log_path:
#                 flash(f'Missing source name or log path for source {i}.', 'error')
#                 return redirect(url_for('index'))
#             sources.append({'name': source_name.strip(), 'logpath': log_path.strip()})

#     elif me_count == 'more':
#         file = request.files.get('me_file_upload')
#         if not file:
#             flash('Please upload a file with source data.', 'error')
#             return redirect(url_for('index'))

#         filename = file.filename.lower()
#         try:
#             if filename.endswith('.csv'):
#                 file_contents = file.read().decode('utf-8').splitlines()
#                 reader = csv.DictReader(file_contents)
#                 for row in reader:
#                     source_name = row.get('Source Name') or row.get('source_name') or row.get('sourceName')
#                     log_path = row.get('Log Path') or row.get('log_path') or row.get('logPath')
#                     if source_name and log_path:
#                         sources.append({'name': source_name.strip(), 'logpath': log_path.strip()})
#             else:
#                 flash('Unsupported file type. Please upload a CSV file.', 'error')
#                 return redirect(url_for('index'))

#             if not sources:
#                 flash('No valid source data found in the uploaded file.', 'error')
#                 return redirect(url_for('index'))
#         except Exception as e:
#             flash(f'Failed to process uploaded file: {str(e)}', 'error')
#             return redirect(url_for('index'))

#     else:
#         flash('Invalid sources count selection.', 'error')
#         return redirect(url_for('index'))

#     app_id = app_name
#     app_path = os.path.join(APPS_DIR, app_id)

#     create_splunk_app(app_path, app_name, index_name, sources=sources)

#     return redirect(url_for('browse_files', app_id=app_id))


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


# @app.route('/edit/<app_id>/browse', defaults={'folder_path': ''})
# @app.route('/edit/<app_id>/browse/<path:folder_path>')
# def browse_files(app_id, folder_path):
#     app_root = os.path.join(APPS_DIR, app_id)
#     current_folder = os.path.join(app_root, folder_path)

#     if not os.path.exists(current_folder):
#         flash('Folder not found', 'error')
#         return redirect(url_for('index'))

#     folders = []
#     files = []

#     for entry in os.listdir(current_folder):
#         full_path = os.path.join(current_folder, entry)
#         rel_path = os.path.relpath(full_path, app_root)
#         if os.path.isdir(full_path):
#             folders.append({'name': entry, 'full_path': rel_path})
#         else:
#             files.append({'name': entry, 'full_path': rel_path})

#     parent_path = os.path.dirname(folder_path) if folder_path else None

#     return render_template('s1_editor.html',
#                            app_id=app_id,
#                            folders=folders,
#                            files=files,
#                            current_path=folder_path,
#                            parent_path=parent_path,
#                            selected_file=None)
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO
import os, subprocess, smtplib, shutil, secrets
from email.message import EmailMessage
from datetime import datetime

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

APPS_DIR = r'apps'
SPLUNK_DEPLOY_DIR = r'C:\Program Files\Splunk\etc\apps'
SPLUNK_LOG_PATH = r'C:\Program Files\Splunk\var\log\splunk\splunkd.log'

# In-memory state (in production, use DB)
app_states = {}

# ------------------- Workflow Route ----------------------

@app.route('/validate/<app_id>', methods=['GET', 'POST'])
def validation_workflow(app_id):
    stage_raw = request.args.get('stage')
    decision = request.args.get('decision')
    
    try:
        stage = int(stage_raw)
    except (TypeError, ValueError):
        stage = 1

    state = app_states.get(app_id, {'stage': stage, 'decision': decision})
    app_path = os.path.join(APPS_DIR, app_id)

    if stage == 2:
        logs = run_btool_check(app_path)
        state.update({'logs': logs, 'stage': 2})

    elif stage == 3:
        logs = send_email_notification(app_id)
        state.update({
            'logs': logs + "\n⏳ Awaiting approver action...",
            'stage': 4,
            'decision': None,
            'decision_time': None
        })

    elif stage == 4:
        if decision == "approve":
            logs = deploy_splunk_app(app_id, app_path)
            state.update({
                'logs': logs,
                'decision': 'approve',
                'stage': 4,
                'decision_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        elif decision == "reject":
            logs = "Deployment rejected."
            state.update({
                'logs': logs,
                'decision': 'reject',
                'stage': 4,
                'decision_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            state.update({'logs': "⏳ Waiting for approver to take action...", 'stage': 4})

    elif stage == 5:
        logs = get_internal_logs()
        state.update({'logs': logs, 'stage': 5})

    else:
        state.update({'logs': "Unknown stage.", 'stage': stage})

    app_states[app_id] = state

    return render_template(
        's1_flow.html',
        app_id=app_id,
        btool_logs=state['logs'],
        stage=state['stage'],
        decision=state.get('decision'),
        decision_time=state.get('decision_time'),
        reason=state.get('reason'),
        schedule_info=state.get('schedule_info'),
        enumerate=enumerate
    )


# ------------------ Schedule Deployment ------------------

@app.route('/schedule/<app_id>', methods=['POST'])
def schedule_deployment(app_id):
    deploy_datetime = request.form.get('deploy_datetime')
    if not deploy_datetime:
        flash("Please select a date and time to schedule the deployment.", "danger")
        return redirect(url_for('validation_workflow', app_id=app_id, stage=4, decision='approve'))

    app_states[app_id]['schedule_info'] = deploy_datetime
    flash(f"Deployment for {app_id} scheduled at {deploy_datetime}", "success")
    return redirect(url_for('validation_workflow', app_id=app_id, stage=5))


# ------------------ Email Approval ------------------------

@app.route('/approve/<app_id>')
def approve_from_email(app_id):
    token = request.args.get('token')
    state = app_states.get(app_id)

    if not state or token != state.get('token') or state.get('used'):
        return "<h3>🔒 Link used or invalid.</h3>"

    app_path = os.path.join(APPS_DIR, app_id)
    logs = deploy_splunk_app(app_id, app_path)

    state.update({
        'decision': 'approve',
        'logs': logs,
        'stage': 5,
        'used': True,
        'decision_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    socketio.emit('decision_update', {'app_id': app_id, 'decision': 'approve'})
    return "<h3>✅ Approved. You may close this window.</h3>"


@app.route('/reject/<app_id>', methods=['GET', 'POST'])
def reject_from_email(app_id):
    token = request.args.get('token')
    state = app_states.get(app_id)

    if not state or token != state.get('token') or state.get('used'):
        return "<h3>🔒 Link used or invalid.</h3>"

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        if not reason:
            return "<h3>⚠️ Reason required.</h3>"

        state.update({
            'decision': 'reject',
            'logs': f"Deployment rejected. Reason: {reason}",
            'reason': reason,
            'stage': 5,
            'used': True,
            'decision_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        socketio.emit('decision_update', {'app_id': app_id, 'decision': 'reject'})
        return f"<h3>❌ Rejected: {reason}</h3>"

    return f"""
    <h3>Reject App '{app_id}'</h3>
    <form method="post">
        <label>Reason for rejection:</label><br>
        <textarea name="reason" required></textarea><br><br>
        <button type="submit">Submit</button>
    </form>
    """


# ------------------ Supporting Functions ------------------

def send_email_notification(app_id):
    try:
        token = secrets.token_urlsafe(16)
        state = app_states.setdefault(app_id, {'stage': 3, 'logs': '', 'decision': None})
        state.update({'token': token, 'used': False})

        approve_url = f"http://127.0.0.1:5000/approve/{app_id}?token={token}"
        reject_url = f"http://127.0.0.1:5000/reject/{app_id}?token={token}"

        html_content = f"""
        <h2>🚀 Splunk App '{app_id}' - Approval Needed</h2>
        <p><a href="{approve_url}">✅ Approve</a> | <a href="{reject_url}">❌ Reject</a></p>
        """

        msg = EmailMessage()
        msg['Subject'] = f'Splunk App {app_id} - Approval Needed'
        msg['From'] = 'yaswanthkumarch2001@gmail.com'
        msg['To'] = 'Yaswanth@middlewaretalents.com'
        msg.set_content("Use a browser that supports HTML.")
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('yaswanthkumarch2001@gmail.com', 'uqjc bszf djfw bsor')  # App password only!
            server.send_message(msg)

        return "✅ Email sent."
    except Exception as e:
        return f"❌ Email failed: {str(e)}"


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
                    cmd = [r'C:\Program Files\Splunk\bin\splunk.exe', 'btool', conf_name, 'list', '--debug', f'--app={app_name}']
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    output += f"=== {conf_name}.conf ===\n"
                    output += result.stdout if result.returncode == 0 else result.stderr
                    output += "\n\n"
                except Exception as e:
                    output += f"Error running btool for {conf_name}: {str(e)}\n\n"
    return output.strip()


def deploy_splunk_app(app_id, app_path):
    try:
        dest_path = os.path.join(SPLUNK_DEPLOY_DIR, app_id)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(app_path, dest_path)
        return f"✅ App '{app_id}' deployed successfully."
    except Exception as e:
        return f"❌ Deployment failed: {str(e)}"


def get_internal_logs():
    try:
        with open(SPLUNK_LOG_PATH, 'r') as f:
            return f.read()[-3000:]
    except Exception as e:
        return f"❌ Could not read internal logs: {str(e)}"




# Optional: dummy routes for home and file browser


# @app.route('/browse/<app_id>')
# def browse_files(app_id):
#     return f"📁 File browser for app: {app_id}"




# @app.route('/edit/<app_id>/<path:file_path>', methods=['GET', 'POST'])
# def edit_file(app_id, file_path):
#     file_path = file_path.replace("\\", "/")
#     full_path = os.path.join(APPS_DIR, app_id, file_path)

#     if not os.path.exists(full_path):
#         flash('File not found', 'error')
#         return redirect(url_for('browse_files', app_id=app_id, folder_path=os.path.dirname(file_path)))

#     validation_message = None
#     recommendations = []

#     if request.method == 'POST':
#         content = request.form['content']

#         if full_path.endswith('.conf'):
#             is_valid, validation_message = is_valid_splunk_conf(content)
#             if not is_valid:
#                 flash(validation_message, 'error')
#                 return redirect(url_for('edit_file', app_id=app_id, file_path=file_path))

#         save_file(full_path, content)
#         flash('File saved successfully!', 'success')
#         return redirect(url_for('s1_flow', app_id=app_id))

#     with open(full_path, 'r', encoding='utf-8') as f:
#         content = f.read()

#     if os.path.basename(full_path) == 'inputs.conf':
#         if '[monitor://' not in content:
#             recommendations.append("⚠️ You haven't defined any `[monitor://...]` stanzas.")
#         if 'index =' not in content:
#             recommendations.append("💡 Add `index = your_index_name` to send data to a Splunk index.")
#         if 'disabled = 0' not in content:
#             recommendations.append("📝 Use `disabled = 0` to ensure the input is enabled.")

#     mode = request.args.get('mode', 'read')
#     read_only = (mode != 'edit')

#     app_root = os.path.join(APPS_DIR, app_id)
#     current_path = os.path.dirname(file_path)
#     parent_path = os.path.dirname(current_path) if current_path else None

#     folders, files = [], []
#     current_folder = os.path.join(app_root, current_path)
#     for entry in os.listdir(current_folder):
#         full_entry_path = os.path.join(current_folder, entry)
#         rel_path = os.path.relpath(full_entry_path, app_root)
#         if os.path.isdir(full_entry_path):
#             folders.append({'name': entry, 'full_path': rel_path})
#         else:
#             files.append({'name': entry, 'full_path': rel_path})

#     return render_template('s1_editor.html',
#                            app_id=app_id,
#                            selected_file=file_path,
#                            content=content,
#                            read_only=read_only,
#                            current_path=current_path,
#                            parent_path=parent_path,
#                            folders=folders,
#                            files=files,
#                            validation_message=validation_message,
#                            recommendations=recommendations)
# @app.route('/s1_flow/<app_id>')
# def s1_flow(app_id):
#     return render_template('s1_flow.html', app_id=app_id)

import posixpath

@app.route('/edit/<app_id>/<path:file_path>', methods=['GET', 'POST'])
def edit_file(app_id, file_path):
    file_path = file_path.replace("\\", "/")
    file_path = posixpath.normpath(file_path)

    full_path = os.path.abspath(os.path.join(APPS_DIR, app_id, file_path))
    app_root = os.path.abspath(os.path.join(APPS_DIR, app_id))

    if not full_path.startswith(app_root):
        flash("Access denied", "error")
        return redirect(url_for('browse_files', app_id=app_id))

    if not os.path.exists(full_path):
        flash('File not found', 'error')
        folder_path = posixpath.dirname(file_path)
        return redirect(url_for('browse_files', app_id=app_id, folder_path=folder_path))

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

        # ✅ Correct redirect
        return redirect(url_for('s1_flow', app_id=app_id))

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if os.path.basename(full_path) == 'inputs.conf':
        if '[monitor://' not in content:
            recommendations.append("⚠️ You haven't defined any `[monitor://...]` stanzas.")
        if 'index =' not in content:
            recommendations.append("💡 Add `index = your_index_name` to send data to a Splunk index.")
        if 'disabled = 0' not in content:
            recommendations.append("📝 Use `disabled = 0` to ensure the input is enabled.")

    current_path = posixpath.dirname(file_path)
    parent_path = posixpath.dirname(current_path) if current_path else None

    folders, files = [], []
    current_folder = os.path.join(app_root, current_path.replace("/", os.sep))
    for entry in os.listdir(current_folder):
        full_entry_path = os.path.join(current_folder, entry)
        rel_path = os.path.relpath(full_entry_path, app_root).replace("\\", "/")
        if os.path.isdir(full_entry_path):
            folders.append({'name': entry, 'full_path': rel_path})
        else:
            files.append({'name': entry, 'full_path': rel_path})

    return render_template('s1_editor.html',
                           app_id=app_id,
                           selected_file=file_path,
                           content=content,
                           read_only=(request.args.get('mode', 'read') != 'edit'),
                           current_path=current_path,
                           parent_path=parent_path,
                           folders=folders,
                           files=files,
                           validation_message=validation_message,
                           recommendations=recommendations)

# ✅ FIXED: This no longer redirects to itself
@app.route('/s1_flow/<app_id>')
def s1_flow(app_id):
    return render_template('s1_flow.html', app_id=app_id, stage=1, btool_logs=None)




@app.route('/download/<app_id>')
def download_app(app_id):
    app_path = os.path.join(APPS_DIR, app_id)
    zip_path = os.path.join(UPLOADS_DIR, f'{app_id}.zip')

    if os.path.exists(zip_path):
        os.remove(zip_path)

    rezip_app(app_path, zip_path)

    return send_file(zip_path, as_attachment=True)


if __name__ == '__main__':
    # app.run(debug=True, port=5000)
    socketio.run(app, debug=True ,port=5000)
