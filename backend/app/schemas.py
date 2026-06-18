from datetime import datetime

from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: str
    filename: str
    source_type: str
    file_path: str
    duration: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    id: str
    recording_id: str
    text: str | None
    speaker_labels: dict | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionUpdate(BaseModel):
    text: str


class SpeakerLabelsUpdate(BaseModel):
    speaker_labels: dict[str, str]


class QAPairResponse(BaseModel):
    id: str
    transcription_id: str
    question: str
    answer: str
    order_index: int
    suggestions: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QAPairListResponse(BaseModel):
    qa_pairs: list[QAPairResponse]
    speaker_labels: dict | None
