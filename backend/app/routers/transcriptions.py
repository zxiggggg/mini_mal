from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import QAPair, Recording, Transcription
from ..schemas import (
    QAPairListResponse,
    QAPairResponse,
    SpeakerLabelsUpdate,
    TranscriptionResponse,
    TranscriptionUpdate,
)
from ..services.qa_extractor import extract_qa_pairs, QAExtractionError
from ..services.suggester import generate_suggestions, SuggestionError
from ..services.transcriber import transcribe_audio, TranscriptionError

router = APIRouter(prefix="/api/recordings/{recording_id}", tags=["transcriptions"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def start_transcription(recording_id: str, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(404, "Recording not found")

    existing = (await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )).scalar_one_or_none()

    if existing and existing.status == "done":
        return existing

    if existing and existing.status == "processing":
        return existing

    if existing:
        existing.status = "processing"
        existing.error_message = None
    else:
        existing = Transcription(recording_id=recording_id, status="processing")
        db.add(existing)
    await db.commit()
    await db.refresh(existing)

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


@router.put("/speakers", response_model=TranscriptionResponse)
async def update_speaker_labels(
    recording_id: str,
    body: SpeakerLabelsUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")
    transcription.speaker_labels = body.speaker_labels
    await db.commit()
    await db.refresh(transcription)
    return transcription


@router.post("/qa-pairs", response_model=QAPairListResponse)
async def create_qa_pairs(recording_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")
    if not transcription.text or not transcription.speaker_labels:
        raise HTTPException(400, "请先完成转写和说话人标注")

    # Delete existing QA pairs
    existing = (await db.execute(
        select(QAPair).where(QAPair.transcription_id == transcription.id)
    )).scalars().all()
    for qa in existing:
        await db.delete(qa)

    # Extract new ones
    try:
        pairs = await extract_qa_pairs(transcription.text, transcription.speaker_labels)
    except QAExtractionError as e:
        raise HTTPException(400, str(e))

    new_pairs = []
    for i, p in enumerate(pairs):
        qa = QAPair(
            transcription_id=transcription.id,
            question=p.get("question", ""),
            answer=p.get("answer", ""),
            order_index=i,
        )
        db.add(qa)
        new_pairs.append(qa)

    await db.commit()
    for qa in new_pairs:
        await db.refresh(qa)

    return QAPairListResponse(
        qa_pairs=[QAPairResponse.model_validate(qa) for qa in new_pairs],
        speaker_labels=transcription.speaker_labels,
    )


@router.get("/qa-pairs", response_model=QAPairListResponse)
async def list_qa_pairs(recording_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")

    result = await db.execute(
        select(QAPair)
        .where(QAPair.transcription_id == transcription.id)
        .order_by(QAPair.order_index)
    )
    qa_pairs = result.scalars().all()

    return QAPairListResponse(
        qa_pairs=[QAPairResponse.model_validate(qa) for qa in qa_pairs],
        speaker_labels=transcription.speaker_labels,
    )


@router.post("/suggestions", response_model=QAPairListResponse)
async def create_suggestions(recording_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transcription).where(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()
    if not transcription:
        raise HTTPException(404, "Transcription not found")

    result = await db.execute(
        select(QAPair)
        .where(QAPair.transcription_id == transcription.id)
        .order_by(QAPair.order_index)
    )
    qa_pairs = result.scalars().all()

    if not qa_pairs:
        raise HTTPException(400, "请先提取问答对")

    for qa in qa_pairs:
        try:
            suggestions = await generate_suggestions(qa.question, qa.answer)
            qa.suggestions = suggestions
        except SuggestionError:
            qa.suggestions = ["建议生成失败，请重试"]

    await db.commit()
    for qa in qa_pairs:
        await db.refresh(qa)

    return QAPairListResponse(
        qa_pairs=[QAPairResponse.model_validate(qa) for qa in qa_pairs],
        speaker_labels=transcription.speaker_labels,
    )
