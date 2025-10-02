# wplay/strategy/prioritized_replay_buffer.py

import numpy as np
import random
import joblib
from collections import deque
from typing import List, Tuple, Any

class PrioritizedReplayBuffer:
    """
    Buffer de repetición con prioridades para Prioritized Experience Replay.

    Parámetros:
      - capacity: tamaño máximo del buffer.
      - alpha:    exponent para priorizado (0 = uniforme, 1 = totalmente priorizado).
      - beta:     factor de corrección de sesgo por importancia.
      - epsilon:  pequeño valor para evitar prioridades cero.
    """

    def __init__(
        self,
        capacity: int,
        alpha: float = 0.6,
        beta: float = 0.4,
        epsilon: float = 1e-6
    ):
        self.capacity   = capacity
        self.alpha      = alpha
        self.beta       = beta
        self.epsilon    = epsilon

        # Almacena las transiciones (state, action, reward, next_state, done)
        self.buffer     = []
        # Prioridades asociadas a cada posición en el buffer
        self.priorities = np.zeros((capacity,), dtype=np.float32)
        # Puntero circular para inserción
        self.pos        = 0

    def add(
        self,
        state: Any,
        action: int,
        reward: float,
        next_state: Any,
        done: bool
    ) -> None:
        """
        Añade una transición al buffer con prioridad máxima actual.
        """
        max_prio = self.priorities.max() if self.buffer else 1.0
        experience = (state, action, reward, next_state, done)

        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.pos] = experience

        self.priorities[self.pos] = max_prio
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        """
        Muestrea un minibatch de tamaño batch_size usando prioridades.
        Devuelve: states, actions, rewards, next_states, dones, indices, weights.
        """
        # 1) Obtener prioridades actuales
        buffer_size = len(self.buffer)
        if buffer_size == self.capacity:
            prios = self.priorities
        else:
            prios = self.priorities[:buffer_size]

        # 2) Elevar prioridades a alpha y normalizar
        probs = (prios + self.epsilon) ** self.alpha
        total = probs.sum()
        if not np.isfinite(total) or total == 0.0:
            # fallback a muestreo uniforme
            probs = np.ones(buffer_size, dtype=np.float64) / buffer_size
        else:
            probs = probs / total

        # 3) Muestrear índices
        indices = np.random.choice(buffer_size, batch_size, p=probs)

        # 4) Obtener muestras
        samples = [self.buffer[idx] for idx in indices]

        # 5) Calcular weights de importancia
        weights = (buffer_size * probs[indices]) ** (-self.beta)
        weights = weights / (weights.max() + 1e-8)
        weights = np.array(weights, dtype=np.float32)

        # 6) Desempaquetar batch
        states, actions, rewards, next_states, dones = zip(*samples)

        # 7) Convertir a arrays con forma consistente
        #    Se asume que cada estado es un vector de dimensión fija
        states_array      = np.vstack(states).astype(np.float32)      # shape: (batch_size, state_dim)
        next_states_array = np.vstack(next_states).astype(np.float32) # shape: (batch_size, state_dim)

        actions_array     = np.array(actions, dtype=np.int32)         # shape: (batch_size,)
        rewards_array     = np.array(rewards, dtype=np.float32)       # shape: (batch_size,)
        dones_array       = np.array(dones, dtype=bool)               # shape: (batch_size,)

        return (
            states_array,
            actions_array,
            rewards_array,
            next_states_array,
            dones_array,
            indices,
            weights,
        )


    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """
        Actualiza las prioridades de los índices especificados.
        """
        for idx, prio in zip(indices, priorities):
            self.priorities[idx] = prio

    def size(self) -> int:
        """Devuelve el número actual de transiciones en buffer."""
        return len(self.buffer)

    def save(self, filepath: str) -> None:
        """Serializa el buffer completo usando pickle (joblib)."""
        data = {
            'buffer': list(self.buffer),
            'priorities': list(self.priorities)
        }
        joblib.dump(data, filepath)

    def load(self, filepath: str) -> None:
        """Carga el buffer y prioridades desde disco."""
        data = joblib.load(filepath)
        self.buffer = deque(data['buffer'], maxlen=self.capacity)
        self.priorities = data['priorities']