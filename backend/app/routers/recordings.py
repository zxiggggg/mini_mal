import base64
import csv
import io
import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import QAPair, Recording, Transcription
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


@router.get("/{recording_id}/export")
async def export_recording(recording_id: str, format: str = Query("json"), db: AsyncSession = Depends(get_db)):
    if format not in ("json", "csv", "txt"):
        raise HTTPException(400, "format must be json, csv, or txt")

    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(404, "Recording not found")

    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()

    qa_pairs = []
    if transcription:
        result = await db.execute(
            select(QAPair)
            .where(QAPair.transcription_id == transcription.id)
            .order_by(QAPair.order_index)
        )
        qa_pairs = result.scalars().all()

    data = {
        "filename": recording.filename,
        "source_type": recording.source_type,
        "created_at": recording.created_at.isoformat(),
        "transcript": transcription.text if transcription else None,
        "speaker_labels": transcription.speaker_labels if transcription else None,
        "qa_pairs": [
            {
                "question": q.question,
                "answer": q.answer,
                "suggestions": q.suggestions,
            }
            for q in qa_pairs
        ],
    }

    if format == "json":
        return PlainTextResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={recording.filename}.json"},
        )

    if format == "txt":
        lines = [f"文件：{recording.filename}", f"来源：{recording.source_type}", ""]
        if transcription and transcription.text:
            lines.append("=== 转写文本 ===")
            lines.append(transcription.text)
            lines.append("")
        for i, q in enumerate(qa_pairs):
            lines.append(f"--- 问答对 {i + 1} ---")
            lines.append(f"问题：{q.question}")
            lines.append(f"回答：{q.answer}")
            if q.suggestions:
                for s in q.suggestions:
                    lines.append(f"  · {s}")
            lines.append("")
        return PlainTextResponse(
            "\n".join(lines),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={recording.filename}.txt"},
        )

    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["question", "answer", "suggestions"])
    for q in qa_pairs:
        writer.writerow([
            q.question,
            q.answer,
            " | ".join(q.suggestions) if q.suggestions else "",
        ])
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={recording.filename}.csv"},
    )


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(404, "Recording not found")

    # Delete transcription and QA pairs
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if transcription:
        result = await db.execute(
            select(QAPair).where(QAPair.transcription_id == transcription.id)
        )
        for qa in result.scalars():
            await db.delete(qa)
        await db.delete(transcription)

    # Delete audio file
    file_path = Path(recording.file_path)
    if file_path.exists():
        file_path.unlink()

    await db.delete(recording)
    await db.commit()
    return {"ok": True}
