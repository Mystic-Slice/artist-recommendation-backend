from utility import determine_media_type
from converters import (
    transcribe_audio,
    transcribe_image,
    describe_audio,
    describe_image,
    get_generic_description,
    generate_tags,
)
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
        "age": data["age"],
        "language": data["language"],
        "password": hashed_password,
        "working_professional": data["working_professional"],
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


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Handle file upload and media processing.

    This endpoint accepts an image, text, or audio file as input, determines the type of media,
    processes it based on the specified return type (audio or image), and returns a list of URLs
    pointing to the processed media files along with artist details and the user ID.

    Request Parameters:
    - file (file): The media file to be uploaded. (Required)
    - return_type (string): The desired return type. (Required)
      Allowed values: 'audio', 'image'
    - user_id (string): The user ID. (Required)

    Response:
    - user_id (string): The user ID provided in the request.
    - return_type (string): The return type specified in the request.
    - urls (array): A list of objects containing URLs and artist details.
      - url (string): The URL of the processed media file.
      - artist_name (string): The name of the artist.
      - artist_email (string): The email of the artist.
      - artist_portfolio_url (string): The portfolio URL of the artist.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    return_type = request.form.get("return_type")
    if return_type not in ["audio", "image"]:
        return jsonify({"error": "Invalid return type"}), 400

    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    filename = secure_filename(file.filename)
    local_file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(local_file_path)

    media_type = determine_media_type(local_file_path)
    if not media_type:
        return jsonify({"error": "Unsupported media type"}), 400

    # Upload the image to Firebase
    input_media_url = firebase_handler.upload_to_firebase(filename, local_file_path)

    if media_type == "audio":
        transcription = transcribe_audio(input_media_url)
        description = describe_audio(transcription)
    else:
        transcription = transcribe_image(input_media_url)
        description = describe_image(transcription)

    generic_description = get_generic_description(description)
    tags = generate_tags(generic_description)

    add_to_vectorstore(
        text=generic_description, tags=tags, type=media_type, url=input_media_url
    )

    result = search_vectorstore(
        text=generic_description,
        type=return_type,
        tags=tags,
        collection_name=os.getenv("QDRANT_INDEX_NAME"),
    )

    # Clean up local file
    firebase_handler.delete_local_file(local_file_path)

    # Example media data
    # medias = [
    #     {
    #         "name": "Artist One",
    #         "email": "artist1@example.com",
    #         "portfolio_url": "https://portfolio.example.com/artist1",
    #         "url": "https://firebasestorage.googleapis.com/v0/b/artist-recommendation.firebasestorage.app/o/Great-Scenes-Mr-Beans-Holiday.jpg?alt=media&token=86455e64-fd28-4cdc-8840-edccdbf068d1",
    #     },
    #     {
    #         "name": "Artist Two",
    #         "email": "artist2@example.com",
    #         "portfolio_url": "https://portfolio.example.com/artist2",
    #         "url": "https://firebasestorage.googleapis.com/v0/b/artist-recommendation.firebasestorage.app/o/Kill-Bill-Fight-Scene.jpg?alt=media&token=d36681dc-ff50-4621-a1ba-04f620d190fe",
    #     },
    #     {
    #         "name": "Artist Three",
    #         "email": "artist3@example.com",
    #         "portfolio_url": "https://portfolio.example.com/artist3",
    #         "url": "https://firebasestorage.googleapis.com/v0/b/artist-recommendation.firebasestorage.app/o/titanic_scene.webp?alt=media&token=72017555-2212-4009-a19e-ed044a4000b2",
    #     },
    # ]

    # Create the response data
    # response_data = []
    # for i, _ in enumerate(medias):
    #     response_data.append(
    #         {
    #             "url": medias[i]["url"],
    #             "artist_name": medias[i]["name"],
    #             "artist_email": medias[i]["email"],
    #             "artist_portfolio_url": medias[i]["portfolio_url"],
    #         }
    #     )

    response_data = []
    for i, _ in enumerate(result):
        response_data.append(
            {
                "url": result[i].payload["url"],
                "artist_name": 'Test Artist',
                "artist_email": 'Test Email',
                "artist_portfolio_url": 'http://test.com',
            }
        )

    return jsonify(
        {
            "input_media_url": input_media_url,
            "return_type": return_type,
            "urls": response_data,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
