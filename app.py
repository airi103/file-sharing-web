from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
import time
import threading
import mimetypes
import argparse
import uuid
from PIL import Image
from collections import OrderedDict

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
THUMBNAIL_FOLDER = 'thumbnails'
THUMBNAIL_SIZE = (400, 400)
CLEANUP_INTERVAL = 60
MAX_CACHE_SIZE = 1000

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16 GB

file_expiration = OrderedDict()
file_metadata = OrderedDict()

def cleanup_files():
    while True:
        current_time = time.time()
        expired_files = [file_id for file_id, exp_time in file_expiration.items() if current_time > exp_time]
        
        for file_id in expired_files:
            delete_file(file_id)

        while len(file_metadata) > MAX_CACHE_SIZE:
            delete_file(next(iter(file_metadata)))

        time.sleep(CLEANUP_INTERVAL)

def delete_file(file_id):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
    thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], f"{file_id}_thumb.jpg")
    
    try:
        os.remove(file_path)
    except OSError:
        pass
    try:
        os.remove(thumbnail_path)
    except OSError:
        pass
    
    file_expiration.pop(file_id, None)
    file_metadata.pop(file_id, None)

cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

def generate_thumbnail(file_path, file_id):
    try:
        with Image.open(file_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], f"{file_id}_thumb.jpg")
            img.convert("RGB").save(thumbnail_path, "JPEG", quality=85, optimize=True)
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
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
    file.save(file_path)
    
    expiration = int(request.form.get('expiration', 3600))
    file_expiration[file_id] = time.time() + expiration
    
    mime_type, _ = mimetypes.guess_type(file.filename)
    thumbnail_path = generate_thumbnail(file_path, file_id) if mime_type and mime_type.startswith('image/') else None
    
    file_metadata[file_id] = {
        'filename': file.filename,
        'size': os.path.getsize(file_path),
        'type': mime_type or 'application/octet-stream',
        'thumbnail': thumbnail_path
    }
    
    return jsonify({'message': 'File uploaded successfully', 'id': file_id}), 200

@app.route('/files')
def list_files():
    return jsonify([
        {
            'id': file_id,
            'name': metadata['filename'],
            'size': metadata['size'],
            'type': metadata['type'],
            'thumbnail': url_for('get_thumbnail', file_id=file_id) if metadata['thumbnail'] else None
        } for file_id, metadata in file_metadata.items()
    ])

@app.route('/share/<file_id>')
def share_file(file_id):
    if file_id in file_metadata:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype=file_metadata[file_id]['type'])
        delete_file(file_id)
    return jsonify({'error': 'File not found'}), 404

@app.route('/thumbnail/<file_id>')
def get_thumbnail(file_id):
    if file_id in file_metadata and file_metadata[file_id]['thumbnail']:
        thumbnail_path = file_metadata[file_id]['thumbnail']
        if os.path.exists(thumbnail_path):
            return send_file(thumbnail_path, mimetype='image/jpeg')
        file_metadata[file_id]['thumbnail'] = None
    return jsonify({'error': 'Thumbnail not found'}), 404

@app.route('/preview/<file_id>')
def preview_file(file_id):
    if file_id in file_metadata:
        metadata = file_metadata[file_id]
        file_url = url_for('share_file', file_id=file_id, _external=True)
        image_url = file_url if metadata['type'].startswith('image/') else None
        thumbnail_url = url_for('get_thumbnail', file_id=file_id, _external=True) if metadata['thumbnail'] else None
        return render_template('share.html', file_id=file_id, file_metadata=metadata, file_url=file_url, image_url=image_url, thumbnail_url=thumbnail_url)
    return jsonify({'error': 'File not found'}), 404

@app.route('/storage-info')
def get_storage_info():
    total_size = sum(os.path.getsize(os.path.join(root, file)) 
                     for root, _, files in os.walk(UPLOAD_FOLDER) 
                     for file in files)
    return jsonify({'used': total_size})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="File Sharing Application")
    parser.add_argument('--port', type=int, default=9145, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on')
    args = parser.parse_args()

    print(f"Starting server on {args.host}:{args.port}")
    app.run(debug=True, host=args.host, port=args.port)
