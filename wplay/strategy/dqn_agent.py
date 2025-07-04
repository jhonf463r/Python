# wplay/strategy/dqn_agent.py

import os
import logging
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential, Input
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import load_model, clone_model
from typing import Optional
from wplay.wplay_config.hyperparams import HyperParams

from wplay.strategy.prioritized_replay_buffer import PrioritizedReplayBuffer
from wplay.strategy.constants import MONTO_MAX

def build_q_network(state_dim: int, action_dim: int, hidden_units=None) -> Sequential:
    hidden_units = hidden_units or [64, 64]
    return Sequential([
        Input(shape=(state_dim,)),
        *[Dense(u, activation='relu') for u in hidden_units],
        Dense(action_dim, activation='linear')
    ])

class DQNAgent:
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hp: HyperParams,
        model_path: Optional[str] = None,
    ):
        # Dimensiones
        self.state_dim  = state_dim
        self.action_dim = action_dim

        # Hiperparámetros DQN
        self.gamma       = hp.dqn_gamma
        self.tau         = hp.dqn_tau
        self.hidden_units = hp.dqn_hidden

        # ε-greedy por fases
        self.eps_start, self.eps_mid, self.eps_final = (
            hp.dqn_eps_start,
            hp.dqn_eps_mid,
            hp.dqn_eps_final
        )
        self.phase1, self.phase2 = hp.dqn_phase1, hp.dqn_phase2
        self.epsilon    = self.eps_start
        self.step_count = 0

        # Scheduler de learning rate
        total_steps = self.phase1 + self.phase2
        self.learning_rate = hp.dqn_lr
        self.lr_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate=self.learning_rate,
            decay_steps=total_steps,
            decay_rate=hp.dqn_lr_decay_rate if hasattr(hp, 'dqn_lr_decay_rate') else 0.5,
            staircase=True
        )

       # Rutas de modelo
        base = model_path or hp.model_base_path
        if not base.endswith('.h5'):
            base = os.path.splitext(base)[0] + '.h5'
        self.model_path = base
       # Construir o cargar redes
        if os.path.exists(self.model_path):
            try:
                self._q_network = load_model(self.model_path)
                real_dim = self._q_network.input_shape[1]
                if real_dim != self.state_dim:
                    logging.warning(f"[DQNAgent] Ajustando state_dim {self.state_dim}→{real_dim}")
                    self.state_dim = real_dim
                # crear target a partir de _q_network
                self.target_network = clone_model(self._q_network)
                self.target_network.set_weights(self._q_network.get_weights())
            except Exception as e:
                logging.warning(f"[DQNAgent] Falló load_model ({e}), construyendo de nuevo")
                self._build_networks()
        else:
            self._build_networks()

        # Función de inferencia y optimizador
        self._infer_q   = tf.function(lambda x: self._q_network(x, training=False))
        self.optimizer  = Adam(self.lr_scheduler)

        # Buffer Prioritized Replay
        self.memory = PrioritizedReplayBuffer(capacity=hp.dqn_buffer_capacity)

        logging.info(
            f"[DQNAgent] Init state_dim={self.state_dim}, action_dim={self.action_dim}, "
            f"hidden_units={self.hidden_units}, gamma={self.gamma}"
        )
        logging.info(f"[DQNAgent] lr={self.learning_rate}, gamma={self.gamma}")


    def _build_networks(self):
        """Construye _q_network y target_network según self.state_dim."""
        self._q_network      = build_q_network(self.state_dim, self.action_dim, self.hidden_units)
        self.target_network  = build_q_network(self.state_dim, self.action_dim, self.hidden_units)
        self.target_network.set_weights(self._q_network.get_weights())
        logging.info(f"[DQNAgent] Redes construidas: state_dim={self.state_dim}, action_dim={self.action_dim}")


    def rebuild_network(self, new_state_dim: int):
        """
        Reconstruye ambas redes si cambia la dimensión.
        Ahora NO compilamos ningún tf.function, dejamos que
        Keras maneje dinámicamente la forma de entrada.
        """
        if new_state_dim <= 0 or new_state_dim == self.state_dim:
            return

        logging.info(f"[DQNAgent] Rebuild networks: {self.state_dim} → {new_state_dim}")
        self.state_dim = new_state_dim

        # 1) Reconstruir las dos redes
        self._build_networks()

        # 2) Re‑crear optimizador (con scheduler)
        self.optimizer = Adam(self.lr_scheduler)


    def select_action(self, state: np.ndarray, eval_mode: bool = False) -> int:
        """
        ε‑greedy + rebuild automático.
        Llamamos siempre directamente a self._q_network(...)
        para que respete la forma actual.
        """
        # --- 1) Calcular ε actual ---
        if eval_mode:
            eps = 0.0
        else:
            self.step_count += 1
            if self.step_count < self.phase1:
                self.epsilon = self.eps_start + (self.eps_mid - self.eps_start) * self.step_count / self.phase1
            elif self.step_count < self.phase2:
                self.epsilon = self.eps_mid + (self.eps_final - self.eps_mid) * (self.step_count - self.phase1) / (self.phase2 - self.phase1)
            self.epsilon = np.clip(self.epsilon, self.eps_final, self.eps_start)
            eps = self.epsilon

        # --- 2) Batchify ---
        s = np.asarray(state, dtype=np.float32)
        if s.ndim == 1:
            s = s[np.newaxis, :]

        # --- 3) Rebuild si cambió la dimensión ---
        input_dim = self._q_network.input_shape[-1]
        if s.shape[1] != input_dim:
            logging.warning(f"[DQNAgent] select_action: rebuild por mismatch {input_dim}→{s.shape[1]}")
            self.rebuild_network(s.shape[1])

        # --- 4) Inferir Q-values directamente ---
        q_vals = self._q_network(s, training=False).numpy()

        # --- 5) ε‑greedy decision ---
        if not eval_mode and np.random.rand() < eps:
            return int(np.random.randint(self.action_dim))
        return int(np.argmax(q_vals[0]))


    def store_transition(self, state, action, raw_reward, next_state, done):
        shaped = raw_reward / MONTO_MAX
        r = float(np.clip(shaped, -1.0, 1.0))
        self.memory.add(state, action, r, next_state, done)


    def train_offline(self, states, actions, rewards, next_states, dones, batch_size=64, epochs=1):
        # Rebuild defensivo
        if states.shape[1] != self.state_dim:
            self.rebuild_network(states.shape[1])
        losses = []
        N = len(states)
        for _ in range(epochs):
            idx = np.random.permutation(N)
            for start in range(0, N, batch_size):
                mb = idx[start:start+batch_size]
                loss = self._train_step_offline(
                    states[mb], actions[mb], rewards[mb], next_states[mb], dones[mb]
                )
                if loss is not None: losses.append(loss)
        avg = float(np.mean(losses)) if losses else None
        if avg is not None: logging.info(f"[DQNAgent][offline] avg_loss={avg:.4f}")
        return avg


    def _train_step_offline(self, states, actions, rewards, next_states, dones):
        # Reconstruye si cambió dim
        if states.shape[1] != self.state_dim:
            self.rebuild_network(states.shape[1])
        # Q-targets Double‑DQN
        q_next    = self.target_network(next_states)
        max_next  = tf.reduce_max(q_next, axis=1)
        target_qs = rewards + (1.0 - dones.astype(np.float32)) * self.gamma * max_next

        acts    = tf.convert_to_tensor(actions, dtype=tf.int32)
        one_hot = tf.one_hot(acts, self.action_dim, dtype=tf.float32)

        with tf.GradientTape() as tape:
            q_vals   = self._q_network(states, training=True)
            q_taken  = tf.reduce_sum(q_vals * one_hot, axis=1)
            loss     = tf.reduce_mean(tf.square(target_qs - q_taken))

        grads = tape.gradient(loss, self._q_network.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self._q_network.trainable_variables))
        # Soft‑update
        for w, w_t in zip(self._q_network.weights, self.target_network.weights):
            w_t.assign(self.tau * w + (1.0 - self.tau) * w_t)

        return float(loss.numpy())


    def train_online(self, batch_size: int = 64) -> Optional[float]:
        if self.memory.size() < batch_size:
            return None
        batch = self.memory.sample(batch_size)
        return self._train_step_offline(
            batch.states, batch.actions, batch.rewards,
            batch.next_states, batch.dones
        )

       
    def get_q_network(self) -> tf.keras.Model:
        return self._q_network
    def predict_q(self, state: np.ndarray) -> np.ndarray:
        """
        Vector de Q(s,a) vía la red, adaptando/rebuild si hace falta.
        """
        if state.ndim == 1:
            state = state[np.newaxis, :]
        s = np.asarray(state, dtype=np.float32)

        # Mismo chequeo que en select_action
        input_dim = self._q_network.input_shape[-1]
        if s.shape[1] != input_dim:
            logging.warning(
                f"[DQNAgent] predict_q: mismatch input_shape {input_dim} vs state_dim {s.shape[1]}, rebuilding"
            )
            self.rebuild_network(s.shape[1])

        # Inferir
        return self._infer_q(tf.constant(s)).numpy()
    def q_values(self, state: np.ndarray) -> np.ndarray:
            """
            Siempre usa predict_q para recortar el vector
            y llamar a la red en modo inferencia.
            """
            # Asegura batch dim y slicing
            if state.ndim == 1:
                state = state[np.newaxis, :]
            # slice aquí también
            if state.shape[1] > self.state_dim:
                state = state[:, :self.state_dim]
            return self.predict_q(state)
    @property
    def q_network(self) -> tf.keras.Model:
        """
        Acceso de solo lectura a la red Q.
        """
        return self._q_network

    @q_network.setter
    def q_network(self, model: tf.keras.Model):
        """
        Permite reasignar _q_network sin romper la propiedad,
        p. ej. al cargar un modelo desde disco.
        """
        self._q_network = model

    def update_target_network(self):
        """Soft-update (Polyak) de la target network."""
        for w, w_t in zip(self.q_network.weights, self.target_network.weights):
            w_t.assign(self.tau * w + (1.0 - self.tau) * w_t)

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
    ) -> float | None:
        """Un solo paso de entrenamiento offline (loss MSE)."""
        # Rebuild si cambió
        if states.shape[1] != self.state_dim:
            self.rebuild_network(states.shape[1])

        # Q-targets
        q_next    = self.target_network(next_states)
        max_next  = tf.reduce_max(q_next, axis=1)
        target_qs = rewards + (1.0 - dones.astype(np.float32)) * self.gamma * max_next

        # One-hot actions
        acts = tf.convert_to_tensor(actions, dtype=tf.int32)
        one_hot = tf.one_hot(acts, self.action_dim, dtype=tf.float32)

        with tf.GradientTape() as tape:
            q_vals = self.q_network(states, training=True)
            q_taken = tf.reduce_sum(q_vals * one_hot, axis=1)
            loss = tf.reduce_mean(tf.square(target_qs - q_taken))

        grads = tape.gradient(loss, self.q_network.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.q_network.trainable_variables))
        self.update_target_network()
        return float(loss.numpy())

    def save(self, path: str):
        """Guarda redes, optimizador, epsilon y buffer."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.q_network.save(path)
        # guardar estado del optimizador y epsilon
        state = {
            "optimizer_weights": self.optimizer.get_weights(),
            "epsilon": self.epsilon,
            "step_count": self.step_count
        }
        import joblib
        joblib.dump(state, path + ".state.pkl")
        # guardar buffer PER
        try:
            self.memory.save(path + ".buffer.pkl")
        except Exception as e:
            logging.warning(f"[DQNAgent] No pude guardar buffer: {e}")

    def load(self, path: str):
        """Carga redes, optimizador, epsilon y buffer."""
        if not os.path.exists(path):
            return
        self.q_network = load_model(path)
        self.target_network = clone_model(self.q_network)
        self.target_network.set_weights(self.q_network.get_weights())
        import joblib
        st = joblib.load(path + ".state.pkl")
        self.optimizer.set_weights(st["optimizer_weights"])
        self.epsilon    = st["epsilon"]
        self.step_count = st["step_count"]
        try:
            self.memory.load(path + ".buffer.pkl")
        except:
            pass
        self.state_dim = self.q_network.input_shape[1]

    def train(self, *args, **kwargs) -> Optional[float]:
        """
        Interfaz unificada: detecta offline u online según args.
        """
        if len(args) >= 5:
            return self.train_offline(*args, **kwargs)
        bs = args[0] if args else kwargs.get('batch_size', 64)
        return self.train_online(bs)


        """
        Carga q_network, target_network, optimizador, epsilon, step_count y buffer.
        """
        if not os.path.exists(path):
            return

        # 1) Cargar la red desde disco directamente en _q_network
        self._q_network = load_model(path)
        # 2) Reconstruir target_network
        self.target_network = clone_model(self._q_network)
        self.target_network.set_weights(self._q_network.get_weights())

        # 3) Cargar estado de optimizador y demás
        import joblib
        state = joblib.load(path + ".state.pkl")
        self.optimizer.set_weights(state["optimizer_weights"])
        self.epsilon    = state["epsilon"]
        self.step_count = state["step_count"]

        # 4) Cargar buffer PER
        self.memory.load(path + ".buffer.pkl")

        # 5) Ajustar state_dim al input real de la red cargada
        self.state_dim = self._q_network.input_shape[1]

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool
    ) -> None:
        """
        Almacena la transición (s, a, r, s', done) en el buffer interno.
        Usamos store_transition para aplicar reward shaping y clipping.
        """
        # Si el estado ha cambiado de dimensión, reconstruir redes
        if state.ndim == 1:
            dim = state.shape[0]
        else:
            dim = state.shape[1]
        if dim != self.state_dim:
            self.rebuild_network(dim)

        # Desenpaquetar reward shaping y drawdown interno si lo necesitas,
        # pero aquí usamos directamente reward crudo:
        self.store_transition(state, action, reward, next_state, done)   
    def save_model(self, path: str):
        # path suele terminar en .h5
        if not path.endswith('.h5'):
            path = os.path.splitext(path)[0] + '.h5'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._q_network.save(path)
        # guardamos estado optimizador/epsilon
        import joblib
        state = {
            "optimizer_weights": self.optimizer.get_weights(),
            "epsilon": self.epsilon,
            "step_count": self.step_count
        }
        joblib.dump(state, path + ".state.pkl")
        # buffer
        try: self.memory.save(path + ".buffer.pkl")
        except Exception as e:
            logging.warning(f"[DQNAgent] No pude guardar buffer: {e}")

    def load_model(self, path: str):
        if not path.endswith('.h5'):
            path = os.path.splitext(path)[0] + '.h5'
        if not os.path.exists(path):
            logging.warning(f"[DQNAgent] load_model: no existe {path}")
            return
        # cargar red principal
        self._q_network = load_model(path)
        # target
        self.target_network = clone_model(self._q_network)
        self.target_network.set_weights(self._q_network.get_weights())
        # restaurar estado
        import joblib
        st = joblib.load(path + ".state.pkl")
        self.optimizer.set_weights(st["optimizer_weights"])
        self.epsilon, self.step_count = st["epsilon"], st["step_count"]
        try: self.memory.load(path + ".buffer.pkl")
        except: pass
        # ajustar dimensión
        self.state_dim = self._q_network.input_shape[1]
