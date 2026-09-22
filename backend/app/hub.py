import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Set
from fastapi import WebSocket

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
        self.class_code: str | None = None
        self.class_name = ""
    async def create_class(self, name: str) -> str:
        async with self.lock:
            self.class_code = secrets.token_urlsafe(4).upper()
            self.class_name = name.strip()[:80] or "Live classroom"
            self.classroom = Classroom()
            return self.class_code
    async def has_class(self, code: str) -> bool:
        async with self.lock:
            return bool(self.class_code and secrets.compare_digest(self.class_code, code))
    async def class_details(self) -> dict[str, str | None]:
        async with self.lock:
            return {"code": self.class_code, "name": self.class_name}
    async def add_teacher(self, socket: WebSocket) -> None:
        async with self.lock: self.classroom.teacher = socket
    async def add_student(self, socket: WebSocket, language: str, name: str) -> None:
        async with self.lock:
            self.classroom.students.add(socket); self.classroom.student_languages[socket] = language; self.classroom.student_names[socket] = name
    async def remove(self, socket: WebSocket) -> None:
        async with self.lock:
            if self.classroom.teacher is socket: self.classroom.teacher = None
            self.classroom.students.discard(socket); self.classroom.student_languages.pop(socket, None); self.classroom.student_names.pop(socket, None); self.classroom.speaking_allowed.discard(socket)
    async def end_class(self) -> list[WebSocket]:
        async with self.lock:
            students = list(self.classroom.students); self.class_code = None; self.class_name = ""; return students
    async def student_name(self, socket: WebSocket) -> str:
        async with self.lock: return self.classroom.student_names.get(socket, "Student")
    async def set_speaking(self, socket: WebSocket, allowed: bool) -> None:
        async with self.lock:
            (self.classroom.speaking_allowed.add(socket) if allowed else self.classroom.speaking_allowed.discard(socket))
    async def can_speak(self, socket: WebSocket) -> bool:
        async with self.lock: return socket in self.classroom.speaking_allowed
    async def language_for(self, socket: WebSocket) -> str:
        async with self.lock: return self.classroom.student_languages.get(socket, "te")
    async def students_for(self, language: str) -> list[WebSocket]:
        async with self.lock: return [s for s in self.classroom.students if self.classroom.student_languages.get(s) == language]
    async def all_students(self) -> list[WebSocket]:
        async with self.lock: return list(self.classroom.students)
    async def send_to_teacher(self, message: dict) -> None:
        async with self.lock: teacher = self.classroom.teacher
        if teacher:
            try: await teacher.send_json(message)
            except Exception: await self.remove(teacher)
    async def connected_message(self) -> dict:
        async with self.lock: return {"type":"students", "count":len(self.classroom.students), "names":list(self.classroom.student_names.values())}
    async def broadcast(self, message: dict, sockets: list[WebSocket]) -> None:
        if not sockets: return
        results = await asyncio.gather(*(s.send_json(message) for s in sockets), return_exceptions=True)
        for socket, result in zip(sockets, results):
            if isinstance(result, Exception): await self.remove(socket)

hub = ClassroomHub()
