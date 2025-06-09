from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import smtplib
from email.mime.text import MIMEText
import uuid
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

status = {"stage": "pending"}
valid_tokens = set()

EMAIL_USER = "yaswanthkumarch2001@gmail.com"
EMAIL_PASS = "uqjc bszf djfw bsor"
TO_EMAIL = "Yaswanth@middlewaretalents.com"
TEAM_EMAIL = "team@middlewaretalents.com"

def upload_to_github():
    print("Uploading to GitHub...")
    time.sleep(2)

def monitor_deployment():
    print("Monitoring deployment...")
    time.sleep(3)

def send_rejection_warning():
    html = "<p>The deployment request was <strong>REJECTED</strong>.</p>"
    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Deployment Request Rejected'
    msg['From'] = EMAIL_USER
    msg['To'] = TEAM_EMAIL
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("Rejection email sent.")
    except Exception as e:
        print("Rejection email failed:", e)

def deploy_flow():
    try:
        status["stage"] = "uploading"
        socketio.emit('status_update', {'status': 'uploading'})
        upload_to_github()

        status["stage"] = "awaiting_schedule_confirmation"
        socketio.emit('status_update', {'status': 'awaiting_schedule_confirmation'})
        print("Awaiting user schedule confirmation...")

    except Exception as e:
        status["stage"] = "error"
        socketio.emit('status_update', {'status': f"error: {str(e)}"})

@app.route('/')
def index():
    return render_template("email_templet.html", status=status["stage"])

@app.route('/email_response')
def email_response():
    action = request.args.get('action')
    token = request.args.get('token')

    if token not in valid_tokens:
        return "Invalid or expired token.", 400

    valid_tokens.remove(token)

    if action == 'approve':
        status["stage"] = "approved"
        socketio.emit('status_update', {'status': 'approved'})
        threading.Thread(target=deploy_flow, daemon=True).start()
        return "You approved the deployment."

    elif action == 'reject':
        status["stage"] = "rejected"
        socketio.emit('status_update', {'status': 'rejected'})
        threading.Thread(target=send_rejection_warning, daemon=True).start()
        return "You rejected the deployment."

    return "Invalid action", 400

@socketio.on('send_email')
def handle_send_email():
    if status["stage"] != "pending":
        emit('status_update', {'status': status["stage"]})
        return

    token = str(uuid.uuid4())
    valid_tokens.add(token)

    html = f"""
    <p>A deployment request needs your review.</p>
    <p>Click one:</p>
    <a href="http://localhost:5000/email_response?action=approve&token={token}"
       style="padding:10px 20px;background:#28a745;color:#fff;text-decoration:none;border-radius:5px;">
       Approve</a>
    &nbsp;
    <a href="http://localhost:5000/email_response?action=reject&token={token}"
       style="padding:10px 20px;background:#dc3545;color:#fff;text-decoration:none;border-radius:5px;">
       Reject</a>
    """

    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Deployment Approval Required'
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        status["stage"] = "email_sent"
        emit('status_update', {'status': 'email_sent'})

    except Exception as e:
        emit('status_update', {'status': f"error: {str(e)}"})

def schedule_deployment(scheduled_timestamp):
    try:
        now = time.time()
        wait_seconds = max(0, scheduled_timestamp - now)
        print(f"Waiting {wait_seconds:.2f} seconds until scheduled deployment...")

        socketio.emit('status_update', {
            'status': 'schedule',
            'scheduled_time': scheduled_timestamp
        })

        time.sleep(wait_seconds)

        socketio.emit('status_update', {'status': 'monitor'})
        monitor_deployment()

        status["stage"] = "deployed"
        socketio.emit('status_update', {'status': 'deployed'})

    except Exception as e:
        socketio.emit('status_update', {'status': f"error: {str(e)}"})

@socketio.on('confirm_schedule')
def handle_confirm_schedule(data):
    scheduled_timestamp = data.get('scheduled_time')
    if not scheduled_timestamp:
        emit('status_update', {'status': 'error', 'message': 'No scheduled_time provided'})
        return

    try:
        scheduled_timestamp = float(scheduled_timestamp)
    except ValueError:
        emit('status_update', {'status': 'error', 'message': 'Invalid scheduled_time format'})
        return

    status["stage"] = "schedule"
    threading.Thread(target=schedule_deployment, args=(scheduled_timestamp,), daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
