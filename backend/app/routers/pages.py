from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..config import SARVAM_API_KEY
from ..hub import hub
router=APIRouter()
ROOT=Path(__file__).resolve().parents[3]
@router.get("/health")
async def health() -> dict[str,str]: return {"status":"ok","sarvam_configured":str(bool(SARVAM_API_KEY)).lower()}
@router.post("/api/classes")
async def create_class(payload: dict[str,str] | None = None) -> dict[str,str]:
    code=await hub.create_class((payload or {}).get("name","Live classroom")); return {"code":code,"name":(await hub.class_details())["name"] or "Live classroom"}
@router.get("/api/classes/{code}")
async def get_class(code: str) -> dict[str,str|bool]:
    details=await hub.class_details(); return {"exists":await hub.has_class(code.strip().upper()),"name":details["name"] or ""}
@router.get("/")
async def website() -> FileResponse: return FileResponse(ROOT / "static" / "index.html")
