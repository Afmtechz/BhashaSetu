import os
from dotenv import load_dotenv
load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "shubh")
SARVAM_WS_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
SARVAM_API_URL = "https://api.sarvam.ai"
LANGUAGE_CODES = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}
