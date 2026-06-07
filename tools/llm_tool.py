from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from config.settings import settings


class LLMService(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        ...


class DeepSeekLLMService(LLMService):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.client = OpenAI(
            api_key=api_key or settings.deepseek_api_key or "",
            base_url=base_url or settings.deepseek_base_url,
        )
        self.model = model or settings.deepseek_model

    def generate(self, prompt: str, system: str | None = None) -> str:
        if not settings.deepseek_api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY is not set")
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""


class LLMServiceFactory:
    _services: dict[str, type[LLMService]] = {
        "deepseek": DeepSeekLLMService,
    }

    @classmethod
    def get(cls, provider: str = "deepseek", **kwargs: str) -> LLMService:
        if provider not in cls._services:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Available: {list(cls._services.keys())}"
            )
        return cls._services[provider](**kwargs)


def get_llm_service(provider: str = "deepseek") -> LLMService:
    return LLMServiceFactory.get(provider)


_llm_service: LLMService | None = None


def get_llm() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = get_llm_service(settings.llm_provider)
    return _llm_service
