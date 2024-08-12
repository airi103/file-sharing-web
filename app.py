from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
import time
import threading
import mimetypes
import argparse
import uuid
from PIL import Image
import io

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
THUMBNAIL_FOLDER = 'thumbnails'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(THUMBNAIL_FOLDER):
    os.makedirs(THUMBNAIL_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16 GB

file_expiration = {}
file_metadata = {}

def cleanup_files():
    while True:
        current_time = time.time()
        files_to_delete = []
        for file_id, expiration_time in file_expiration.items():
            if current_time > expiration_time:
                files_to_delete.append(file_id)
        
        for file_id in files_to_delete:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_metadata[file_id]['filename'])
            thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], f"{file_id}_thumb.jpg")
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            del file_expiration[file_id]
            del file_metadata[file_id]
        
        time.sleep(60)  # Check every minute

cleanup_thread = threading.Thread(target=cleanup_files)
cleanup_thread.daemon = True
cleanup_thread.start()

def generate_thumbnail(file_path, file_id):
    try:
        with Image.open(file_path) as img:
            img.thumbnail((400, 400))
            thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], f"{file_id}_thumb.jpg")
            img.save(thumbnail_path, "JPEG")
            return thumbnail_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = file.filename
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        file.save(file_path)
        expiration = int(request.form.get('expiration', 3600))  # Default to 1 hour
        file_expiration[file_id] = time.time() + expiration
        mime_type, _ = mimetypes.guess_type(filename)
        thumbnail_path = None
        if mime_type and mime_type.startswith('image/'):
            thumbnail_path = generate_thumbnail(file_path, file_id)
        file_metadata[file_id] = {
            'filename': filename,
            'size': os.path.getsize(file_path),
            'type': mime_type or 'application/octet-stream',
            'thumbnail': thumbnail_path
        }
        return jsonify({'message': 'File uploaded successfully', 'id': file_id}), 200

@app.route('/files')
def list_files():
    files = []
    for file_id, metadata in file_metadata.items():
        files.append({
            'id': file_id,
            'name': metadata['filename'],
            'size': metadata['size'],
            'type': metadata['type'],
            'thumbnail': url_for('get_thumbnail', file_id=file_id) if metadata['thumbnail'] else None
        })
    return jsonify(files)

@app.route('/share/<file_id>')
def share_file(file_id):
    if file_id in file_metadata:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        return send_file(file_path, mimetype=file_metadata[file_id]['type'])
    return jsonify({'error': 'File not found'}), 404

@app.route('/thumbnail/<file_id>')
def get_thumbnail(file_id):
    if file_id in file_metadata and file_metadata[file_id]['thumbnail']:
        return send_file(file_metadata[file_id]['thumbnail'], mimetype='image/jpeg')
    return jsonify({'error': 'Thumbnail not found'}), 404

@app.route('/preview/<file_id>')
def preview_file(file_id):
    if file_id in file_metadata:
        file_metadata_item = file_metadata[file_id]
        file_url = url_for('share_file', file_id=file_id, _external=True)
        image_url = file_url if file_metadata_item['type'].startswith('image/') else None
        thumbnail_url = url_for('get_thumbnail', file_id=file_id, _external=True) if file_metadata_item['thumbnail'] else None
        return render_template('share.html', file_id=file_id, file_metadata=file_metadata_item, file_url=file_url, image_url=image_url, thumbnail_url=thumbnail_url)
    return jsonify({'error': 'File not found'}), 404

@app.route('/storage-info')
def get_storage_info():
    total_size = 0
    for root, dirs, files in os.walk(UPLOAD_FOLDER):
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    return jsonify({'used': total_size})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A yet another file sharing platform")
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on')
    args = parser.parse_args()

    print(f"Starting server on {args.host}:{args.port}")
    app.run(debug=True, host=args.host, port=args.port)
