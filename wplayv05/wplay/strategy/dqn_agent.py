# wplay/strategy/dqn_agent.py

import os
import logging
import random
import numpy as np
import tensorflow as tf
from collections import deque
from typing import Optional, Tuple, Any, List

from tensorflow.keras import Sequential, Model, Input
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import load_model, clone_model

from wplay.strategy.prioritized_replay_buffer import PrioritizedReplayBuffer
from wplay.strategy.constants import MONTO_MAX

def build_q_network(state_dim: int, action_dim: int) -> tf.keras.Model:
    """
    Construye una red Q de dos capas ocultas para DQN.
    """
    model = Sequential([
        Input(shape=(state_dim,)),
        Dense(64, activation='relu'),
        Dense(64, activation='relu'),
        Dense(action_dim, activation='linear'),
    ])
    return model

class DQNAgent:
    """
    Agente DQN con:
      - Double DQN
      - Prioritized Experience Replay
      - Soft-/Polyak-update de la target network
      - ε-greedy por fases con eval_mode
      - Entrenamiento online y offline
      - Serialización completa (redes, optimizador, ε y buffer)
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_mid: float = 0.5,
        epsilon_final: float = 0.05,
        decay_steps_phase1: int = 10000,
        decay_steps_phase2: int = 50000,
        tau: float = 0.005,
        use_lr_scheduler: bool = True,
        model_path: Optional[str] = None,
        buffer_capacity: int = 10000,
        buffer_alpha:    float = 0.6,
        buffer_beta:     float = 0.4,
        buffer_epsilon:  float = 1e-6,
    ):
        # Exponer learning_rate para usos externos
        self.learning_rate = learning_rate

        # Cargar modelo previo si se indicó ruta
        if model_path:
            try:
                self.q_network = load_model(model_path)
                self.target_network = clone_model(self.q_network)
                self.target_network.set_weights(self.q_network.get_weights())
                print(f"[DQNAgent] Modelo cargado desde {model_path}")
            except Exception:
                logging.warning(f"[DQNAgent] No se pudo cargar modelo de {model_path}, creando uno nuevo")
                self.q_network = build_q_network(state_dim, action_dim)
                self.target_network = build_q_network(state_dim, action_dim)
                self.target_network.set_weights(self.q_network.get_weights())
        else:
            self.q_network = build_q_network(state_dim, action_dim)
            self.target_network = build_q_network(state_dim, action_dim)
            self.target_network.set_weights(self.q_network.get_weights())

        # Parámetros básicos
        self.state_dim  = state_dim
        self.action_dim = action_dim
        self.gamma      = gamma

        # ε-greedy scheduling
        self.epsilon    = epsilon_start
        self.eps_start, self.eps_mid, self.eps_final = epsilon_start, epsilon_mid, epsilon_final
        self.phase1, self.phase2 = decay_steps_phase1, decay_steps_phase2
        self.step_count = 0

        # Buffer PER
        self.memory = PrioritizedReplayBuffer(
            capacity=buffer_capacity,
            alpha=buffer_alpha,
            beta=buffer_beta,
            epsilon=buffer_epsilon
        )

        # Optimizador y scheduler
        self.optimizer = Adam(learning_rate=learning_rate)
        if use_lr_scheduler:
            self.lr_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=learning_rate,
                decay_steps=decay_steps_phase1 + decay_steps_phase2,
                decay_rate=0.5,
                staircase=True
            )
        else:
            self.lr_scheduler = None

        # Soft‐update factor
        self.tau = tau
        self.update_counter = 0
        self.prev_loss = float('inf')

    def _build_networks(self):
        """
        (Re)construye q_network y target_network con el state_dim actual.
        """
        self.q_network = build_q_network(self.state_dim, self.action_dim)
        self.target_network = build_q_network(self.state_dim, self.action_dim)
        self.target_network.set_weights(self.q_network.get_weights())

    def rebuild_network(self, new_state_dim: int):
        """
        Reconstruye redes y optimizador si cambia la dimensión del estado.
        """
        logging.info(f"[DQNAgent] Rebuild networks: state_dim {self.state_dim} → {new_state_dim}")
        self.state_dim = new_state_dim
        self._build_networks()
        # Reinstanciar optimizador para asegurar compatibilidad
        self.optimizer = Adam(learning_rate=self.learning_rate)
        if self.lr_scheduler:
            # Reinicializar scheduler conservando parámetros
            self.lr_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=self.learning_rate,
                decay_steps=self.phase1 + self.phase2,
                decay_rate=0.5,
                staircase=True
            )

    def select_action(self, state: np.ndarray, eval_mode: bool = False) -> int:
        """
        Devuelve la acción ε-greedy (o greedy si eval_mode=True).
        """
        # Ajuste de ε en función de modo y fases
        if eval_mode:
            eps = 0.0
        else:
            self.step_count += 1
            if self.step_count < self.phase1:
                self.epsilon = max(self.eps_mid, self.eps_start + (self.eps_mid - self.eps_start) * self.step_count / self.phase1)
            elif self.step_count < self.phase2:
                self.epsilon = max(self.eps_final, self.eps_mid + (self.eps_final - self.eps_mid) * (self.step_count - self.phase1) / (self.phase2 - self.phase1))
            eps = self.epsilon

        # Reconstruir si cambió dimensión
        if state.shape[0] != self.state_dim:
            self.rebuild_network(state.shape[0])

        # ε-greedy
        if random.random() < eps:
            return random.randrange(self.action_dim)
        q_vals = self.q_network(np.expand_dims(state,0)).numpy()[0]
        return int(np.argmax(q_vals))

    def update_target_network(self):
        """
        Soft-update (Polyak) de la target network.
        """
        for w, w_tgt in zip(self.q_network.weights, self.target_network.weights):
            w_tgt.assign(self.tau * w + (1.0 - self.tau) * w_tgt)

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        raw_reward: float,
        next_state: np.ndarray,
        done: bool,
        drawdown: Optional[float] = None,
        shaped_ratio: float = 0.5
    ) -> None:
        """
        Almacena transición en el buffer, aplicando reward shaping y normalización.
        """
        reward = raw_reward - shaped_ratio * drawdown if drawdown is not None else raw_reward
        r = float(np.clip(reward / MONTO_MAX, -1.0, 1.0))
        self.memory.add(state, action, r, next_state, done)

    def _sample_batch(self, batch_size: int):
        """
        Muestra un minibatch con PER: estados, acciones, rewards, next_states, dones, weights, indices.
        """
        return self.memory.sample(batch_size)

    def _train_step_offline(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray
    ) -> Optional[float]:
        """
        Paso de entrenamiento DQN clásico (offline).
        """
        if states.ndim != 2 or next_states.ndim != 2:
            logging.error(f"[DQNAgent] States mal formateados: {states.shape}, {next_states.shape}")
            return None

        # Defensivo: rebuild si cambió
        if states.shape[1] != self.state_dim:
            logging.warning(f"[DQNAgent] state_dim cambiado: {self.state_dim} → {states.shape[1]}")
            self.rebuild_network(states.shape[1])

        # Q-target
        q_next = self.target_network(next_states)
        max_next_q = tf.reduce_max(q_next, axis=1)
        target_q = rewards + (1.0 - dones) * self.gamma * max_next_q

        # Loss
        with tf.GradientTape() as tape:
            q_vals = self.q_network(states)
            q_taken = tf.reduce_sum(q_vals * tf.one_hot(actions, self.action_dim), axis=1)
            loss = tf.reduce_mean(tf.square(target_q - q_taken))

        grads = tape.gradient(loss, self.q_network.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.q_network.trainable_variables))

        self.update_target_network()
        return float(loss.numpy())

    def train_offline(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        batch_size: int = 64,
        epochs: int = 1
    ) -> Optional[float]:
        """
        Entrenamiento offline con datos preexistentes.
        """
        N = len(states)
        if N == 0:
            logging.error("[DQNAgent] Sin transiciones para entrenar.")
            return None

        # Reconstruir defensivamente si dim cambió
        if states.shape[1] != self.state_dim:
            logging.warning(f"[DQNAgent] state_dim out-of-date: {self.state_dim} → {states.shape[1]}")
            self.rebuild_network(states.shape[1])

        losses = []
        for _ in range(epochs):
            perm = np.random.permutation(N)
            for start in range(0, N, batch_size):
                mb = perm[start:start+batch_size]
                l = self._train_step_offline(
                    states[mb], actions[mb], rewards[mb], next_states[mb], dones[mb]
                )
                if l is not None:
                    losses.append(l)

        avg = float(np.mean(losses)) if losses else None
        if avg is not None:
            logging.info(f"[DQNAgent][offline] avg_loss={avg:.4f}")
        return avg

    def train_online(self, batch_size: int = 64) -> Optional[float]:
        """
        Entrenamiento online (PER + un solo train step).
        """
        if self.memory.size() < batch_size:
            return None
        states, actions, rewards, next_states, dones, weights, idxs = self._sample_batch(batch_size)
        loss = self._train_step_offline(states, actions, rewards, next_states, dones)
        # opcional: actualizar prioridades con td-error
        return loss

    def train(self, *args, **kwargs) -> Optional[float]:
        """
        Interfaz unificada: detecta offline u online según args.
        """
        if len(args) >= 5:
            return self.train_offline(*args, **kwargs)
        bs = args[0] if args else kwargs.get('batch_size', 64)
        return self.train_online(bs)

    def save(self, path: str) -> None:
        """
        Guarda q_network, estado del optimizador, ε y buffer.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.q_network.save(path)
        state = {
            'optimizer_weights': self.optimizer.get_weights(),
            'epsilon': self.epsilon,
            'step_count': self.step_count,
        }
        import joblib
        joblib.dump(state, path + ".state.pkl")
        self.memory.save(path + ".buffer.pkl")

    def load(self, path: str) -> None:
        """
        Carga modelo, optimizador, ε y buffer.
        """
        if not os.path.exists(path):
            return
        self.q_network = load_model(path)
        self.target_network = clone_model(self.q_network)
        self.target_network.set_weights(self.q_network.get_weights())
        import joblib
        state = joblib.load(path + ".state.pkl")
        self.optimizer.set_weights(state['optimizer_weights'])
        self.epsilon    = state['epsilon']
        self.step_count = state['step_count']
        self.memory.load(path + ".buffer.pkl")
