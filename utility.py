import mimetypes

def determine_media_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if mime_type.startswith('image'):
            return 'image'
        elif mime_type.startswith('audio'):
            return 'audio'
        elif mime_type == 'text/plain':
            return 'text'
    return None