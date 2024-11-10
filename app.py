from utility import determine_media_type
from converters import (
    transcribe_audio,
    transcribe_image,
    describe_audio,
    describe_image,
    get_generic_description,
    generate_tags,
)
from qdrant_handler import add_to_vectorstore, search_vectorstore
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
import sys
import threading
import uuid
import logging

if os.getenv("SHOW_LOGS") == "True":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "./tmp"
app.config["MONGO_URI"] = Config.MONGO_URI

# Ensure the upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

firebase_cred_path = "artist-recommendation-key.json"
firebase_bucket_name = "artist-recommendation.firebasestorage.app"

# Initialize KindoAPI
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# Initialize KindoAPI with the API key from the config file
kindo_api = KindoAPI(api_key=Config.KINDO_API_KEY)
firebase_handler = FirebaseHandler(firebase_cred_path, firebase_bucket_name)


# Signup API
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if mongo.db.users.find_one({"username": data["username"]}):
        return jsonify(success=False, message="User already exists"), 400

    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user_data = {
        "username": data["username"],
        "name": data["name"],
        "password": hashed_password,
    }
    mongo.db.users.insert_one(user_data)
    return jsonify(success=True, message="Signup successful"), 201


# Login API
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = mongo.db.users.find_one({"username": data["username"]})

    if user and bcrypt.check_password_hash(user["password"], data["password"]):
        return jsonify(success=True, message="Login successful"), 200

    return jsonify(success=False, message="Invalid credentials"), 401


# Background task to process slides and save to MongoDB
def process_save_file(local_file_path, filename, media_type):
    # Upload the image to Firebase
    input_media_url = firebase_handler.upload_to_firebase(filename, local_file_path)
    if media_type == "audio":
        transcription = transcribe_audio(local_file_path)
        description = describe_audio(transcription)
    else:
        transcription = transcribe_image(input_media_url)
        description = describe_image(transcription)

    generic_description = get_generic_description(description)
    tags = generate_tags(generic_description)
    add_to_vectorstore(
        text=generic_description, tags=tags, type=media_type, url=input_media_url
    )


# Async endpoint, that initiates the processing and storing of image in the background
@app.route("/save", methods=["POST"])
def save_file():
    """
    This endpoint accepts an image, text, or audio file as input, determines the type of media,
    processes it based on the specified return type (audio or image), and returns a list of URLs
    pointing to the processed media files along with artist details and the user ID.

    Request Parameters:
    - file (file): The media file to be uploaded. (Required)
    - user_id (string): The user ID. (Required)

    Response:
    - input_media_url (string): URL generated for the input media.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    filename = secure_filename(file.filename)
    local_file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(local_file_path)

    media_type = determine_media_type(local_file_path)
    if not media_type:
        return jsonify({"error": "Unsupported media type"}), 400

    # Start background processing of slides
    threading.Thread(
        target=process_save_file, args=(local_file_path, filename, media_type)
    ).start()
    return jsonify({}), 200


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Handle file upload and media processing.

    This endpoint accepts an image, text, or audio file as input, determines the type of media,
    processes it based on the specified return type (audio or image), and returns a list of URLs
    pointing to the processed media files along with artist details and the user ID.

    Request Parameters:
    - file (file): The media file to be uploaded. (File or Text)
    - text(string): Input String (File or text)
    - return_type (string): The desired return type. (Required)
      Allowed values: 'audio', 'image'
    - user_id (string): The user ID. (Required)

    Response:
    - input_media_url (string): URL generated for the input media.
    - return_type (string): The return type specified in the request.
    - urls (array): A list of objects containing URLs and artist details.
      - url (string): The URL of the processed media file.
      - artist_name (string): The name of the artist.
      - artist_email (string): The email of the artist.
      - artist_portfolio_url (string): The portfolio URL of the artist.
    """
    file = request.files["file"]
    text = request.form.get("text")
    input_media_url = None

    if not file and not text:
        return jsonify({"error": "No file or text provided"}), 400

    return_type = request.form.get("return_type")
    if return_type not in ["audio", "image"]:
        return jsonify({"error": "Invalid return type"}), 400

    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    if file:
        filename = secure_filename(file.filename)
        local_file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(local_file_path)

        media_type = determine_media_type(local_file_path)
        if not media_type:
            return jsonify({"error": "Unsupported media type"}), 400

        # Upload the image to Firebase
        input_media_url = firebase_handler.upload_to_firebase(filename, local_file_path)

        if media_type == "audio":
            transcription = transcribe_audio(local_file_path)
            description = describe_audio(transcription)
        elif media_type == "image":
            transcription = transcribe_image(input_media_url)
            description = describe_image(transcription)
        else:
            with open(local_file_path, "r") as file:
                description = file.read()
        # Clean up local file
        firebase_handler.delete_local_file(local_file_path)
    else:
        description = text

    print(f"Description: {description}")
    generic_description = get_generic_description(description)
    tags = generate_tags(generic_description)

    result = search_vectorstore(
        text=generic_description,
        type=return_type,
        tags=tags,
        collection_name=os.getenv("QDRANT_INDEX_NAME"),
    )

    response_data = []
    for i, _ in enumerate(result):
        response_data.append(
            {
                "url": result[i].payload["url"],
                "artist_name": "Test Artist",
                "artist_email": "Test Email",
                "artist_portfolio_url": "http://test.com",
            }
        )

    response = {
        "return_type": return_type,
        "urls": response_data,
    }
    if input_media_url is not None:
        response["input_media_url"] = input_media_url

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
