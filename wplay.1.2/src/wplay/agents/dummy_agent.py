from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, List
import json
import copy
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class DummyAgent:
    """
    Agente trivial para tests:
      - act(): devuelve un valor fijo (action_value) o sample aleatorio si configurable.
      - observe(transition): guarda transiciones en buffer, actualiza last_transition y counter.
      - save(path) / load(path): persistencia simple en JSON en path/dummy_agent_state.json
    """

    def __init__(
        self,
        agent_id: str = "dummy_agent",
        action_value: Any = 0,
        hparams: Optional[Dict[str, Any]] = None,
        deterministic: bool = True,
    ):
        """
        Args:
            agent_id: identificador del agente (string)
            action_value: valor que devuelve en act() cuando es determinista
            hparams: diccionario de hiperparámetros (se clona internamente)
            deterministic: si True `act()` retorna siempre `action_value`
        """
        self.agent_id = str(agent_id)
        self.action_value = action_value
        self.hparams = copy.deepcopy(hparams) if hparams is not None else {}
        self.deterministic = bool(deterministic)

        # buffer de observaciones (lista de dicts)
        self.buffer: List[Dict[str, Any]] = []
        # última transición observada
        self.last_transition: Optional[Dict[str, Any]] = None
        # contador de observaciones / acciones (útil para tests)
        self.counter: int = 0

    def act(self, state: Optional[Any] = None, deterministic: Optional[bool] = None) -> Any:
        """
        Devuelve acción. Si deterministic is None se usa self.deterministic.
        Esta implementación es deliberadamente simple para tests.
        """
        use_det = self.deterministic if deterministic is None else bool(deterministic)
        if use_det:
            action = self.action_value
        else:
            # comportamiento no determinista simple: variar ligeramente si es numérico
            try:
                # para números, devolver un int cercano
                if isinstance(self.action_value, (int, float)):
                    import random
                    action = self.action_value if isinstance(self.action_value, int) else float(self.action_value)
                    # pequeña aleatoriedad
                    if isinstance(self.action_value, int):
                        action = int(self.action_value + random.choice([-1, 0, 1]))
                else:
                    action = self.action_value
            except Exception:
                action = self.action_value
        # aumentar contador de acciones tomadas
        self.counter += 1
        return action

    def observe(self, transition: Dict[str, Any]) -> None:
        """
        Recibe una transición y la almacena en buffer; actualiza last_transition y counter.
        transition es un dict con keys típicas: {'s','a','r','s2','done'}.
        """
        if not isinstance(transition, dict):
            logger.warning("DummyAgent.observe received non-dict transition; ignoring")
            return
        # clonar por seguridad
        t = copy.deepcopy(transition)
        self.buffer.append(t)
        self.last_transition = t
        # contar observaciones también (tests esperan counter increment)
        self.counter += 1

    @property
    def buffer_len(self) -> int:
        return len(self.buffer)

    # --- persistencia simple ---
    def save(self, path: str) -> None:
        """
        Guarda el estado esencial del agente en `path/dummy_agent_state.json`.
        `path` puede ser directorio o ruta a un directorio inexistente (se crea).
        """
        p = Path(path)
        if p.is_file():
            # si pasaron archivo, usar su parent
            p = p.parent
        p.mkdir(parents=True, exist_ok=True)
        out = {
            "agent_id": self.agent_id,
            "action_value": self.action_value,
            "hparams": self.hparams,
            "deterministic": self.deterministic,
            "buffer": self.buffer,
            "last_transition": self.last_transition,
            "counter": self.counter,
        }
        state_file = p / "dummy_agent_state.json"
        state_file.write_text(json.dumps(out, indent=2), encoding="utf8")

    def load(self, path: str) -> None:
        """
        Carga estado desde `path/dummy_agent_state.json` o desde el path directo si le pasaron el archivo.
        """
        p = Path(path)
        if p.is_file():
            state_file = p
        else:
            state_file = p / "dummy_agent_state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"DummyAgent.load: state file not found: {state_file}")
        data = json.loads(state_file.read_text(encoding="utf8"))
        # restaurar campos esperados, con tolerancia si faltan algunos
        self.agent_id = data.get("agent_id", self.agent_id)
        self.action_value = data.get("action_value", self.action_value)
        self.hparams = data.get("hparams", self.hparams) or {}
        self.deterministic = bool(data.get("deterministic", self.deterministic))
        self.buffer = data.get("buffer", []) or []
        self.last_transition = data.get("last_transition", self.last_transition)
        self.counter = int(data.get("counter", self.counter))
