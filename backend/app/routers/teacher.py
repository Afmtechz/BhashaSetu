import asyncio, json
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..hub import hub
from ..services.pipeline import sarvam_receiver
from ..services.sarvam import open_sarvam_stream
router=APIRouter()
@router.websocket("/ws/teacher")
async def teacher_socket(socket: WebSocket) -> None:
    await socket.accept(); sarvam_socket: Any=None; receiver: asyncio.Task[None]|None=None
    try:
        first=await socket.receive_json()
        if first.get("type")!="teacher_join": await socket.close(code=1008); return
        code=str(first.get("code","")).strip().upper()
        if not await hub.has_class(code): await socket.send_json({"type":"error","message":"Create a classroom before starting the lecture."}); await socket.close(code=1008); return
        await hub.add_teacher(socket); await socket.send_json({"type":"class",**(await hub.class_details())}); await socket.send_json({"type":"connecting"})
        sarvam_socket=await open_sarvam_stream(); receiver=asyncio.create_task(sarvam_receiver(sarvam_socket)); await socket.send_json({"type":"ready"})
        while True:
            message=await socket.receive_json(); kind=message.get("type")
            if kind=="audio": await sarvam_socket.send(json.dumps({"event":"audio_input","audio":message["audio"]}))
            elif kind=="stop":
                await sarvam_socket.send(json.dumps({"event":"end"})); students=await hub.end_class(); await hub.broadcast({"type":"class_ended","message":"The teacher ended this class."},students); await asyncio.gather(*(s.close(code=1000,reason="Class ended") for s in students),return_exceptions=True); break
            elif kind=="signal": await hub.broadcast({"type":"signal","signal":message.get("signal")},await hub.all_students())
            elif kind in {"accept_speak","mute_student"}:
                target=str(message.get("name",""))
                for student in await hub.all_students():
                    if await hub.student_name(student)==target: await hub.set_speaking(student,kind=="accept_speak"); await student.send_json({"type":"speak_accepted" if kind=="accept_speak" else "speak_revoked"}); break
                await socket.send_json(await hub.connected_message())
    except WebSocketDisconnect: pass
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        try: await socket.send_json({"type":"error","message":str(error)}); await socket.close(code=1011)
        except Exception: pass
    finally:
        await hub.remove(socket)
        if receiver: receiver.cancel()
        if sarvam_socket: await sarvam_socket.close()
