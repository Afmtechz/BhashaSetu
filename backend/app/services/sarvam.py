import os
import httpx
import websockets
from typing import Any
from ..config import SARVAM_API_KEY, SARVAM_API_URL, SARVAM_TTS_SPEAKER, SARVAM_WS_URL

def require_api_key() -> None:
    if not SARVAM_API_KEY: raise RuntimeError("SARVAM_API_KEY is not configured.")
async def translate(text: str, source: str, target: str) -> str:
    if source == target: return text
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{SARVAM_API_URL}/translate", headers={"api-subscription-key":SARVAM_API_KEY}, json={"input":text,"source_language_code":source,"target_language_code":target,"model":"mayura:v1","mode":"modern-colloquial","speaker_gender":"Male"})
    if response.is_error: raise RuntimeError(f"Sarvam translation failed: {response.text[:300]}")
    translated = response.json().get("translated_text")
    if not translated: raise RuntimeError("Sarvam returned no translated text.")
    return translated
async def text_to_speech(text: str, language: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{SARVAM_API_URL}/text-to-speech", headers={"api-subscription-key":SARVAM_API_KEY}, json={"text":text,"language_code":language,"model":"bulbul:v3","speaker":SARVAM_TTS_SPEAKER,"pace":1.0,"temperature":0.6,"speech_sample_rate":24000,"output_audio_codec":"wav"})
    if response.is_error: raise RuntimeError(f"Sarvam speech synthesis failed: {response.text[:300]}")
    audios = response.json().get("audios")
    if not audios: raise RuntimeError("Sarvam returned no audio.")
    return "".join(audios)
def _stream_url(language: str) -> str:
    code = {"hi":"hi-IN", "te":"te-IN"}.get(language, language)
    return f"{SARVAM_WS_URL}?language_code={code}&model=saaras:v3-realtime&stream_type=fast&endpointing=vad&encoding=linear16&sample_rate=16000&silence_duration_ms=500&min_speech_duration_ms=250"
async def open_sarvam_stream() -> Any:
    require_api_key(); return await websockets.connect(_stream_url("auto"), extra_headers={"api-subscription-key":SARVAM_API_KEY}, ping_interval=20)
async def open_sarvam_stream_for(language: str) -> Any:
    require_api_key(); return await websockets.connect(_stream_url(language), extra_headers={"api-subscription-key":SARVAM_API_KEY}, ping_interval=20)
