import requests
import json
import time
from pathlib import Path
import os
from huggingface_hub import InferenceClient
import logging

from kindo_api import KindoAPI

def transcribe_audio(audio_path):
    logging.info(f"Transcribing audio file: {audio_path}")

    api_url = os.getenv("WHISPER_API_ENDPOINT")
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    # Check if file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Read the audio file in binary mode
    with open(audio_path, "rb") as file:
        data = file.read()

    # Make API request
    response = requests.post(
        api_url,
        headers=headers,
        data=data
    )

    # Check if model is still loading
    if response.status_code == 503:
        estimated_time = json.loads(response.text).get("estimated_time", 20)
        logging.info(f"Model is loading. Waiting for {estimated_time} seconds...")
        time.sleep(estimated_time)
        # Retry the request
        response = requests.post(
            api_url,
            headers=headers,
            data=data
        )

    # Handle other potential errors
    response.raise_for_status()

    response = response.json()


    if response.get('text'):
        logging.info("Transcription complete.")
        return response.get('text')
    else:
        raise Exception("Transcription failed. No text found in response.")

def describe_audio(transcription):
    logging.info(f"Generating audio description for transcription: {transcription}")

    prompt = f"""
    You are given a transcription of a song clip. Your task is to use the transcription to describe the song. Try to understand what the song is about, what emotions it conveys, and what message it is trying to communicate. Write a brief description of the song using the transcription as a reference. The description should not be more than 100 words.
    Transcription: {transcription}
    """


    kindo = KindoAPI(os.getenv("KINDO_API_KEY"))

    response = kindo.call_kindo_api(
        model="azure/gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    try:
        desc = response.json()['choices'][0]['message']['content']

        logging.info(f"Audio Description generated: {desc}")
        return desc
    except Exception as e:
        raise Exception(f"Failed to generate audio description: {e}")
    
def transcribe_image(image_url):
    logging.info(f"Generating image description for image: {image_url}")

    client = InferenceClient(api_key=os.getenv("HUGGINGFACE_API_KEY"))

    prompt = """
    Describe this image with as much details as possible. Mention the objects, people, animals, and any other relevant information in the image. The description should be detailed and informative.
    """ 

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct", 
        messages=messages, 
        max_tokens=500,
    )

    description = response.choices[0].message.content

    logging.info(f"Image Description generated: {description}")
    return description

def describe_image(description):
    logging.info(f"Generating detailed description for image: {description}")

    prompt = f"""
    You are given a description of an image. Your task is to provide a detailed description of the image based on the given description. The description should capture the possible emotions, themes and story behind the image. It should be detailed and informative. The description should not be more than 100 words.
    Description: {description}
    """

    kindo = KindoAPI(os.getenv("KINDO_API_KEY"))

    response = kindo.call_kindo_api(
        model="azure/gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    try:
        desc = response.json()['choices'][0]['message']['content']

        logging.info(f"Detailed Description generated: {desc}")
        return desc
    except Exception as e:
        raise Exception(f"Failed to generate detailed description: {e}")
    
def get_generic_description(description):
    logging.info(f"Generating generic description for text: {description}")

    prompt = f"""
    You are given a text description. It could be about a music sample, an image or a movie plot. Whatever the media might be, using the given description, generate a generic description that captures the essence of the description. The generated description should be concise and informative. It should not contain any reference to what type of media the original description was about.
    Description: {description}
    """

    kindo = KindoAPI(os.getenv("KINDO_API_KEY"))

    response = kindo.call_kindo_api(
        model="azure/gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    try:
        desc = response.json()['choices'][0]['message']['content']

        logging.info(f"Generic Description generated: {desc}")
        return desc
    except Exception as e:
        raise Exception(f"Failed to generate generic description: {e}")
    
def generate_tags(generic_description):
    prompt = f"""
    You are given a description. Your task is to pick the relevant tags based on the description. The tags should be concise and descriptive, capturing the key elements of the description. These tags will help in  categorizing and organizing the content for future reference. The possible tags are Joy, Sorrow, Love, Fear, Hope, Anger, Longing, Freedom, Conflict and Gratitude. The tags must be from this list only. Provide a comma separated list of tags that you think fit with the description. The output should contain nothing but the comma separated tags.
    Description: {generic_description}
    """

    kindo = KindoAPI(os.getenv("KINDO_API_KEY"))

    response = kindo.call_kindo_api(
        model="azure/gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    try:
        tags = response.json()['choices'][0]['message']['content']

        logging.info(f"Tags generated: {tags}")
        return [x.strip() for x in tags.split(",")]
    except Exception as e:
        raise Exception(f"Failed to generate tags: {e}")
