from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: str
    filename: str
    source_type: str
    file_path: str
    duration: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    id: str
    recording_id: str
    text: Optional[str]
    speaker_labels: Optional[dict]
    status: str
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionUpdate(BaseModel):
    text: str


class SpeakerLabelsUpdate(BaseModel):
    speaker_labels: Dict[str, str]


class QAPairResponse(BaseModel):
    id: str
    transcription_id: str
    question: str
    answer: str
    order_index: int
    suggestions: Optional[List[str]]
    created_at: datetime

    model_config = {"from_attributes": True}


class QAPairListResponse(BaseModel):
    qa_pairs: List[QAPairResponse]
    speaker_labels: Optional[dict]


class AutoQAPairPreview(BaseModel):
    question: str
    answer: str


class AutoQAPairPreviewResponse(BaseModel):
    qa_pairs: List[AutoQAPairPreview]
