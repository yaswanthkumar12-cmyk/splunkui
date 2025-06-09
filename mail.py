# from flask import Flask, render_template, request
# from flask_socketio import SocketIO, emit
# import smtplib
# from email.mime.text import MIMEText
# import uuid

# app = Flask(__name__)
# socketio = SocketIO(app)
# status = {"stage": "pending"}
# valid_tokens = set()  # Store valid unused tokens

# EMAIL_USER = "yaswanthkumarch2001@gmail.com"
# EMAIL_PASS = "uqjc bszf djfw bsor"
# TO_EMAIL = "Yaswanth@middlewaretalents.com"

# @app.route('/')
# def index():
#     return render_template("email.html", status=status["stage"])

# @app.route('/email_response')
# def email_response():
#     action = request.args.get('action')
#     token = request.args.get('token')

#     if token not in valid_tokens:
#         return "This action link is invalid or already used.", 400

#     if action == 'approve':
#         status["stage"] = "approved"
#     elif action == 'reject':
#         status["stage"] = "rejected"
#     else:
#         return "Invalid action", 400

#     # Mark token as used
#     valid_tokens.remove(token)

#     # Emit status update
#     socketio.emit('status_update', {'status': status["stage"]})

  
  

  

# @socketio.on('send_email')
# def handle_send_email():
#     if status["stage"] != "pending":
#         emit('status_update', {'status': status["stage"]})
#         return

#     # Generate a unique token
#     token = str(uuid.uuid4())
#     valid_tokens.add(token)

#     # Build email with the token embedded in URLs
#     html = f"""
#     <p>This is a test email from Flask with action buttons.</p>
#     <p>Click one of the options:</p>
#     <a href="http://localhost:5000/email_response?action=approve&token={token}"
#        style="padding:10px 20px;background:#28a745;color:#fff;text-decoration:none;border-radius:5px;">
#        Approve</a>
#     &nbsp;
#     <a href="http://localhost:5000/email_response?action=reject&token={token}"
#        style="padding:10px 20px;background:#dc3545;color:#fff;text-decoration:none;border-radius:5px;">
#        Reject</a>
#     """

#     msg = MIMEText(html, 'html')
#     msg['Subject'] = 'Flask Email with Actions'
#     msg['From'] = EMAIL_USER
#     msg['To'] = TO_EMAIL

#     try:
#         with smtplib.SMTP("smtp.gmail.com", 587) as server:
#             server.starttls()
#             server.login(EMAIL_USER, EMAIL_PASS)
#             server.send_message(msg)

#         status["stage"] = "email_sent"
#         emit('status_update', {'status': status["stage"]}, broadcast=True)

#     except Exception as e:
#         emit('status_update', {'status': f"error: {str(e)}"}, broadcast=True)

# if __name__ == '__main__':
#     socketio.run(app, host="0.0.0.0", port=5000, debug=True)











from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import smtplib
from email.mime.text import MIMEText
import uuid
import threading
import socket
import time

app = Flask(__name__)
socketio = SocketIO(app)
status = {"stage": "pending"}
valid_tokens = set()

EMAIL_USER = "yaswanthkumarch2001@gmail.com"
EMAIL_PASS = "uqjc bszf djfw bsor"
TO_EMAIL = "Yaswanth@middlewaretalents.com"
TEAM_EMAIL = "team@middlewaretalents.com"  # For rejection warnings

# --- Placeholder functions ---

def upload_to_github():
    # Your GitHub upload logic here (use PyGithub or git CLI commands)
    print("[INFO] Uploading code to GitHub...")
    time.sleep(2)  # Simulate time delay
    print("[INFO] Upload complete.")

def schedule_deployment():
    # Your deployment scheduler logic here (could be via cron, APScheduler, external service)
    print("[INFO] Scheduling deployment...")
    time.sleep(2)  # Simulate scheduling delay
    print("[INFO] Deployment scheduled.")

def monitor_deployment():
    # Your deployment monitoring logic here
    print("[INFO] Monitoring deployment...")
    time.sleep(5)  # Simulate monitoring delay
    print("[INFO] Deployment success.")

def send_rejection_warning():
    html = "<p>The deployment request was rejected.</p>"
    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Deployment Request Rejected'
    msg['From'] = EMAIL_USER
    msg['To'] = TEAM_EMAIL
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("[INFO] Rejection warning email sent to team.")
    except Exception as e:
        print("[ERROR] Sending rejection warning failed:", e)

# --- Flask routes and socket handlers ---

@app.route('/')
def index():
    return render_template("email.html", status=status["stage"])

@app.route('/email_response')
def email_response():
    action = request.args.get('action')
    token = request.args.get('token')

    if token not in valid_tokens:
        return "This action link is invalid or already used.", 400

    valid_tokens.remove(token)  # Mark token used

    if action == 'approve':
        status["stage"] = "approved"
        socketio.emit('status_update', {'status': status["stage"]})

        # Run deploy flow in background
        threading.Thread(target=deploy_flow).start()

        return "Thank you, you have APPROVED the request."

    elif action == 'reject':
        status["stage"] = "rejected"
        socketio.emit('status_update', {'status': status["stage"]})

        # Send rejection warning email async
        threading.Thread(target=send_rejection_warning).start()

        return "Thank you, you have REJECTED the request."

    else:
        return "Invalid action", 400

@socketio.on('send_email')
def handle_send_email():
    if status["stage"] != "pending":
        emit('status_update', {'status': status["stage"]})
        return

    token = str(uuid.uuid4())
    valid_tokens.add(token)

    html = f"""
    <p>This is a test email from Flask with action buttons.</p>
    <p>Click one of the options:</p>
    <a href="http://localhost:5000/email_response?action=approve&token={token}"
       style="padding:10px 20px;background:#28a745;color:#fff;text-decoration:none;border-radius:5px;">
       Approve</a>
    &nbsp;
    <a href="http://localhost:5000/email_response?action=reject&token={token}"
       style="padding:10px 20px;background:#dc3545;color:#fff;text-decoration:none;border-radius:5px;">
       Reject</a>
    """

    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Flask Email with Actions'
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        status["stage"] = "email_sent"
        emit('status_update', {'status': status["stage"]}, broadcast=True)

    except Exception as e:
        emit('status_update', {'status': f"error: {str(e)}"}, broadcast=True)

def deploy_flow():
    """Runs after approval: upload, schedule, monitor, update status."""
    try:
        socketio.emit('status_update', {'status': 'uploading_to_github'})
        upload_to_github()

        socketio.emit('status_update', {'status': 'scheduling_deployment'})
        schedule_deployment()

        socketio.emit('status_update', {'status': 'monitoring_deployment'})
        monitor_deployment()

        status["stage"] = "deployed"
        socketio.emit('status_update', {'status': status["stage"]})

    except Exception as e:
        status["stage"] = "error_in_deployment"
        socketio.emit('status_update', {'status': f"error: {str(e)}"})

# --- UDP Listener ---

def udp_listener():
    UDP_IP = "0.0.0.0"
    UDP_PORT = 9999
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"UDP server listening on {UDP_IP}:{UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        print(f"Received UDP message: {message} from {addr}")
        socketio.emit('udp_message', {'message': message})

if __name__ == '__main__':
    # Start UDP listener thread
    udp_thread = threading.Thread(target=udp_listener)
    udp_thread.daemon = True
    udp_thread.start()

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
