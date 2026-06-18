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
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionUpdate(BaseModel):
    text: str
