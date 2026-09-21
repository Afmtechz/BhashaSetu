import asyncio
import base64
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Set

import httpx
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
ROOT = Path(__file__).resolve().parent
SARVAM_WS_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
SARVAM_API_URL = "https://api.sarvam.ai"
LANGUAGE_CODES = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}

app = FastAPI(title="Bhasha-Setu AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Classroom:
    teacher: WebSocket | None = None
    students: Set[WebSocket] = field(default_factory=set)
    student_languages: dict[WebSocket, str] = field(default_factory=dict)
    student_names: dict[WebSocket, str] = field(default_factory=dict)
    speaking_allowed: Set[WebSocket] = field(default_factory=set)


class ClassroomHub:
    def __init__(self) -> None:
        self.classroom = Classroom()
        self.lock = asyncio.Lock()

    async def add_teacher(self, socket: WebSocket) -> None:
        async with self.lock:
            self.classroom.teacher = socket

    async def add_student(self, socket: WebSocket, language: str, name: str) -> None:
        async with self.lock:
            self.classroom.students.add(socket)
            self.classroom.student_languages[socket] = language
            self.classroom.student_names[socket] = name

    async def remove(self, socket: WebSocket) -> None:
        async with self.lock:
            if self.classroom.teacher is socket:
                self.classroom.teacher = None
            self.classroom.students.discard(socket)
            self.classroom.student_languages.pop(socket, None)
            self.classroom.student_names.pop(socket, None)
            self.classroom.speaking_allowed.discard(socket)

    async def student_count(self) -> int:
        async with self.lock:
            return len(self.classroom.students)

    async def student_name(self, socket: WebSocket) -> str:
        async with self.lock:
            return self.classroom.student_names.get(socket, "Student")

    async def set_speaking(self, socket: WebSocket, allowed: bool) -> None:
        async with self.lock:
            if allowed:
                self.classroom.speaking_allowed.add(socket)
            else:
                self.classroom.speaking_allowed.discard(socket)

    async def can_speak(self, socket: WebSocket) -> bool:
        async with self.lock:
            return socket in self.classroom.speaking_allowed

    async def language_for(self, socket: WebSocket) -> str:
        async with self.lock:
            return self.classroom.student_languages.get(socket, "te")

    async def students_for(self, language: str) -> list[WebSocket]:
        async with self.lock:
            return [
                socket
                for socket in self.classroom.students
                if self.classroom.student_languages.get(socket) == language
            ]

    async def all_students(self) -> list[WebSocket]:
        async with self.lock:
            return list(self.classroom.students)

    async def send_to_teacher(self, message: dict) -> None:
        async with self.lock:
            teacher = self.classroom.teacher
        if teacher:
            try:
                await teacher.send_json(message)
            except Exception:
                await self.remove(teacher)

    async def connected_message(self) -> dict:
        async with self.lock:
            return {
                "type": "students",
                "count": len(self.classroom.students),
                "names": list(self.classroom.student_names.values()),
            }

    async def broadcast(self, message: dict, sockets: list[WebSocket]) -> None:
        if not sockets:
            return
        results = await asyncio.gather(
            *(socket.send_json(message) for socket in sockets),
            return_exceptions=True,
        )
        for socket, result in zip(sockets, results):
            if isinstance(result, Exception):
                await self.remove(socket)


hub = ClassroomHub()
segment_id = 0


def require_api_key() -> None:
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not configured.")


async def translate(text: str, source: str, target: str) -> str:
    if source == target:
        return text
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{SARVAM_API_URL}/translate",
            headers={"api-subscription-key": SARVAM_API_KEY},
            json={
                "input": text,
                "source_language_code": source,
                "target_language_code": target,
                "model": "mayura:v1",
                "mode": "modern-colloquial",
                "speaker_gender": "Male",
            },
        )
    if response.is_error:
        raise RuntimeError(f"Sarvam translation failed: {response.text[:300]}")
    translated = response.json().get("translated_text")
    if not translated:
        raise RuntimeError("Sarvam returned no translated text.")
    return translated


