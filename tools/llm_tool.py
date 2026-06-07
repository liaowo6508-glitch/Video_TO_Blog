from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from config.settings import settings


class LLMService(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        json_schema: Optional[str] = None,
    ) -> str:
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

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        json_schema: Optional[str] = None,
    ) -> str:
        if not settings.deepseek_api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY is not set")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})

        # 构造带 JSON schema 或 few-shot 的 user prompt
        if json_mode and json_schema:
            user_content = (
                f"{prompt}\n\n"
                f"请严格按照以下 JSON Schema 输出，不要包含任何额外文字：\n"
                f"```json\n{json_schema}\n```"
            )
        elif json_mode:
            user_content = (
                f"{prompt}\n\n"
                "请严格按照 JSON 格式输出，不要包含任何额外文字。"
            )
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        kwargs: dict[str, object] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
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
