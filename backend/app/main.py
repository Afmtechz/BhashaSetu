from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers.pages import router as pages_router
from .routers.teacher import router as teacher_router
from .routers.student import router as student_router

def create_app() -> FastAPI:
    application = FastAPI(title="Bhasha-Setu AI")
    application.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    application.mount("/static", StaticFiles(directory="static"), name="static")
    application.include_router(pages_router)
    application.include_router(teacher_router)
    application.include_router(student_router)
    return application

app = create_app()
