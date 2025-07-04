import os
import numpy as np
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import load_model
from sklearn.utils import shuffle

class RLAgent:
    def __init__(self, state_dim: int, action_dim: int, model_path: str):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.model_path = model_path
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        self.model = Sequential([
            Dense(64, activation="relu", input_shape=(state_dim,)),
            Dense(64, activation="relu"),
            Dense(action_dim, activation="linear")
        ])
        self.model.compile(optimizer="adam", loss="mse")
        
        self.epsilon = 1.0  # Exploración al principio

    def select_action(self, state):
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.action_dim)
        q_values = self.model.predict(state[None], verbose=0)[0]
        return int(np.argmax(q_values))

    def train_step(self, state, action, reward, next_state, done):
        q = self.model.predict(state[None], verbose=0)
        q_next = self.model.predict(next_state[None], verbose=0)[0]
        target = reward + (0 if done else 0.99 * np.max(q_next))
        q[0][action] = target
        self.model.train_on_batch(state[None], q)

    def train(self, states, actions, rewards, next_states, dones, epochs=5, batch_size=32):
        """
        Entrenamiento del modelo DQN con lotes de datos históricos.
        """
        print(f"RLAgent: entrenando con {len(states)} muestras...")

        # Barajamos por seguridad
        states, actions, rewards, next_states, dones = shuffle(
            states, actions, rewards, next_states, dones, random_state=42
        )

        for epoch in range(epochs):
            for i in range(0, len(states), batch_size):
                end = i + batch_size
                s_batch = states[i:end]
                a_batch = actions[i:end]
                r_batch = rewards[i:end]
                ns_batch = next_states[i:end]
                d_batch = dones[i:end]

                q_vals = self.model.predict(s_batch, verbose=0)
                q_next = self.model.predict(ns_batch, verbose=0)

                for j in range(len(s_batch)):
                    target = r_batch[j] + (0 if d_batch[j] else 0.99 * np.max(q_next[j]))
                    q_vals[j][a_batch[j]] = target

                self.model.train_on_batch(s_batch, q_vals)

            print(f"  🧠 Epoch {epoch+1}/{epochs} completado")

        # Reducir epsilon después de entrenar
        self.epsilon = max(0.1, self.epsilon * 0.95)

    def save(self, path=None):
        if not path:
            path = self.model_path
        self.model.save(path)
        print(f"RLAgent: modelo guardado en {path}")

    def load(self, path=None):
        if not path:
            path = self.model_path
        if os.path.isfile(path):
            self.model = load_model(path)
            print(f"RLAgent: modelo cargado desde {path}")
        else:
            print(f"RLAgent: no se encontró {path}, se usará modelo sin entrenar")
