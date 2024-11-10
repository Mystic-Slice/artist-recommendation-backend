import mimetypes
import os


def determine_media_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if mime_type.startswith("image"):
            return "image"
        elif mime_type.startswith("audio"):
            return "audio"
        elif mime_type == "text/plain":
            return "text"

    # Additional check for file extensions
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension in [".webp", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
        return "image"
    elif file_extension in [".mp3", ".wav", ".ogg", ".flac", ".aac"]:
        return "audio"
    elif file_extension in [".txt", ".md", ".rtf"]:
        return "text"

    return None
