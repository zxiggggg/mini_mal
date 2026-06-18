import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openai import AsyncOpenAI, AuthenticationError


class TranscriptionError(Exception):
    pass


# ── Volcengine ASR ──────────────────────────────────────────────

VOLC_HOST = "openspeech.bytedance.com"
VOLC_SUBMIT = f"https://{VOLC_HOST}/api/v1/vc/submit"
VOLC_QUERY = f"https://{VOLC_HOST}/api/v1/vc/query"


def _volc_sign(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _volc_authorization(method: str, path: str, query: str, headers: dict, body: bytes) -> str:
    ak = os.getenv("VOLC_ACCESS_KEY", "")
    sk = os.getenv("VOLC_SECRET_KEY", "")
    if not ak or not sk:
        raise TranscriptionError("请检查火山引擎 Access Key / Secret Key 配置")

    # Build signed headers
    signed_headers = "content-type;host;x-date"
    x_date = headers.get("X-Date", "")

    # Canonical request
    canonical = f"{method}\n{path}\n{query}\n"
    canonical += f"content-type:{headers.get('Content-Type', '')}\n"
    canonical += f"host:{headers.get('Host', '')}\n"
    canonical += f"x-date:{x_date}\n"
    canonical += f"\n{signed_headers}\n"
    canonical += hashlib.sha256(body).hexdigest()

    # String to sign
    credential_scope = x_date[:8] + "/cn-north-1/openspeech/request"
    string_to_sign = (
        f"HMAC-SHA256\n{x_date}\n{credential_scope}\n"
        + hashlib.sha256(canonical.encode()).hexdigest()
    )

    # Signing key
    k_date = _volc_sign(sk, x_date[:8])
    k_region = _volc_sign(k_date, "cn-north-1")
    k_service = _volc_sign(k_region, "openspeech")
    signing_key = _volc_sign(k_service, "request")

    signature = _volc_sign(signing_key, string_to_sign)

    return (
        f"HMAC-SHA256 "
        f"Credential={ak}/{x_date[:8]}/cn-north-1/openspeech/request, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def _transcribe_volc(file_path: str) -> str:
    """Transcribe using Volcengine ASR (file recognition)."""
    app_id = os.getenv("VOLC_APP_ID", "")
    if not app_id:
        raise TranscriptionError("请检查火山引擎 App ID 配置")

    full_path = Path(file_path)
    if not full_path.exists():
        raise TranscriptionError("音频文件不存在")

    # Step 1: Submit
    boundary = uuid.uuid4().hex
    body_parts = []
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="appid"\r\n\r\n{app_id}\r\n'.encode())
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="audio"; filename="{full_path.name}"\r\n'.encode())
    body_parts.append(f"Content-Type: audio/{full_path.suffix.lstrip('.')}\r\n\r\n".encode())
    body_parts.append(full_path.read_bytes())
    body_parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    parsed = urlparse(VOLC_SUBMIT)
    headers = {
        "Host": VOLC_HOST,
        "X-Date": x_date,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    headers["Authorization"] = _volc_authorization("POST", parsed.path, "", headers, body)

    req = Request(VOLC_SUBMIT, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    if result.get("code") != 1000:
        raise TranscriptionError(f"火山引擎提交失败: {result.get('message', '未知错误')}")

    task_id = result["task"]["id"]

    # Step 2: Poll until done
    query_path = parsed.path.replace("submit", "query")
    for _ in range(120):  # max 4 minutes
        time.sleep(2)
        now = datetime.now(timezone.utc)
        x_date = now.strftime("%Y%m%dT%H%M%SZ")
        q_headers = {
            "Host": VOLC_HOST,
            "X-Date": x_date,
            "Content-Type": "application/json",
        }
        q_headers["Authorization"] = _volc_authorization("GET", query_path, f"appid={app_id}&id={task_id}", q_headers, b"")

        q_url = f"{VOLC_QUERY}?appid={app_id}&id={task_id}"
        req = Request(q_url, headers=q_headers, method="GET")
        with urlopen(req, timeout=30) as resp:
            q_result = json.loads(resp.read())

        status = q_result.get("task", {}).get("status", "")
        if status == "success":
            utterances = q_result.get("task", {}).get("utterances", [])
            if not utterances:
                return q_result.get("task", {}).get("text", "")
            lines = []
            for u in utterances:
                speaker = u.get("speaker", "?")
                text = u.get("text", "").strip()
                if text:
                    lines.append(f"[说话人 {speaker}] {text}")
            return "\n\n".join(lines)

        if status == "failed":
            raise TranscriptionError(f"火山引擎转写失败: {q_result.get('task', {}).get('message', '')}")

    raise TranscriptionError("转写超时，请重试")


# ── OpenAI ASR ──────────────────────────────────────────────────

async def _transcribe_openai(file_path: str, source_type: str) -> str:
    """Transcribe using OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise TranscriptionError("请检查 OpenAI API Key 配置")

    client = AsyncOpenAI(api_key=api_key)
    full_path = Path(file_path)

    try:
        with open(full_path, "rb") as audio:
            response = await client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio,
                response_format="verbose_json",
                **(dict(include=["diarization"]) if source_type == "direct_recording" else {}),
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


# ── Dispatcher ──────────────────────────────────────────────────

async def transcribe_audio(file_path: str, source_type: str) -> str:
    """Transcribe audio. Uses Volcengine if configured, otherwise OpenAI."""
    volc_ak = os.getenv("VOLC_ACCESS_KEY", "")
    if volc_ak:
        return _transcribe_volc(file_path)
    else:
        return await _transcribe_openai(file_path, source_type)
