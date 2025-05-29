# wplay/strategy/meta_strategy_selector.py

import os
import numpy as np
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam


class MetaStrategySelector:
    def __init__(
        self,
        state_dim: int = 10,
        strategy_list: list = None,
        model_path: str = "wplay/models/meta_strategy_selector.h5",
        window: int = 100
    ):
        self.state_dim = state_dim
        self.strategy_list = strategy_list or ["dqn", "ppo", "martingala", "dalembert"]
        self.n_strategies = len(self.strategy_list)
        self.model_path = model_path
        self.window = window
        self.epsilon = 1.0

        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        self._build_or_load_model()

    def _build_or_load_model(self):
        if os.path.exists(self.model_path):
            self.model = load_model(self.model_path)
            print(f"MetaStrategySelector: modelo cargado desde {self.model_path}")
        else:
            self.model = Sequential([
                Input(shape=(self.state_dim,)),
                Dense(64, activation='relu'),
                Dense(64, activation='relu'),
                Dense(self.n_strategies, activation='softmax')
            ])
            self.model.compile(optimizer=Adam(learning_rate=0.001), loss='categorical_crossentropy')
            print("MetaStrategySelector: modelo nuevo creado")

    def select_strategy(self, state: np.ndarray) -> str:
        if np.random.rand() < self.epsilon:
            return np.random.choice(self.strategy_list)
        probs = self.model.predict(state[None], verbose=0)[0]
        idx = int(np.argmax(probs))
        return self.strategy_list[idx]

    def train(self, states, strategy_indices, epochs=5, batch_size=32):
        states = np.array(states)
        y = np.eye(self.n_strategies)[strategy_indices]

        self.model.fit(states, y, epochs=epochs, batch_size=batch_size, verbose=1)
        self.epsilon = max(0.1, self.epsilon * 0.95)

    def save(self, path: str = None):
        if path is None:
            path = self.model_path
        self.model.save(path)
        print(f"MetaStrategySelector: modelo guardado en {path}")

    def load(self, path: str = None):
        if path is None:
            path = self.model_path
        if os.path.exists(path):
            self.model = load_model(path)
            print(f"MetaStrategySelector: modelo cargado desde {path}")