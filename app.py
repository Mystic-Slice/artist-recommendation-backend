from utility import determine_media_type
from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from config import Config
from kindo_api import KindoAPI
from firebase_handler import FirebaseHandler
from werkzeug.utils import secure_filename
import os
import time
import re
import threading
import uuid

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = './tmp'
app.config["MONGO_URI"] = Config.MONGO_URI

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

firebase_cred_path = "artist-recommendation-key.json"
firebase_bucket_name = "artist-recommendation.firebase.app"

# Initialize KindoAPI
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# Initialize KindoAPI with the API key from the config file
kindo_api = KindoAPI(api_key=Config.KINDO_API_KEY)
firebase_handler = FirebaseHandler(firebase_cred_path, firebase_bucket_name)

# Signup API
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if mongo.db.users.find_one({"username": data['username']}):
        return jsonify(success=False, message="User already exists"), 400
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user_data = {
        "username": data['username'],
        "name": data['name'],
        "age": data['age'],
        "language": data['language'],
        "password": hashed_password,
        "working_professional": data['working_professional']
    }
    mongo.db.users.insert_one(user_data)
    return jsonify(success=True, message="Signup successful"), 201

# Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = mongo.db.users.find_one({"username": data['username']})
    
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        return jsonify(success=True, message="Login successful"), 200
    
    return jsonify(success=False, message="Invalid credentials"), 401


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    return_type = request.form.get('return_type')
    if return_type not in ['audio', 'image']:
        return jsonify({'error': 'Invalid return type'}), 400

    filename = secure_filename(file.filename)
    local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(local_file_path)

    # Upload the image to Firebase
    public_url = firebase_handler.upload_to_firebase(file_name, local_file_path)

    # Clean up local file
    firebase_handler.delete_local_file(local_file_path)

    media_type = determine_media_type(file_path)
    if not media_type:
        return jsonify({'error': 'Unsupported media type'}), 400

    file_urls = []
    return jsonify({'urls': file_urls})


if __name__ == "__main__":
    app.run(debug=True)