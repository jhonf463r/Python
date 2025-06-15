# wplay/strategy/meta_strategy_selector.py

import os
import logging
import numpy as np
import tensorflow as tf
from collections import deque
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam

class MetaStrategySelector:
    def __init__(
        self,
        state_dim: int = 10,
        strategy_list: list = None,
        model_path: str = "wplay/models/meta_strategy_selector.h5",
        window: int = 100,
        ucb_c: float = 1.0,
        use_ts: bool = True
    ):
        """
        - state_dim: dimensión del vector de estado.
        - strategy_list: lista de claves de estrategia (e.g. ["dqn","ppo"]).
        - model_path: ruta para guardar/cargar el modelo Keras.
        - window: número de iteraciones para retraining periódico.
        - ucb_c: constante de exploración para UCB1.
        - use_ts: True para Thompson Sampling; False para UCB.
        """
        self.state_dim      = state_dim
        self.strategy_list  = strategy_list or ["dqn", "ppo"]
        self.n_strategies   = len(self.strategy_list)
        self.model_path     = model_path
        self.window         = window
        self.ucb_c          = ucb_c
        self.use_ts         = use_ts

        # — Buffers offline para retraining periódico —
        self.reward_history = deque(maxlen=window)
        self._offline_states = deque(maxlen=window)
        self._offline_idxs   = deque(maxlen=window)

        # — Contadores UCB1 clásico —
        self.counts       = np.zeros(self.n_strategies, dtype=int)   # n_i
        self.values       = np.zeros(self.n_strategies, dtype=float) # media reward
        self.total_counts = 0                                         # N

        # — Contadores Bayesianos para Thompson Sampling —
        self.successes = np.zeros(self.n_strategies, dtype=int)
        self.failures  = np.zeros(self.n_strategies, dtype=int)

        # Construir o cargar modelo
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        self._build_or_load_model()

    def _build_or_load_model(self):
        """Carga modelo existente o crea uno nuevo de dos capas."""
        if os.path.exists(self.model_path):
            self.model = load_model(self.model_path)
            logging.info(f"[META] Modelo cargado desde {self.model_path}")
        else:
            self.model = Sequential([
                Input(shape=(self.state_dim,)),
                Dense(64, activation='relu'),
                Dense(64, activation='relu'),
                Dense(self.n_strategies, activation='softmax')
            ])
            self.model.compile(optimizer=Adam(1e-3), loss='categorical_crossentropy')
            logging.info("[META] Modelo nuevo creado")

    def rebuild_model(self, new_state_dim: int):
        """
        Reconstruye la red para una nueva dimensión de entrada.
        Útil si cambian las features disponibles.
        """
        self.state_dim = new_state_dim
        self.model = Sequential([
            Input(shape=(self.state_dim,)),
            Dense(64, activation='relu'),
            Dense(64, activation='relu'),
            Dense(self.n_strategies, activation='softmax')
        ])
        self.model.compile(optimizer=Adam(1e-3), loss='categorical_crossentropy')
        logging.info(f"[META] Model rebuilt with state_dim={self.state_dim}")

    def update(self, strategy: str, reward: float):
        """
        1) Mapear estrategia → índice.
        2) Actualizar buffers y contadores UCB.
        3) Actualizar contadores Bayesianos para TS.
        4) Acumular datos offline para retraining periódico.
        5) Cada 'window' pasos: retrain forzando eager execution.
        """
        # 1) Índice
        try:
            idx = self.strategy_list.index(strategy)
        except ValueError:
            logging.warning(f"[META] update(): estrategia desconocida '{strategy}'")
            return

        # 2) Historial de recompensas
        self.reward_history.append(reward)

        # — UCB1 clásico: actualizar counts & valores medios —
        self.counts[idx] += 1
        self.total_counts += 1
        n_i = self.counts[idx]
        self.values[idx] += (reward - self.values[idx]) / n_i

        # — Thompson Sampling: éxitos vs fracasos —
        if reward > 0:
            self.successes[idx] += 1
        else:
            self.failures[idx] += 1

        # 3) Acumular par (estado ficticio, etiqueta)
        dummy = np.zeros((self.state_dim,), dtype=np.float32)
        self._offline_states.append(dummy)
        self._offline_idxs.append(idx)

        # 4) Retraining periódico
        if len(self.reward_history) >= self.window and len(self.reward_history) % self.window == 0:
            logging.info("[META] Retraining meta-modelo online")

            # Preparar X, y
            X = np.stack(self._offline_states, axis=0).astype(np.float32)
            y = np.eye(self.n_strategies, dtype=np.float32)[list(self._offline_idxs)]

            # Recompilar para sincronizar optimizador
            self.model.compile(optimizer=Adam(1e-3), loss='categorical_crossentropy')

            # Forzar eager para evitar errores .numpy()
            tf.config.run_functions_eagerly(True)

            # Entrenar un epoch
            self.model.fit(X, y, epochs=1, batch_size=self.window, verbose=1)

            # Restaurar ejecución graficada si lo deseas
            tf.config.run_functions_eagerly(False)

            # Guardar modelo
            self.model.save(self.model_path)
            logging.info(f"[META] Modelo guardado en {self.model_path}")

    def select_strategy(self, state: np.ndarray) -> str:
        """
        1) Aplica heurísticas contextuales rápidas.
        2) Si no, usa UCB1 o Thompson Sampling según `use_ts`.
        3) (Opcional) podría caer en la red softmax como fallback.
        """
        # — Heurísticas contextuales —
        try:
            drawdown       = float(state[12]) if state.shape[-1] > 12 else 0.0
            t_sin_victoria = float(state[13]) if state.shape[-1] > 13 else 0.0
            jugadores      = float(state[1])
            vel_prom       = float(np.mean(state[2:7])) if state.shape[-1] > 7 else 0.0
            saldo_var      = float(np.var(state[7:12])) if state.shape[-1] > 12 else 0.0
            dir_score      = float(np.sum(state[14:16])) if state.shape[-1] > 15 else 0.0

            # Ejemplos de reglas:
            if drawdown > 0.6 and t_sin_victoria > 0.9:
                return "ppo"
            if jugadores > 0.7 and saldo_var > 0.25:
                return "dqn"
            if vel_prom > 0.6 and dir_score > 0:
                return "ppo"
        except Exception as e:
            logging.warning(f"[META] heurísticas fallaron: {e}")

        # — Exploración epsilon-greedy podría añadirse aquí —

        # — Estrategia — UCB1 o Thompson Sampling —
        if self.use_ts:
            # Thompson Sampling: muestrear de Beta(1+succ,1+fail)
            samples = [
                np.random.beta(1 + self.successes[i], 1 + self.failures[i])
                for i in range(self.n_strategies)
            ]
            idx = int(np.argmax(samples))
            logging.debug(f"[META] TS samples={samples}, elegido='{self.strategy_list[idx]}'")
        else:
            # Asegurar probar cada estrategia al menos una vez
            for i in range(self.n_strategies):
                if self.counts[i] == 0:
                    return self.strategy_list[i]
            # Calcular UCB scores
            ucb_scores = []
            for i in range(self.n_strategies):
                bonus = self.ucb_c * np.sqrt(np.log(self.total_counts) / self.counts[i])
                ucb_scores.append(self.values[i] + bonus)
            idx = int(np.argmax(ucb_scores))
            logging.debug(f"[META] UCB scores={ucb_scores}, elegido='{self.strategy_list[idx]}'")

        return self.strategy_list[idx]

    def train(self, states, strategy_indices, epochs=5, batch_size=32):
        """
        Entrenamiento manual desde fuera.
        """
        X = np.array(states, dtype=np.float32)
        y = np.eye(self.n_strategies, dtype=np.float32)[strategy_indices]
        self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=1)

    def save(self, path: str = None):
        """Guarda el modelo en disco."""
        dst = path or self.model_path
        self.model.save(dst)
        logging.info(f"[META] Modelo guardado en {dst}")

    def load(self, path: str = None):
        """Carga un modelo previamente guardado."""
        src = path or self.model_path
        if os.path.exists(src):
            self.model = load_model(src)
            logging.info(f"[META] Modelo cargado desde {src}")
