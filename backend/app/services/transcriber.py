import os
from pathlib import Path

from openai import AsyncOpenAI, AuthenticationError


class TranscriptionError(Exception):
    pass


async def transcribe_audio(
    file_path: str, source_type: str
) -> str:
    """Transcribe audio file. Returns text with speaker labels."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise TranscriptionError("请检查 OpenAI API Key 配置")

    client = AsyncOpenAI(api_key=api_key)
    full_path = Path(file_path)

    try:
        if source_type == "video_call":
            # Simple transcription, no diarization needed
            with open(full_path, "rb") as audio:
                response = await client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio,
                    response_format="verbose_json",
                )
            segments = getattr(response, "segments", [])
            if segments:
                lines = [f"[说话人 {s.get('speaker', '?')}] {s.get('text', '')}" for s in segments]
                return "\n\n".join(lines)
            return response.text

        else:  # direct_recording — use diarization
            with open(full_path, "rb") as audio:
                response = await client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio,
                    response_format="verbose_json",
                    include=["diarization"],
                )
            segments = getattr(response, "segments", [])
            if segments:
                lines = [f"[说话人 {s.get('speaker', '?')}] {s.get('text', '')}" for s in segments]
                return "\n\n".join(lines)
            return response.text

    except AuthenticationError:
        raise TranscriptionError("请检查 OpenAI API Key 配置")
    except Exception as e:
        raise TranscriptionError(f"转写失败: {str(e)}")
