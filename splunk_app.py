from flask import Flask, render_template, request, jsonify
import splunklib.client as client

app = Flask(__name__)

# Splunk Connection Settings
SPLUNK_HOST = "127.0.0.1"
SPLUNK_PORT = 8089
SPLUNK_USERNAME = "MTL1013"
SPLUNK_PASSWORD = "MTL@1013"

def get_splunk_service():
    return client.connect(
        host=SPLUNK_HOST,
        port=SPLUNK_PORT,
        username=SPLUNK_USERNAME,
        password=SPLUNK_PASSWORD
    )

@app.route('/')
def index_page():
    return render_template("delete_index.html")

@app.route('/splunk_indexes', methods=['GET'])
def list_indexes():
    try:
        service = get_splunk_service()
        index_names = [index.name for index in service.indexes]
        return jsonify(index_names)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/delete_index', methods=['POST'])
def delete_index():
    index_name = request.form.get('index_name')
    if not index_name:
        return jsonify({'status': 'error', 'message': 'Index name is required'}), 400
    try:
        service = get_splunk_service()
        if index_name in service.indexes:
            index = service.indexes[index_name]

            # If index is disabled, enable it before deletion
            try:
                index.enable()
            except Exception as enable_err:
                # If it's already enabled, it might raise an exception — ignore it
                pass

            index.delete()
            return jsonify({'status': 'success', 'message': f'Index \"{index_name}\" deleted successfully.'})
        else:
            return jsonify({'status': 'error', 'message': 'Index not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
