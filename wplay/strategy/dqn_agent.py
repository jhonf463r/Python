# Archivo: wplay/strategy/dqn_agent.py

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.models import load_model, clone_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import MeanSquaredError
from wplay.strategy.prioritized_replay_buffer import PrioritizedReplayBuffer

class DQNAgent:
    """
    Agente DQN con Double DQN y Prioritized Experience Replay.
    Ubicación: 'wplay/strategy/dqn_agent.py'
    """
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        model_path: str,
        buffer_size: int = 100000,
        alpha: float = 0.6,
        beta_start: float = 0.4,
        beta_frames: int = 100000,
        gamma: float = 0.99,
        lr: float = 1e-3,
        epsilon_start: float = 1.0,
        epsilon_final: float = 0.1,
        epsilon_decay: float = 0.995,
        target_update_freq: int = 1000,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.model_path = model_path
        self.lr = lr
        os.makedirs(os.path.dirname(model_path) or '.', exist_ok=True)

        # Hiperparámetros
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_final = epsilon_final
        self.epsilon_decay = epsilon_decay
        self.target_update_freq = target_update_freq

        # Buffer priorizado
        self.buffer = PrioritizedReplayBuffer(buffer_size, alpha)
        self.beta_start = beta_start
        self.beta_frames = beta_frames
        self.frame_idx = 1

        # Redes en DQN doble
        self.model = self._build_model()
        self.target_model = clone_model(self.model)
        self.target_model.set_weights(self.model.get_weights())

    def _build_model(self):
        model = Sequential([
            Input(shape=(self.state_dim,)),
            Dense(64, activation='relu'),
            Dense(64, activation='relu'),
            Dense(self.action_dim, activation='linear'),
        ])
        optimizer = Adam(learning_rate=self.lr)
        loss = MeanSquaredError()
        model.compile(optimizer=optimizer, loss=loss, run_eagerly=True)
        return model

    def select_action(self, state: np.ndarray) -> int:
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.action_dim)
        q_vals = self.model.predict(state[None], verbose=0)[0]
        return int(np.argmax(q_vals))

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(state, action, reward, next_state, done)
        self.frame_idx += 1

    def train(
        self,
        batch_size: int = 64,
        *,
        transition_csv: str = None,
        states: np.ndarray = None,
        actions: np.ndarray = None,
        rewards: np.ndarray = None,
        next_states: np.ndarray = None,
        dones: np.ndarray = None,
        epochs: int = 1
    ) -> None:
        # Leer CSV y remapear acciones a categorías antes de entrenar
        if transition_csv:
            df = pd.read_csv(transition_csv)
            # mapear columna 'action' a categoría index fuera del CSV
            # asumir existe df['action_cat'] ya
            if 'action_cat' not in df.columns:
                raise ValueError("Debe mapear las acciones a categorías con 'action_cat' antes de entrenar DQN.")
            st = df.filter(regex='^state_').values
            act = df['action_cat'].astype(int).values
            rew = df['reward'].values
            ns = df.filter(regex='^next_state_').values
            if 'done' in df.columns:
                dn = df['done'].astype(bool).values
            else:
                dn = np.zeros(len(df), dtype=bool)
                dn[-1] = True
            # validar rango
            if act.max() >= self.action_dim or act.min() < 0:
                print(f"[ERROR] Acciones fuera de rango 0–{self.action_dim-1}: {act.min()}–{act.max()}")
                return
            return self.train(
                batch_size=batch_size,
                states=st,
                actions=act,
                rewards=rew,
                next_states=ns,
                dones=dn,
                epochs=epochs
            )

        # Pre-entrenamiento offline
        if states is not None:
            for _ in range(epochs):
                self._train_batch(states, actions, rewards, next_states, dones, None, np.ones(len(states)))
            return

        # Entrenamiento online con buffer
        if self.buffer.size() < batch_size:
            return
        beta = min(1.0, self.beta_start + self.frame_idx * (1.0 - self.beta_start) / self.beta_frames)
        st_b, ac_b, rw_b, ns_b, dn_b, idxs, w_b = self.buffer.sample(batch_size, beta)
        self._train_batch(st_b, ac_b, rw_b, ns_b, dn_b, idxs, w_b)
        # actualizar epsilon y target model
        self.epsilon = max(self.epsilon_final, self.epsilon * self.epsilon_decay)
        if self.frame_idx % self.target_update_freq == 0:
            self.target_model.set_weights(self.model.get_weights())

    def _train_batch(
        self,
        states, actions, rewards, next_states, dones, indices, weights
    ) -> None:
        q_next = self.model.predict(next_states, verbose=0)
        q_target_next = self.target_model.predict(next_states, verbose=0)
        q_pred = self.model.predict(states, verbose=0)
        for i in range(len(states)):
            if dones[i]:
                target = rewards[i]
            else:
                best_next = np.argmax(q_next[i])
                target = rewards[i] + self.gamma * q_target_next[i][best_next]
            q_pred[i][actions[i]] = target
        self.model.train_on_batch(states, q_pred, sample_weight=weights)
        if indices is not None:
            td_errors = np.abs(
                q_pred[np.arange(len(states)), actions]
                - q_target_next[np.arange(len(states)), actions]
            )
            self.buffer.update_priorities(indices, td_errors)

    def save(self, path: str = None) -> None:
        if path is None:
            path = self.model_path
        self.model.save(path)

    def load(self, path: str = None) -> None:
        if path is None:
            path = self.model_path
        if os.path.isfile(path):
            loaded = load_model(path, custom_objects={'MeanSquaredError': MeanSquaredError}, compile=False)
            optimizer = Adam(learning_rate=self.lr)
            loss = MeanSquaredError()
            loaded.compile(optimizer=optimizer, loss=loss, run_eagerly=True)
            if loaded.input_shape[-1] == self.state_dim:
                self.model = loaded
                self.target_model = clone_model(loaded)
                self.target_model.set_weights(self.model.get_weights())
