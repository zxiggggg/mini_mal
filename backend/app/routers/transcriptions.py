import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Recording, Transcription
from ..schemas import TranscriptionResponse, TranscriptionUpdate
from ..services.transcriber import transcribe_audio, TranscriptionError

router = APIRouter(prefix="/api/recordings/{recording_id}", tags=["transcriptions"])


def _segments_to_text(segments) -> str:
    lines = []
    for s in segments:
        speaker = s.get("speaker", "?")
        text = s.get("text", "")
        lines.append(f"[说话人 {speaker}] {text}")
    return "\n\n".join(lines)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def start_transcription(recording_id: str, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(404, "Recording not found")

    # Check if already transcribed
    existing = (await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )).scalar_one_or_none()

    if existing and existing.status == "done":
        return existing

    if existing and existing.status == "processing":
        return existing

    # Create or reset transcription record
    if existing:
        existing.status = "processing"
        existing.error_message = None
    else:
        existing = Transcription(recording_id=recording_id, status="processing")
        db.add(existing)
    await db.commit()
    await db.refresh(existing)

    # Run transcription in background (FastAPI doesn't support async background natively well,
    # but for a single-user local tool, sync blocking is acceptable)
    try:
        text = await transcribe_audio(recording.file_path, recording.source_type)
        existing.text = text
        existing.status = "done"
    except TranscriptionError as e:
        existing.status = "error"
        existing.error_message = str(e)

    await db.commit()
    await db.refresh(existing)
    return existing


@router.get("/transcription", response_model=TranscriptionResponse)
async def get_transcription(recording_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")
    return transcription


@router.put("/transcription", response_model=TranscriptionResponse)
async def update_transcription(
    recording_id: str,
    body: TranscriptionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")
    transcription.text = body.text
    await db.commit()
    await db.refresh(transcription)
    return transcription
