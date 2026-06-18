import base64
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Recording
from ..schemas import RecordingResponse

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

UPLOAD_DIR = Path("data/recordings")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/mp4", "audio/m4a", "audio/ogg", "audio/webm",
    "audio/x-m4a", "audio/aac",
}


@router.post("/upload", response_model=RecordingResponse)
async def upload_recording(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if source_type not in ("video_call", "direct_recording"):
        raise HTTPException(400, "source_type must be video_call or direct_recording")

    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(400, f"Unsupported audio format: {content_type}")

    rec_id = str(uuid.uuid4())
    ext = Path(file.filename or "recording").suffix or ".webm"
    save_name = f"{rec_id}{ext}"
    save_path = UPLOAD_DIR / save_name

    content = await file.read()
    save_path.write_bytes(content)

    recording = Recording(
        id=rec_id,
        filename=file.filename or "untitled",
        source_type=source_type,
        file_path=str(save_path.relative_to(Path.cwd())),
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)
    return recording


@router.post("/record", response_model=RecordingResponse)
async def record_audio(
    blob: str = Form(...),
    mime_type: str = Form("audio/webm"),
    source_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if source_type not in ("video_call", "direct_recording"):
        raise HTTPException(400, "source_type must be video_call or direct_recording")

    rec_id = str(uuid.uuid4())
    ext_map = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
    }
    ext = ext_map.get(mime_type, ".webm")
    save_name = f"{rec_id}{ext}"
    save_path = UPLOAD_DIR / save_name

    raw = blob.split(",", 1)[-1] if "," in blob else blob
    data = base64.b64decode(raw)
    save_path.write_bytes(data)

    recording = Recording(
        id=rec_id,
        filename=f"browser-recording-{rec_id[:8]}{ext}",
        source_type=source_type,
        file_path=str(save_path.relative_to(Path.cwd())),
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)
    return recording


@router.get("", response_model=list[RecordingResponse])
async def list_recordings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Recording).order_by(Recording.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(recording_id: str, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(404, "Recording not found")
    return recording
