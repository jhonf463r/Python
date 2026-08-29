"""Ollama Model Discovery Service - Discovers and Downloads Free Models.

This service automatically discovers free models available on Ollama library,
downloads suitable models, and ensures the system has the best free models
available for its reasoning capabilities.

Tier: Provider Management (Local)
Priority: HIGH - ensures free models are always available without API keys
Integration: OllamaExpertProvider + CloudReasoningActivator
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelDiscoveryResult:
    """Resultado de descubrimiento/descarga de modelo."""
    model_name: str
    action: str  # 'discovered', 'downloaded', 'skipped', 'error'
    reason: str
    size_gb: float = 0.0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OllamaModelDiscoveryService:
    """Discovers and downloads free Ollama models automatically."""

    # Free models that are good for different use cases
    FREE_MODELS = {
        'phi3': {
            'name': 'phi3',
            'size_gb': 2.5,
            'description': 'Microsoft Phi-3: small but capable',
            'use_case': 'general',
            'priority': 'high',
        },
        'llama3.1': {
            'name': 'llama3.1',
            'size_gb': 4.0,
            'description': 'Meta Llama 3.1: capable all-around model',
            'use_case': 'general',
            'priority': 'high',
        },
        'qwen2.5': {
            'name': 'qwen2.5',
            'size_gb': 4.5,
            'description': 'Alibaba Qwen 2.5: strong reasoning',
            'use_case': 'reasoning',
            'priority': 'high',
        },
        'gemma2': {
            'name': 'gemma2',
            'size_gb': 3.0,
            'description': 'Google Gemma 2: lightweight and capable',
            'use_case': 'lightweight',
            'priority': 'medium',
        },
        'mistral': {
            'name': 'mistral',
            'size_gb': 4.0,
            'description': 'Mistral 7B: strong general model',
            'use_case': 'general',
            'priority': 'medium',
        },
    }

    def __init__(
        self,
        ollama_provider: Any | None = None,
        evolution_dir: str | None = None,
        auto_start: bool | None = None,
        check_interval_seconds: float = 3600.0,
    ) -> None:
        self.ollama_provider = ollama_provider
        self.evolution_dir = Path(evolution_dir) if evolution_dir else None
        self.check_interval_seconds = max(float(check_interval_seconds), 300.0)
        self._auto_start = (not self._in_test_mode()) if auto_start is None else bool(auto_start)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._discovery_history: list[ModelDiscoveryResult] = []
        self._available_models: set[str] = set()
        self._load_history()

        if self._auto_start:
            self.start()

    def _in_test_mode(self) -> bool:
        import os
        return os.environ.get('IABV_TEST_MODE', '').lower() in ('1', 'true')

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name='iabv-ollama-model-discovery',
            daemon=True
        )
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout_seconds)

    def _monitor_loop(self) -> None:
        """Background loop for periodic model discovery."""
        while not self._stop_event.is_set():
            try:
                self.discover_and_download_models()
            except Exception as exc:
                logger.warning('ollama_model_discovery loop error: %s', exc)
            self._stop_event.wait(self.check_interval_seconds)

    def discover_and_download_models(self) -> list[ModelDiscoveryResult]:
        """Discover available models and download free ones if needed."""
        # RESOURCE GUARD: Check if model discovery is allowed
        try:
            from iabv_v15.services.resource_guard import get_resource_guard
            guard = get_resource_guard()
            decision = guard.check_action_allowed(
                action="ollama_model_discovery",
                estimated_ram_mb=500,  # Model downloads are expensive
                goal_required=False,
                essential=False,
            )
            if not decision.allowed:
                result = ModelDiscoveryResult(
                    model_name='ollama',
                    action='skipped',
                    reason=f"Resource guard: {decision.reason}",
                )
                return [result]
        except Exception:
            # If guard fails, proceed (fail-safe)
            pass

        results = []
        ollama = shutil.which('ollama') or str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe')

        if not ollama:
            result = ModelDiscoveryResult(
                model_name='ollama',
                action='error',
                reason='Ollama not found, cannot discover models'
            )
            return [result]

        # Get currently installed models
        current_models = self._get_installed_models()
        with self._lock:
            self._available_models = set(current_models)

        # Download free high-priority models if not installed
        for model_key, model_info in self.FREE_MODELS.items():
            if model_info['priority'] == 'high' and model_key not in self._available_models:
                download_result = self._download_model(model_key)
                results.append(download_result)
                with self._lock:
                    if download_result.action == 'downloaded':
                        self._available_models.add(model_key)

        if results:
            logger.info(f'OllamaModelDiscovery: {len(results)} operations')
            self._save_history()

        return results

    def _get_installed_models(self) -> list[str]:
        """Get list of currently installed Ollama models."""
        if not self._check_ollama_available():
            return []
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                models = []
                for line in result.stdout.strip().splitlines()[1:]:  # Skip header
                    parts = [p.strip() for p in line.split()]
                    if parts:
                        models.append(parts[0])
                return models
        except Exception as exc:
            logger.warning('Failed to get installed Ollama models: %s', exc)
        return []

    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        ollama = shutil.which('ollama') or str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe')
        return bool(ollama)

    def _download_model(self, model_name: str) -> ModelDiscoveryResult:
        """Download a free Ollama model."""
        if not self._check_ollama_available():
            return ModelDiscoveryResult(
                model_name=model_name,
                action='error',
                reason='Ollama not available'
            )

        model_info = self.FREE_MODELS.get(model_name, {})
        if not model_info:
            return ModelDiscoveryResult(
                model_name=model_name,
                action='skipped',
                reason=f'Model {model_name} not in free models catalog'
            )

        try:
            # Check disk space before download
            if model_info['size_gb'] > 10:  # Large model
                disk_free_gb = self._get_disk_free_gb()
                if disk_free_gb < model_info['size_gb'] * 2:  # Need 2x space margin
                    return ModelDiscoveryResult(
                        model_name=model_name,
                        action='skipped',
                        reason=f'Insufficient disk space (need {model_info["size_gb"] * 2}GB, have {disk_free_gb}GB)'
                    )

            # Download model
            result = subprocess.run(
                ['ollama', 'pull', model_name],
                capture_output=True, text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                return ModelDiscoveryResult(
                    model_name=model_name,
                    action='downloaded',
                    reason=f'Successfully downloaded {model_info["description"]}',
                    size_gb=model_info['size_gb']
                )
            else:
                return ModelDiscoveryResult(
                    model_name=model_name,
                    action='error',
                    reason=f'Ollama pull failed: {result.stderr}'
                )

        except Exception as exc:
            return ModelDiscoveryResult(
                model_name=model_name,
                action='error',
                reason=f'Download failed: {str(exc)}'
            )

    def _get_disk_free_gb(self) -> float:
        """Get free disk space in GB."""
        try:
            import shutil
            disk = shutil.disk_usage(self.evolution_dir if self.evolution_dir else Path.cwd())
            return disk.free / (1024**3)
        except Exception:
            return 0.0

    def get_available_models(self) -> list[str]:
        """Get list of available Ollama models."""
        with self._lock:
            return list(self._available_models)

    def recommend_model_for_query(self, complexity: str) -> str | None:
        """Recommend a model based on query complexity."""
        available = self.get_available_models()

        if not available:
            return None

        # Simple queries: any model works
        if complexity == 'simple':
            return available[0]

        # Medium/Complex: prefer models with better reasoning
        reasoning_models = ['qwen2.5', 'llama3.1', 'mistral']
        for model in reasoning_models:
            if model in available:
                return model

        # Fallback to first available
        return available[0]

    def _load_history(self) -> None:
        """Load discovery history from disk."""
        if not self.evolution_dir:
            return
        history_file = self.evolution_dir / 'ollama_model_discovery_history.json'
        if not history_file.exists():
            return
        try:
            data = json.loads(history_file.read_text(encoding='utf-8'))
            for result_data in data:
                try:
                    self._discovery_history.append(ModelDiscoveryResult(**result_data))
                except Exception:
                    continue
                # Track available models
                if result_data.get('action') == 'downloaded':
                    self._available_models.add(result_data.get('model_name'))
        except Exception as exc:
            logger.warning('Failed to load discovery history: %s', exc)

    def _save_history(self) -> None:
        """Save discovery history to disk."""
        if not self.evolution_dir:
            return
        history_file = self.evolution_dir / 'ollama_model_discovery_history.json'
        self.evolution_dir.mkdir(parents=True, exist_ok=True)
        try:
            data = [r.__dict__ if hasattr(r, '__dict__') else r for r in self._discovery_history]
            history_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as exc:
            logger.warning('Failed to save discovery history: %s', exc)

    def get_discovery_summary(self) -> dict[str, Any]:
        """Get summary of discovery activity."""
        with self._lock:
            total = len(self._discovery_history)
            downloaded = sum(1 for r in self._discovery_history if r.action == 'downloaded')
            errors = sum(1 for r in self._discovery_history if r.action == 'error')
            skipped = sum(1 for r in self._discovery_history if r.action == 'skipped')

            return {
                'total_discovery_operations': total,
                'models_downloaded': downloaded,
                'download_errors': errors,
                'skipped_operations': skipped,
                'available_models': list(self._available_models),
                'catalog_size': len(self.FREE_MODELS),
                'last_discovery': self._discovery_history[-1].timestamp_utc if self._discovery_history else None,
                'check_interval_seconds': self.check_interval_seconds,
                'last_updated': datetime.now(timezone.utc).isoformat(),
            }
