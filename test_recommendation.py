from converters import transcribe_audio, transcribe_image, describe_audio, describe_image, get_generic_description, generate_tags

from qdrant_handler import add_to_vectorstore, search_vectorstore
import os
import dotenv
import logging
import sys

dotenv.load_dotenv()

if os.getenv("SHOW_LOGS") == "True":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# audio_dir = "data/audio"

# for audio_file in os.listdir(audio_dir):
#     audio_path = os.path.join(audio_dir, audio_file)

#     # Get transcription
#     result = transcribe_audio(audio_path)

#     # Describe the audio
#     description = describe_audio(result)

#     generic_description = get_generic_description(description)

#     tags = generate_tags(generic_description)

#     print("Tags generated:", tags)

#     print("-------------------------------------------------")
#     break

# image_url = "https://i.pinimg.com/736x/5f/e1/1e/5fe11e98bac3c740ac5625ab0f359aff.jpg"

# transcription = transcribe_image(image_url)
# description = describe_image(transcription)
# generic_description = get_generic_description(description)
# tags = generate_tags(generic_description)

# print("Description: ", description)
# print("Tags generated:", tags)

# add_to_vectorstore(
#     text="The Statue of Liberty is a colossal neoclassical sculpture on Liberty Island in New York Harbor in New York City, in the United States.",
#     tags=["Statue of Liberty", "New York", "USA"],
#     type="image",
#     url="https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
# )

# add_to_vectorstore(
#     text="Two men hugging",
#     tags=["New York", "USA", "humans", "men"],
#     type="image",
#     url="https://img.freepik.com/premium-photo/there-are-two-men-hugging-each-other-hug-generative-ai_900751-22080.jpg"
# )

# add_to_vectorstore(
#     text="Sceneary music",
#     tags=["sunset", "city", "skyline"],
#     type="music",
#     url="https://plus.unsplash.com/premium_photo-1668024966086-bd66ba04262f?fm=jpg&q=60&w=3000&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MXx8c2NlbmVyeXxlbnwwfHwwfHx8MA%3D%3D"
# )

# add_to_vectorstore(
#     text="Two men hugging music",
#     tags=["New York", "USA", "music", "men"],
#     type="music",
#     url="https://img.freepik.com/premium-photo/there-are-two-men-hugging-each-other-hug-generative-ai_900751-22080.jpg"
# )

# result = search_vectorstore(
#     text="Statue of Liberty",
#     type="music",
#     tags=["skyline"],
#     collection_name="hacksc"
# )

# print(result)

## Audio
# Audio -> transcribe_audio -> describe_audio -> generic description + generate tags -> add to vectorstore (text, type, tags, url)

## Image
# Image -> transcribe_image -> describe_image -> generic description + generate tags -> add to vectorstore (text, type, tags, url)

# Search
# Search -> search_vectorstore (text, type, tags, url) -> results