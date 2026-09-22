import asyncio
import json
from typing import Any
from fastapi import WebSocket
from ..config import LANGUAGE_CODES
from ..hub import hub
from .sarvam import text_to_speech, translate
segment_id = 0
async def process_final_transcript(text: str, detected_language: str) -> None:
    global segment_id
    segment_id += 1; source = detected_language if detected_language in LANGUAGE_CODES.values() else "en-IN"
    if source not in {"en-IN", "te-IN"}:
        await hub.send_to_teacher({"type":"error","message":"This demo supports English and Telugu speech only."}); return
    for target_code, target_key in {"hi-IN":"hi", "te-IN":"te"}.items():
        students = await hub.students_for(target_key)
        if not students: continue
        try:
            translated = await translate(text, source, target_code); audio = await text_to_speech(translated, target_code)
            await hub.broadcast({"type":"subtitle","original":text,"translated":translated,"source_language":source,"target_language":target_code,"segment_id":segment_id,"spoken_at_ms":int(asyncio.get_running_loop().time()*1000),"audio_base64":audio}, students)
        except RuntimeError as error: await hub.broadcast({"type":"error","message":str(error)}, students)
async def process_student_speech(socket: WebSocket, text: str, detected_language: str) -> None:
    if not await hub.can_speak(socket): return
    source = detected_language if detected_language in {"hi-IN","te-IN"} else await hub.language_for(socket)
    try: await hub.send_to_teacher({"type":"student_speech","name":await hub.student_name(socket),"original":text,"translated":await translate(text, source, "en-IN")})
    except RuntimeError as error: await socket.send_json({"type":"error","message":str(error)})
async def sarvam_receiver(sarvam_socket: Any) -> None:
    async for raw_message in sarvam_socket:
        message=json.loads(raw_message); event=message.get("event")
        if event == "transcript.partial": await hub.send_to_teacher({"type":"transcript_partial","text":message.get("text","")})
        elif event == "transcript.final":
            text=message.get("text","").strip()
            if text:
                await hub.send_to_teacher({"type":"transcript_final","text":text,"language":message.get("language","en-IN")}); await process_final_transcript(text, message.get("language","en-IN"))
        elif event == "error": await hub.send_to_teacher({"type":"error","message":message.get("message","Sarvam STT error")})
