import openai
import requests
import os
from tempfile import NamedTemporaryFile

openai.api_key = os.getenv("OPENAI_API_KEY")

async def transcribe_audio_from_exotel(audio_url: str) -> str:
    try:
        response = requests.get(audio_url)
        if response.status_code != 200:
            raise Exception("Failed to download audio")

        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_filename = tmp_file.name

        with open(tmp_filename, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            return transcript['text']

    except Exception as e:
        print("Transcription error:", e)
        return "Sorry, I couldn’t understand the message clearly."
