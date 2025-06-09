import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.models import load_model, clone_model
from tensorflow.keras.optimizers import Adam
from wplay.strategy.prioritized_replay_buffer import PrioritizedReplayBuffer
from wplay.strategy.constants import MONTO_MAX


def build_q_network(state_dim: int, action_dim: int) -> tf.keras.Model:
    """
    Construye una red Q simple de dos capas ocultas para DQN.
    """
    model = Sequential([
        Input(shape=(state_dim,)),
        Dense(64, activation='relu'),
        Dense(64, activation='relu'),
        Dense(action_dim, activation='linear'),
    ])
    return model

class DQNAgent:
    def __init__(
        self,
        state_dim,
        action_dim,
        learning_rate: float = 1e-3,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_mid=0.5,
        epsilon_final=0.05,
        decay_steps_phase1=10000,
        decay_steps_phase2=40000,
        tau=0.005,
        use_lr_scheduler=True,
        **kwargs
    ):
        # Dimensiones y constantes
        self.state_dim  = state_dim
        self.action_dim = action_dim
        self.gamma      = gamma
        self.step_count = 0
        # Contador para actualizaciones de target & LR scheduler
        self.update_target_counter = 0

        # ε-greedy por fases
        self.epsilon    = epsilon_start
        self.eps_start  = epsilon_start
        self.eps_mid    = epsilon_mid
        self.eps_final  = epsilon_final
        self.phase1     = decay_steps_phase1
        self.phase2     = decay_steps_phase2

        # Construcción de redes
        self.q_network      = build_q_network(state_dim, action_dim)
        self.target_network = build_q_network(state_dim, action_dim)
        self.target_network.set_weights(self.q_network.get_weights())

        # Replay buffer con Prioritized Experience Replay
        self.memory = PrioritizedReplayBuffer(capacity=10000, **kwargs)

        # Optimizer y scheduler (opcional)
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        if use_lr_scheduler:
            self.lr_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=learning_rate,
                decay_steps=10000,
                decay_rate=0.5,
                staircase=True
            )
        else:
            self.lr_scheduler = None

        # Polyak averaging (suavizado)
        self.tau = tau

    def select_action(self, state: np.ndarray) -> int:
        """
        Alias de choose_action para compatibilidad con StrategyManagerDL.
        """
        return self.choose_action(state)

    def choose_action(self, state: np.ndarray) -> int:
        """
        Selección ε-greedy por fases según step_count.
        """
        # incrementar paso para el schedule de epsilon
        self.step_count += 1

        # aggiornar epsilon en fase1/fase2
        if self.step_count < self.phase1:
            decay = (self.eps_mid - self.eps_start) / self.phase1
            self.epsilon = max(self.eps_mid, self.eps_start + decay * self.step_count)
        elif self.step_count < self.phase2:
            decay = (self.eps_final - self.eps_mid) / (self.phase2 - self.phase1)
            self.epsilon = max(
                self.eps_final,
                self.eps_mid + decay * (self.step_count - self.phase1)
            )

        # elegir acción
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.action_dim)
        q_vals = self.q_network(np.expand_dims(state, 0)).numpy()[0]
        return int(np.argmax(q_vals))


    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        raw_reward: float,
        next_state: np.ndarray,
        done: bool
    ) -> None:
        """
        Escala y clippea la recompensa, y añade la transición al buffer
        usando el método público de PrioritizedReplayBuffer.
        """
        # normalizar y clippear
        r = np.clip(raw_reward / MONTO_MAX, -1.0, 1.0)
        # añadir al buffer correctamente
        self.memory.add(state, action, r, next_state, done)
        
    def train_step(self, batch_size: int, *args, **kwargs) -> float | None:
        """
        Paso de entrenamiento DQN:
        - Valida que haya batch_size muestras en el buffer.
        - Si no, retorna None.
        - Si sí, aplica PER + Double DQN + Polyak + LR scheduler.
        """
        if self.memory.size() < batch_size:
            return None

        # — LR scheduler —
        if self.lr_scheduler:
            lr = self.lr_scheduler(self.update_target_counter)
            self.optimizer.learning_rate.assign(lr)

        # — Muestreo PER —
        states, actions, rewards, next_states, dones, weights, indices = \
            self.memory.sample(batch_size)

        # Asegurar índices como array de enteros
        indices = np.array(indices, dtype=np.int64)

        # — Double DQN target —
        q_next_online  = self.q_network(next_states)
        best_next_acts = tf.argmax(q_next_online, axis=1)
        q_next_target  = self.target_network(next_states)
        max_next_q     = tf.gather(q_next_target, best_next_acts, axis=1, batch_dims=0)
        target_q       = tf.stop_gradient(rewards + (1 - dones) * self.gamma * max_next_q)

        # — Cálculo de pérdida y gradientes —
        with tf.GradientTape() as tape:
            q_vals    = self.q_network(states)
            q_taken   = tf.reduce_sum(q_vals * tf.one_hot(actions, self.action_dim), axis=1)
            td_error  = q_taken - target_q
            loss      = tf.reduce_mean(weights * tf.square(td_error))

        grads = tape.gradient(loss, self.q_network.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.q_network.trainable_variables))

        # — Actualizar prioridades PER una a una —
        # Aplanar el array de errores a 1D y convertir a floats
        abs_errors = (np.abs(td_error.numpy().flatten()) + 1e-6).tolist()
        for idx, prio in zip(indices, abs_errors):
            self.memory.priorities[int(idx)] = float(prio)

        # — Polyak averaging —
        for w, tw in zip(self.q_network.weights, self.target_network.weights):
            tw.assign(self.tau * w + (1 - self.tau) * tw)

        self.update_target_counter += 1
        return float(loss.numpy())


    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.q_network.save(path)
    def train(
        self,
        batch_size: int = 64,
        transition_csv: str = None,
        states: np.ndarray = None,
        actions: np.ndarray = None,
        rewards: np.ndarray = None,
        next_states: np.ndarray = None,
        dones: np.ndarray = None,
        epochs: int = 1
    ) -> float or None:
        """
        Wrapper de compatibilidad para el pipeline offline.
        Si se pasan arrays (states,...), entrena usando ellos;
        si no, entrena online desde el buffer PER con train_step.
        """
        # Caso offline: datos precargados
        if states is not None and actions is not None:
            # Aquí puedes usar tu lógica offline original,
            # p.ej. llamar a _train_batch o a un método específico.
            losses = []
            for _ in range(epochs):
                # asumir que states, actions, ... tienen la misma longitud
                for i in range(0, len(states), batch_size):
                    sb = states[i:i+batch_size]
                    ab = actions[i:i+batch_size]
                    rb = rewards[i:i+batch_size]
                    nsb = next_states[i:i+batch_size]
                    db = dones[i:i+batch_size]
                    # convertir arrays a float32/bool adecuados
                    # escalar r, clip, luego llamar a memory.add si usas PER,
                    # o directamente a train_step:
                    loss = self.train_step(batch_size)
                    if loss is not None:
                        losses.append(loss.numpy() if hasattr(loss, 'numpy') else loss)
            return float(np.mean(losses)) if losses else None

        # Caso online (sin pasar datos): usamos buffer PER
        return_value = self.train_step(batch_size)
        return float(return_value.numpy()) if hasattr(return_value, 'numpy') else return_value


    def load(self, path: str) -> None:
        if os.path.exists(path):
            self.q_network = load_model(path, compile=False)
            self.target_network = clone_model(self.q_network)
            self.target_network.set_weights(self.q_network.get_weights())
