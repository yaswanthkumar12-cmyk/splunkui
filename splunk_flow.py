from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store the workflow state server-side per session or global (simplified here)
workflow_state = {
    'uploaded': False,
    'validated': False,
    'email_sent': False,
    'approval': None,  # 'approved' or 'rejected'
    'deployed': False,
    'monitoring': False,
}

def simulate_long_task(logs, delay=1):
    """Helper to simulate task steps with logs and delay."""
    for i, msg in enumerate(logs, 1):
        time.sleep(delay)
        socketio.emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]})

@app.route('/')
def index():
    return render_template('splunk_flow.html')

@socketio.on('stage_action')
def handle_stage_action(data):
    stage = data.get('stage')
    action = data.get('action')
    logs = []
    
    # For concurrency, run time-consuming tasks in a separate thread so we don't block the server
    def process_action():
        nonlocal logs
        # Stage 1: Upload
        if stage == 1 and action == 'upload':
            if not workflow_state['uploaded']:
                logs = ["Uploading app file...", "Upload complete."]
                for i, msg in enumerate(logs, 1):
                    time.sleep(1)
                    emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]}, broadcast=False)
                workflow_state['uploaded'] = True
            else:
                emit('stage_response', {'success': False, 'message': 'Already uploaded.'}, broadcast=False)
        
        # Stage 2: Validate
        elif stage == 2 and action == 'validate':
            if workflow_state['uploaded'] and not workflow_state['validated']:
                logs = ["Starting validation...", "Validation complete."]
                for i, msg in enumerate(logs, 1):
                    time.sleep(1)
                    emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]}, broadcast=False)
                workflow_state['validated'] = True
            else:
                emit('stage_response', {'success': False, 'message': 'Validation not allowed yet or already done.'}, broadcast=False)
        
        # Stage 3: Send Email
        elif stage == 3 and action == 'send_email':
            if workflow_state['validated'] and not workflow_state['email_sent']:
                logs = ["Composing email...", "Sending email..."]
                for i, msg in enumerate(logs, 1):
                    time.sleep(1)
                    emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]}, broadcast=False)
                workflow_state['email_sent'] = True
                # Notify frontend to show approval buttons
                emit('approval_required', {'message': 'Approval required from manager.', 'logs': logs}, broadcast=False)
            else:
                emit('stage_response', {'success': False, 'message': 'Cannot send email yet or already sent.'}, broadcast=False)

        # Stage 4: Approve / Reject
        elif stage == 4 and action in ('approve', 'reject'):
            if workflow_state['email_sent'] and workflow_state['approval'] is None:
                if action == 'approve':
                    workflow_state['approval'] = 'approved'
                    emit('approval_update', {'approval': 'approved', 'logs': ['Manager approved the app.']}, broadcast=False)
                else:
                    workflow_state['approval'] = 'rejected'
                    emit('approval_update', {'approval': 'rejected', 'logs': ['Manager rejected the app.']}, broadcast=False)
            else:
                emit('stage_response', {'success': False, 'message': 'Approval already done or not required.'}, broadcast=False)

        # Stage 5: Deploy
        elif stage == 5 and action == 'deploy':
            if workflow_state['approval'] == 'approved' and not workflow_state['deployed']:
                logs = ["Deploying app...", "Deployment complete."]
                for i, msg in enumerate(logs, 1):
                    time.sleep(1)
                    emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]}, broadcast=False)
                workflow_state['deployed'] = True
            else:
                emit('stage_response', {'success': False, 'message': 'Cannot deploy yet or already deployed.'}, broadcast=False)

        # Stage 6: Monitor
        elif stage == 6 and action == 'monitor':
            if workflow_state['deployed'] and not workflow_state['monitoring']:
                logs = ["Starting monitoring...", "Monitoring active."]
                for i, msg in enumerate(logs, 1):
                    time.sleep(1)
                    emit('stage_response', {'success': True, 'message': msg, 'logs': logs[:i]}, broadcast=False)
                workflow_state['monitoring'] = True
            else:
                emit('stage_response', {'success': False, 'message': 'Cannot start monitoring yet or already started.'}, broadcast=False)

        else:
            emit('stage_response', {'success': False, 'message': 'Invalid stage or action.'}, broadcast=False)

    # Run process_action in a thread to avoid blocking
    threading.Thread(target=process_action).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
