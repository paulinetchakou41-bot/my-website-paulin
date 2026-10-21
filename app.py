import os
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_ultra_secret_key'
socketio = SocketIO(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- IN-MEMORY STORAGE (Simulates a database) ---
# Format: {'session_id': {'username': '...', 'avatar': '...'}}
users = {}
# Format: ['General', 'Developers', 'Hobbies']
groups = ["General"]


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    return render_template('index.html')


# --- PROFILE & CONNECTION MANAGEMENT ---
@socketio.on('set_profile')
def handle_set_profile(data):
    """Saves the user's username and avatar URL for their active session."""
    users[request.sid] = {
        'username': data.get('username', 'Anonymous'),
        'avatar': data.get('avatar', '/uploads/default_avatar.png')  # Default image placeholder
    }
    # Automatically join the main group on connection
    join_room("General")
    emit('profile_updated', {'success': True, 'groups': groups})


# --- GROUP MANAGEMENT ---
@socketio.on('create_group')
def handle_create_group(data):
    """Creates a new group chat and notifies all connected users."""
    group_name = data.get('group_name', '').strip()
    if group_name and group_name not in groups:
        groups.append(group_name)
        # Broadcast the updated group list to everyone
        emit('group_list_updated', groups, broadcast=True)


@socketio.on('join_group')
def handle_join_group(data):
    """Handles switching between group channels."""
    old_group = data.get('old_group')
    new_group = data.get('new_group')

    if old_group:
        leave_room(old_group)

    if new_group in groups:
        join_room(new_group)
        emit('joined_group', {'group': new_group})


# --- GROUP-TARGETED MESSAGING ---
@socketio.on('send_message')
def handle_message(data):
    """Sends a message strictly to the members of the specified group room."""
    group = data.get('group', 'General')
    user_info = users.get(request.sid, {'username': 'Anonymous', 'avatar': ''})

    payload = {
        'username': user_info['username'],
        'avatar': user_info['avatar'],
        'msg': data.get('msg')
    }
    # Targeted delivery using SocketIO room filtering
    emit('new_message', payload, to=group)


# --- FILE UPLOADS (For Profile Avatars or Media Messages) ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_url = url_for('uploaded_file', filename=filename)

        return jsonify({'success': True, 'url': file_url}), 200

if __name__ == '__main__':
    # Remplacer socketio.run(app, debug=True) par :
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)