import asyncio, json
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..hub import hub
from ..services.pipeline import process_student_speech
from ..services.sarvam import open_sarvam_stream_for
router=APIRouter()
@router.websocket("/ws/student")
async def student_socket(socket: WebSocket) -> None:
    await socket.accept(); language="te"; name="Student"; sarvam_socket:Any=None; receiver:asyncio.Task[None]|None=None
    try:
        first=await socket.receive_json(); code=str(first.get("code","")).strip().upper()
        if first.get("type")!="join" or not await hub.has_class(code): await socket.send_json({"type":"error","message":"That class is not active. Check the class code and try again."}); await socket.close(code=1008); return
        language=first.get("language","te"); name=str(first.get("name","Student")).strip()[:60] or "Student"
        if language not in {"hi","te"}: await socket.send_json({"type":"error","message":"Choose Hindi or Telugu."}); await socket.close(code=1008); return
        await hub.add_student(socket,language,name); await socket.send_json({"type":"ready"}); await hub.send_to_teacher(await hub.connected_message())
        while True:
            message=await socket.receive_json(); kind=message.get("type")
            if kind=="student_ready": await hub.send_to_teacher({"type":"student_ready"})
            elif kind=="signal": await hub.send_to_teacher({"type":"signal","signal":message.get("signal")})
            elif kind=="speak_request": await hub.send_to_teacher({"type":"speak_request","name":await hub.student_name(socket)})
            elif kind=="student_audio" and await hub.can_speak(socket):
                if sarvam_socket is None:
                    sarvam_socket=await open_sarvam_stream_for(language)
                    async def receive_student() -> None:
                        async for raw in sarvam_socket:
                            event=json.loads(raw)
                            if event.get("event")=="transcript.final" and (text:=event.get("text","").strip()): await process_student_speech(socket,text,event.get("language",language))
                    receiver=asyncio.create_task(receive_student())
                await sarvam_socket.send(json.dumps({"event":"audio_input","audio":message["audio"]}))
    except WebSocketDisconnect: pass
    finally:
        await hub.remove(socket)
        if receiver: receiver.cancel()
        if sarvam_socket: await sarvam_socket.close()
        await hub.send_to_teacher(await hub.connected_message())
