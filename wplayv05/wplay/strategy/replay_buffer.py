# wplay/strategy/replay_buffer.py

import random
from collections import deque
from typing import Deque, Tuple, List, Any

class ReplayBuffer:
    """
    Replay buffer simple para almacenar transiciones y muestrear minibatches.
    Cada transición es una tupla: (state, action, reward, next_state, done).
    """

    def __init__(self, max_size: int = 10000):
        """
        :param max_size: capacidad máxima del buffer.
        """
        self.buffer: Deque[Tuple[Any, int, float, Any, bool]] = deque(maxlen=max_size)

    def add(
        self,
        state: Any,
        action: int,
        reward: float,
        next_state: Any,
        done: bool
    ) -> None:
        """
        Añade una transición al buffer.
        :param state:       estado actual (vector o array).
        :param action:      acción ejecutada (int).
        :param reward:      recompensa obtenida (float).
        :param next_state:  estado resultante.
        :param done:        si el episodio terminó tras esta transición.
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> List[Tuple[Any, int, float, Any, bool]]:
        """
        Devuelve un minibatch de transiciones muestreadas aleatoriamente.
        :param batch_size: tamaño del minibatch a extraer.
        """
        if batch_size > len(self.buffer):
            raise ValueError(f"Batch size {batch_size} mayor que tamaño del buffer {len(self.buffer)}")
        return random.sample(self.buffer, batch_size)

    def size(self) -> int:
        """Número actual de transiciones almacenadas."""
        return len(self.buffer)

    def clear(self) -> None:
        """Vacía completamente el buffer."""
        self.buffer.clear()
