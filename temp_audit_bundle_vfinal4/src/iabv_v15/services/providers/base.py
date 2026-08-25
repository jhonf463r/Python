from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from iabv_v15.domain.models import InferenceRequest, InferenceResult, ProviderHealth


class ProviderUnavailableError(RuntimeError):
    pass


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        raise NotImplementedError

    @abstractmethod
    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        raise NotImplementedError

    @abstractmethod
    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        raise NotImplementedError

    @abstractmethod
    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        raise NotImplementedError

    @staticmethod
    def images_as_input(screenshots: list[str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for screenshot in screenshots:
            items.append({"type": "input_image", "image_url": f"file://{screenshot}"})
        return items
