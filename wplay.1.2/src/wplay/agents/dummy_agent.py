# src/wplay/agents/dummy_agent.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
import json
import random
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class DummyAgent:
    """
    Agent simple para testing:
      - act(...) devuelve `action_value` (o aleatorio si action_value is None)
      - observe(transition) añade a buffer, guarda last_transition y aumenta counter
      - save(path) / load(path) para persistencia simple JSON
      - reset() para limpiar buffer y contador
      - compatible con registry.build(..., deterministic=True, ...) (acepta **kwargs)
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        action_value: Optional[int] = 0,
        deterministic: bool = False,
        hparams: Optional[Dict[str, Any]] = None,
        buffer_capacity: int = 1000,
        save_name: str = "dummy_agent_state.json",
        **kwargs,
    ):
        # identity
        self.agent_id = agent_id or "dummy"
        # behavior
        self.action_value = action_value
        self.deterministic = bool(deterministic)
        # simple internal state
        self.counter = 0
        self._buffer = []  # internal replay-like buffer
        self.buffer_capacity = int(buffer_capacity) if buffer_capacity is not None else 1000
        self.last_transition: Optional[Dict[str, Any]] = None
        self.hparams = hparams or {}
        self.save_name = save_name

    # properties helpers expected by tests
    @property
    def buffer_len(self) -> int:
        return len(self._buffer)

    # expose buffer for tests which may check len or iter (but keep underscore to discourage mutation)
    @property
    def buffer(self):
        return self._buffer

    def act(self, state: Any = None, deterministic: Optional[bool] = None) -> Any:
        """Return action. If deterministic argument provided, use it, otherwise fallback to self.deterministic"""
        use_det = self.deterministic if deterministic is None else bool(deterministic)
        if self.action_value is not None:
            return self.action_value
        # fallback: deterministic => 0 else random int small
        return 0 if use_det else random.randint(0, 3)

    def observe(self, transition: Dict[str, Any]) -> None:
        """Record transition into internal buffer, update last_transition and counter."""
        # minimal validation
        if not isinstance(transition, dict):
            logger.warning("DummyAgent.observe expects dict transition, got %s", type(transition))
            return
        self.last_transition = transition
        # append limited-capacity buffer
        if self.buffer_capacity <= 0:
            return
        if len(self._buffer) >= self.buffer_capacity:
            # simple ring behavior: drop oldest
            self._buffer.pop(0)
        self._buffer.append(transition)
        self.counter += 1

    # Persistence API used by tests
    def save(self, path: str) -> None:
        """
        Save a minimal JSON state into `path/<save_name>`.
        Tests expect a file exists at path / 'dummy_agent_state.json'.
        """
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        state = {
            "agent_id": self.agent_id,
            "action_value": self.action_value,
            "deterministic": self.deterministic,
            "counter": self.counter,
            "buffer": list(self._buffer),
            "buffer_capacity": self.buffer_capacity,
            "last_transition": self.last_transition,
            "hparams": self.hparams,
        }
        (p / self.save_name).write_text(json.dumps(state, indent=2), encoding="utf8")

    def load(self, path: str) -> None:
        """Load state from `path/<save_name>` if exists. Missing keys are ignored."""
        f = Path(path) / self.save_name
        if not f.exists():
            raise FileNotFoundError(f"DummyAgent.load: no state file at {str(f)}")
        data = json.loads(f.read_text(encoding="utf8"))
        # restore known fields (safe)
        self.agent_id = data.get("agent_id", self.agent_id)
        self.action_value = data.get("action_value", self.action_value)
        self.deterministic = bool(data.get("deterministic", self.deterministic))
        self.counter = int(data.get("counter", self.counter or 0))
        buf = data.get("buffer", [])
        # ensure it's a list
        self._buffer = list(buf) if isinstance(buf, (list, tuple)) else []
        self.buffer_capacity = int(data.get("buffer_capacity", self.buffer_capacity))
        self.last_transition = data.get("last_transition", self.last_transition)
        self.hparams = data.get("hparams", self.hparams or {})

    def reset(self) -> None:
        """Reset agent internal runtime state while keeping configuration (action_value/hparams)."""
        self.counter = 0
        self._buffer = []
        self.last_transition = None

    # helper for nicer debugging
    def __repr__(self) -> str:
        return f"<DummyAgent id={self.agent_id!r} action_value={self.action_value!r} counter={self.counter} buffer_len={self.buffer_len}>"
