import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from openai import AsyncOpenAI, AuthenticationError


class TranscriptionError(Exception):
    pass


# ── Volcengine ASR ──────────────────────────────────────────────

VOLC_HOST = "openspeech.bytedance.com"
VOLC_SUBMIT = f"https://{VOLC_HOST}/api/v1/vc/submit"
VOLC_QUERY = f"https://{VOLC_HOST}/api/v1/vc/query"

PROXY_URL = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", ""))


def _volc_sign(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _volc_authorization(method: str, path: str, query: str, headers: dict, body: bytes) -> str:
    ak = os.getenv("VOLC_ACCESS_KEY", "")
    sk = os.getenv("VOLC_SECRET_KEY", "")
    if not ak or not sk:
        raise TranscriptionError("请检查火山引擎 Access Key / Secret Key 配置")

    signed_headers = "content-type;host;x-date"
    x_date = headers["X-Date"]

    canonical = (
        f"{method}\n{path}\n{query}\n"
        f"content-type:{headers['content-type']}\n"
        f"host:{headers['host']}\n"
        f"x-date:{x_date}\n"
        f"\n{signed_headers}\n"
        f"{hashlib.sha256(body).hexdigest()}"
    )

    credential_scope = x_date[:8] + "/cn-north-1/openspeech/request"
    string_to_sign = (
        f"HMAC-SHA256\n{x_date}\n{credential_scope}\n"
        + hashlib.sha256(canonical.encode()).hexdigest()
    )

    k_date = _volc_sign(sk, x_date[:8])
    k_region = _volc_sign(k_date, "cn-north-1")
    k_service = _volc_sign(k_region, "openspeech")
    signing_key = _volc_sign(k_service, "request")

    signature = _volc_sign(signing_key, string_to_sign)

    return (
        f"HMAC-SHA256 "
        f"Credential={ak}/{credential_scope}, "
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

    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    if PROXY_URL:
        print(f"[Volcengine] 使用代理: {PROXY_URL}")

    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")

    with open(full_path, "rb") as f:
        resp = requests.post(
            VOLC_SUBMIT,
            data={"appid": app_id},
            files={"audio": (full_path.name, f, f"audio/{full_path.suffix.lstrip('.')}")},
            headers={
                "Host": VOLC_HOST,
                "X-Date": x_date,
            },
            auth=_VolcAuth(app_id),
            timeout=60,
            proxies=proxies,
        )

    result = resp.json()
    if result.get("code") != 1000:
        raise TranscriptionError(f"火山引擎提交失败: {result.get('message', '未知错误')}")

    task_id = result["task"]["id"]

    for _ in range(120):
        time.sleep(2)
        x_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        resp = requests.get(
            VOLC_QUERY,
            params={"appid": app_id, "id": task_id},
            headers={"Host": VOLC_HOST, "X-Date": x_date},
            auth=_VolcAuth(app_id),
            timeout=30,
            proxies=proxies,
        )
        q = resp.json()
        status = q.get("task", {}).get("status", "")
        if status == "success":
            utterances = q.get("task", {}).get("utterances", [])
            if not utterances:
                return q.get("task", {}).get("text", "")
            lines = []
            for u in utterances:
                speaker = u.get("speaker", "?")
                text = u.get("text", "").strip()
                if text:
                    lines.append(f"[说话人 {speaker}] {text}")
            return "\n\n".join(lines)
        if status == "failed":
            raise TranscriptionError(f"火山引擎转写失败: {q.get('task', {}).get('message', '')}")

    raise TranscriptionError("转写超时，请重试")


class _VolcAuth(requests.auth.AuthBase):
    def __init__(self, app_id: str):
        self.app_id = app_id

    def __call__(self, r):
        r.headers["Host"] = VOLC_HOST
        x_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        r.headers["X-Date"] = x_date
        body = r.body or b""
        path = urlparse(r.url).path
        query = urlparse(r.url).query
        r.headers["Authorization"] = _volc_authorization(
            r.method,
            path,
            query,
            {"host": VOLC_HOST, "x-date": x_date, "content-type": r.headers.get("Content-Type", "")},
            body if isinstance(body, bytes) else body.encode(),
        )
        return r


# ── OpenAI ASR ──────────────────────────────────────────────────

async def _transcribe_openai(file_path: str, source_type: str) -> str:
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


# ── Whisper.cpp fallback ────────────────────────────────────────

def _looks_like_free_fallback_enabled() -> bool:
    return os.getenv("TRANSCRIBE_FALLBACK", "whisper").lower() in {"whisper", "local", "free"}


def _parse_target_language() -> str | None:
    value = os.getenv("WHISPER_LANGUAGE", "").strip()
    return value or None


def _transcribe_local_whisper(file_path: str) -> str:
    full_path = Path(file_path)
    if not full_path.exists():
        raise TranscriptionError("音频文件不存在")

    model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise TranscriptionError(f"本地转写依赖未安装: {str(e)}")

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments, _info = model.transcribe(str(full_path), vad_filter=True, language=_parse_target_language())
        lines = []
        for segment in segments:
            text = (segment.text or "").strip()
            if text:
                lines.append(text)
        if not lines:
            raise TranscriptionError("本地转写未返回文本")
        return "\n".join(lines)
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"本地转写失败: {str(e)}")


# ── Dispatcher ──────────────────────────────────────────────────

async def transcribe_audio(file_path: str, source_type: str) -> str:
    volc_ak = os.getenv("VOLC_ACCESS_KEY", "")
    if volc_ak:
        return _transcribe_volc(file_path)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        return await _transcribe_openai(file_path, source_type)

    if _looks_like_free_fallback_enabled():
        return _transcribe_local_whisper(file_path)

    raise TranscriptionError("请检查 OpenAI API Key 配置")
