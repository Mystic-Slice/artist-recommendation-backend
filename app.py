from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from config import Config
from kindo_api import KindoAPI
from firebase_handler import FirebaseHandler
import time
import re
import threading
import uuid

app = Flask(__name__)
app.config["MONGO_URI"] = Config.MONGO_URI

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


if __name__ == "__main__":
    app.run(debug=True)