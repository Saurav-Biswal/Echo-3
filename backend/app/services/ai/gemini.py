"""Gemini-backed intent extraction.

Speaks the same :class:`AIProvider` contract as the mock, so the pipeline never
learns it is talking to Gemini. Responsibilities that live *only* here:

* handing the model :class:`IntentAnalysis` as a response schema so structure is
  enforced at generation time (§10);
* uploading video/image via the Files API when they exceed the inline limit, and
  waiting for the file to become ACTIVE;
* retrying transient failures, then falling back to the lighter model;
* re-validating the returned JSON and attempting one repair before giving up.

The API key is read from settings, which read it from the environment - it is
never passed in from, or exposed to, a client (§40).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas.ai_output import IntentAnalysis
from app.services.ai.base import AIProvider, AnalysisResult
from app.services.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.services.media.normalized import NormalizedMedia
from app.utils.errors import (
    AiError,
    AiRateLimitedError,
    AiTimeoutError,
    MalformedAiOutputError,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

_RATE_LIMIT_MARKERS = ("429", "rate limit", "resource_exhausted", "quota")
_TIMEOUT_MARKERS = ("timeout", "deadline", "504")
# A retired or misspelled model name is a configuration fault, not a blip:
# retrying it three times only delays a failure that will never succeed.
_PERMANENT_MARKERS = ("404", "not_found", "is not found", "no longer available")


class GeminiAIProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        from google import genai  # imported lazily so the mock path needs no SDK

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._models = [settings.gemini_model, settings.gemini_fallback_model]

    async def analyze(self, media: NormalizedMedia) -> AnalysisResult:
        contents = await self._build_contents(media)

        last_error: Exception | None = None
        for model in _unique(self._models):
            for attempt in range(1, settings.gemini_max_attempts + 1):
                try:
                    analysis = await self._generate(model, contents)
                    logger.info(
                        "ai.gemini_ok", model=model, attempt=attempt,
                        category=analysis.category.value,
                        confidence=analysis.confidence,
                    )
                    return AnalysisResult(analysis=analysis, model=model)
                except MalformedAiOutputError as exc:
                    last_error = exc
                    logger.warning("ai.gemini_malformed", model=model, attempt=attempt)
                    break  # a different model is more likely to help than a retry
                except AiRateLimitedError as exc:
                    last_error = exc
                    await asyncio.sleep(min(2 ** attempt, 8))
                except AiError as exc:
                    last_error = exc
                    logger.warning(
                        "ai.gemini_error",
                        model=model,
                        attempt=attempt,
                        code=exc.code,
                        detail=exc.detail,
                    )
                    if not exc.permanent and attempt < settings.gemini_max_attempts:
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    break
        raise last_error or AiError(detail="gemini produced no result")

    # --------------------------------------------------------------- internals

    async def _generate(self, model: str, contents: list[Any]) -> IntentAnalysis:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=IntentAnalysis,
            temperature=0.2,
        )
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=model, contents=contents, config=config
                ),
                timeout=settings.gemini_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise AiTimeoutError(detail=f"{model} timed out") from exc
        except Exception as exc:  # SDK raises a variety of provider errors
            raise _classify_ai_error(exc) from exc

        return _validate_response(response)

    async def _build_contents(self, media: NormalizedMedia) -> list[Any]:
        prompt = build_user_prompt(media)
        parts: list[Any] = [prompt]

        attachment = None
        if media.has_video and media.local_path is not None:
            attachment = await self._as_part(media.local_path, media.mime_type or "video/mp4")
        elif media.has_image and media.local_path is not None:
            attachment = await self._as_part(media.local_path, media.mime_type or "image/jpeg")

        if attachment is not None:
            parts.append(attachment)
        return parts

    async def _as_part(self, path: Path, mime_type: str) -> Any:
        from google.genai import types

        size = path.stat().st_size
        data = path.read_bytes()
        if size <= settings.gemini_inline_upload_limit_bytes:
            return types.Part.from_bytes(data=data, mime_type=mime_type)
        return await self._upload_file(path, mime_type)

    async def _upload_file(self, path: Path, mime_type: str) -> Any:
        uploaded = await self._client.aio.files.upload(
            file=str(path), config={"mime_type": mime_type}
        )
        deadline = settings.gemini_file_active_timeout_seconds
        waited = 0.0
        while getattr(uploaded.state, "name", str(uploaded.state)) == "PROCESSING":
            if waited >= deadline:
                raise AiTimeoutError(detail="uploaded file stuck in PROCESSING")
            await asyncio.sleep(2.0)
            waited += 2.0
            uploaded = await self._client.aio.files.get(name=uploaded.name)
        if getattr(uploaded.state, "name", str(uploaded.state)) == "FAILED":
            raise AiError(detail="uploaded file failed to process")
        return uploaded


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def _validate_response(response: Any) -> IntentAnalysis:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, IntentAnalysis):
        return parsed
    text = getattr(response, "text", None)
    if not text:
        raise MalformedAiOutputError(detail="empty response from model")
    try:
        payload = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise MalformedAiOutputError(detail="response was not valid JSON") from exc
    try:
        return IntentAnalysis.model_validate(payload)
    except Exception as exc:  # pydantic ValidationError
        raise MalformedAiOutputError(detail=f"schema validation failed: {exc}"[:300]) from exc


def _classify_ai_error(exc: Exception) -> AiError:
    message = str(exc).lower()
    if any(marker in message for marker in _RATE_LIMIT_MARKERS):
        return AiRateLimitedError(detail=str(exc)[:300])
    if any(marker in message for marker in _TIMEOUT_MARKERS):
        return AiTimeoutError(detail=str(exc)[:300])
    error = AiError(detail=f"{type(exc).__name__}: {exc}"[:300])
    if any(marker in message for marker in _PERMANENT_MARKERS):
        # Skip straight to the fallback model instead of retrying a name the
        # API has already told us it will never serve.
        error.permanent = True
    return error
