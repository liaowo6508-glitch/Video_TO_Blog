from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from config.settings import settings


class ASRService(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        ...


class LocalWhisperASR(ASRService):
    def __init__(
        self,
        model: str | None = None,
    ) -> None:
        import whisper

        self.model_name = model or settings.local_whisper_model
        self.model = whisper.load_model(self.model_name)

    def transcribe(self, audio_path: str) -> str:
        audio_p = Path(audio_path)
        if not audio_p.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        result = self.model.transcribe(
            str(audio_p),
            language="zh",
            fp16=False,
        )
        return result.get("text", "")


class GroqASRService(ASRService):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from groq import Groq

        self.client = Groq(api_key=api_key or settings.groq_api_key or "")
        self.model = model or settings.groq_model

    def transcribe(self, audio_path: str) -> str:
        if not settings.groq_api_key:
            raise EnvironmentError("GROQ_API_KEY is not set")
        audio_p = Path(audio_path)
        if not audio_p.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with audio_p.open("rb") as f:
            transcript = self.client.audio.transcriptions.create(
                file=(audio_p.name, f.read(), "audio/wav"),
                model=self.model,
                response_format="text",
                language="zh",
            )
        return transcript.text or ""


class ASRServiceFactory:
    _services: dict[str, type[ASRService]] = {
        "groq": GroqASRService,
        "local_whisper": LocalWhisperASR,
    }

    @classmethod
    def get(cls, provider: str | None = None, **kwargs: str) -> ASRService:
        provider = provider or settings.asr_provider
        if provider not in cls._services:
            raise ValueError(
                f"Unknown ASR provider: {provider}. "
                f"Available: {list(cls._services.keys())}"
            )
        return cls._services[provider](**kwargs)


def get_asr_service(provider: str | None = None) -> ASRService:
    return ASRServiceFactory.get(provider)


_asr_service: ASRService | None = None


def get_asr() -> ASRService:
    global _asr_service
    if _asr_service is None:
        _asr_service = get_asr_service()
    return _asr_service
