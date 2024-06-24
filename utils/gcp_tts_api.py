from google.cloud import texttospeech
import os
from dotenv import load_dotenv


load_dotenv("../.env")


GCP_API_KEY=os.environ.get('GCP_API_KEY')
GCP_PROJECT_ID=os.environ.get('GCP_PROJECT_ID')
GCP_MALE_MODEL="it-IT-Neural2-C"
GCP_FEMALE_MODEL="it-IT-Neural2-A"

class GcpTTSApi():

    def __init__(self):
        self.__client = texttospeech.TextToSpeechClient(
            client_options={
                "api_key": GCP_API_KEY,
                "quota_project_id": GCP_PROJECT_ID,
            }
        )

    def synthetize_speech(self, input_text=None, gender=None):

        if not input_text:
            raise ValueError("No input text specified.")
        if not gender:
            raise ValueError("No gender specified.")
        if gender.upper() not in ['MALE', 'FEMALE']:
            raise ValueError("Invalid gender specified.")

        synthesis_input = texttospeech.SynthesisInput(text=input_text)
        model = GCP_MALE_MODEL if gender.upper() == "MALE" else GCP_FEMALE_MODEL
        voice = texttospeech.VoiceSelectionParams(
            language_code="it-IT",
            name=model
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        try:
            response = self.__client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            return [response.audio_content, model]

        except Exception as e:
            print(f"Error in synthetize_speech: {e}")
            return None