async def text_to_speech(text: str, language: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{SARVAM_API_URL}/text-to-speech",
            headers={"api-subscription-key": SARVAM_API_KEY},
            json={
                "text": text,
                "language_code": language,
                "model": "bulbul:v3",
                "speaker": os.getenv("SARVAM_TTS_SPEAKER", "shubh"),
                "pace": 1.0,
                "temperature": 0.6,
                "speech_sample_rate": 24000,
                "output_audio_codec": "wav",
            },
        )
    if response.is_error:
        raise RuntimeError(f"Sarvam speech synthesis failed: {response.text[:300]}")
    audios = response.json().get("audios")
    if not audios:
        raise RuntimeError("Sarvam returned no audio.")
    return "".join(audios)


async def process_final_transcript(text: str, detected_language: str) -> None:
    global segment_id
    segment_id += 1
    current_segment = segment_id
    source = detected_language if detected_language in LANGUAGE_CODES.values() else "en-IN"
    if source not in {"en-IN", "te-IN"}:
        teacher = hub.classroom.teacher
        if teacher:
            await teacher.send_json(
                {"type": "error", "message": "This demo supports English and Telugu speech only."}
            )
        return
    targets = {"hi-IN": "hi", "te-IN": "te"}
    for target_code, target_key in targets.items():
        students = await hub.students_for(target_key)
        if not students:
            continue
        try:
            translated = await translate(text, source, target_code)
            audio = await text_to_speech(translated, target_code)
            await hub.broadcast(
                {
                    "type": "subtitle",
                    "original": text,
                    "translated": translated,
                    "source_language": source,
                    "target_language": target_code,
                    "segment_id": current_segment,
                    "spoken_at_ms": int(asyncio.get_running_loop().time() * 1000),
                    "audio_base64": audio,
                },
                students,
            )
        except RuntimeError as error:
            await hub.broadcast(
                {"type": "error", "message": str(error)},
                students,
            )


async def process_student_speech(
    socket: WebSocket, text: str, detected_language: str
) -> None:
    if not await hub.can_speak(socket):
        return
    source = detected_language if detected_language in {"hi-IN", "te-IN"} else await hub.language_for(socket)
    try:
        english = await translate(text, source, "en-IN")
        await hub.send_to_teacher(
            {
                "type": "student_speech",
                "name": await hub.student_name(socket),
                "original": text,
                "translated": english,
            }
        )
    except RuntimeError as error:
        await socket.send_json({"type": "error", "message": str(error)})


async def sarvam_receiver(sarvam_socket: Any) -> None:
    async for raw_message in sarvam_socket:
        message = json.loads(raw_message)
        event = message.get("event")
        if event == "transcript.partial":
            teacher = hub.classroom.teacher
            if teacher:
                await teacher.send_json(
                    {"type": "transcript_partial", "text": message.get("text", "")}
                )
        elif event == "transcript.final":
            text = message.get("text", "").strip()
            if text:
                teacher = hub.classroom.teacher
                if teacher:
                    await teacher.send_json(
                        {
                            "type": "transcript_final",
                            "text": text,
                            "language": message.get("language", "en-IN"),
                        }
                    )
                await process_final_transcript(text, message.get("language", "en-IN"))
        elif event == "error":
            teacher = hub.classroom.teacher
            if teacher:
                await teacher.send_json(
                    {"type": "error", "message": message.get("message", "Sarvam STT error")}
                )


async def open_sarvam_stream() -> Any:
    require_api_key()
    return await websockets.connect(
        f"{SARVAM_WS_URL}?language_code=auto&model=saaras:v3-realtime"
        "&stream_type=fast&endpointing=vad&encoding=linear16&sample_rate=16000"
        "&silence_duration_ms=500&min_speech_duration_ms=250",
        extra_headers={"api-subscription-key": SARVAM_API_KEY},
        ping_interval=20,
    )


async def open_sarvam_stream_for(language: str) -> Any:
    require_api_key()
    language_code = {"hi": "hi-IN", "te": "te-IN"}.get(language, language)
    return await websockets.connect(
        f"{SARVAM_WS_URL}?language_code={language_code}&model=saaras:v3-realtime"
        "&stream_type=fast&endpointing=vad&encoding=linear16&sample_rate=16000"
        "&silence_duration_ms=500&min_speech_duration_ms=250",
        extra_headers={"api-subscription-key": SARVAM_API_KEY},
        ping_interval=20,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sarvam_configured": str(bool(SARVAM_API_KEY)).lower()}


@app.get("/")
async def website() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")


@app.websocket("/ws/teacher")
async def teacher_socket(socket: WebSocket) -> None:
    await socket.accept()
    await hub.add_teacher(socket)
    sarvam_socket: Any = None
    receiver: asyncio.Task[None] | None = None
    try:
        await socket.send_json({"type": "connecting"})
        sarvam_socket = await open_sarvam_stream()
        receiver = asyncio.create_task(sarvam_receiver(sarvam_socket))
        await socket.send_json({"type": "ready"})
        while True:
            message = await socket.receive_json()
            if message.get("type") == "audio":
                await sarvam_socket.send(
                    json.dumps(
                        {
                            "event": "audio_input",
                            "audio": message["audio"],
                        }
                    )
                )
            elif message.get("type") == "stop":
                await sarvam_socket.send(json.dumps({"event": "end"}))
                break
            elif message.get("type") == "signal":
                await hub.broadcast(
                    {"type": "signal", "signal": message.get("signal")},
                    await hub.all_students(),
                )
            elif message.get("type") == "accept_speak":
                target_name = str(message.get("name", ""))
                for student in await hub.all_students():
                    if await hub.student_name(student) == target_name:
                        await hub.set_speaking(student, True)
                        await student.send_json({"type": "speak_accepted"})
                        break
            elif message.get("type") == "mute_student":
                target_name = str(message.get("name", ""))
                for student in await hub.all_students():
                    if await hub.student_name(student) == target_name:
                        await hub.set_speaking(student, False)
                        await student.send_json({"type": "speak_revoked"})
                        break
            if message.get("type") in {"accept_speak", "mute_student"}:
                await socket.send_json(await hub.connected_message())
    except WebSocketDisconnect:
        pass
    except (RuntimeError, websockets.WebSocketException, KeyError, json.JSONDecodeError) as error:
        try:
            await socket.send_json({"type": "error", "message": str(error)})
            await socket.close(code=1011)
        except Exception:
            pass
    finally:
        await hub.remove(socket)
        if receiver:
            receiver.cancel()
        if sarvam_socket:
            await sarvam_socket.close()


@app.websocket("/ws/student")
async def student_socket(socket: WebSocket) -> None:
    await socket.accept()
    language = "te"
    name = "Student"
    sarvam_socket: Any = None
    receiver: asyncio.Task[None] | None = None
    try:
        first_message = await socket.receive_json()
        if first_message.get("type") == "join":
            language = first_message.get("language", "te")
            name = str(first_message.get("name", "Student")).strip()[:60] or "Student"
        if language not in {"hi", "te"}:
            await socket.send_json({"type": "error", "message": "Choose Hindi or Telugu."})
            await socket.close(code=1008)
            return
        await hub.add_student(socket, language, name)
        await socket.send_json({"type": "ready"})
        await hub.send_to_teacher(await hub.connected_message())
        while True:
            message = await socket.receive_json()
            if message.get("type") == "student_ready":
                await hub.send_to_teacher({"type": "student_ready"})
            elif message.get("type") == "signal":
                await hub.send_to_teacher(
                    {"type": "signal", "signal": message.get("signal")}
                )
            elif message.get("type") == "speak_request":
                await hub.send_to_teacher(
                    {"type": "speak_request", "name": await hub.student_name(socket)}
                )
            elif message.get("type") == "student_audio":
                if await hub.can_speak(socket):
                    if sarvam_socket is None:
                        sarvam_socket = await open_sarvam_stream_for(language)

                        async def receive_student() -> None:
                            async for raw in sarvam_socket:
                                event = json.loads(raw)
                                if event.get("event") == "transcript.final":
                                    text = event.get("text", "").strip()
                                    if text:
                                        await process_student_speech(
                                            socket, text, event.get("language", language)
                                        )

                        receiver = asyncio.create_task(receive_student())
                    await sarvam_socket.send(
                        json.dumps({"event": "audio_input", "audio": message["audio"]})
                    )
    except WebSocketDisconnect:
        pass
    finally:
        await hub.remove(socket)
        if receiver:
            receiver.cancel()
        if sarvam_socket:
            await sarvam_socket.close()
        await hub.send_to_teacher(await hub.connected_message())
