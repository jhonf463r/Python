# wplay/strategy/meta_manager.py

import random
import numpy as np
import tensorflow as tf

class MetaStrategyManager:
    def __init__(self, dqn_agent, ppo_agent, categories):
        self.dqn = dqn_agent
        self.ppo = ppo_agent
        self.categories = categories

        self.buffer_dqn = []
        self.buffer_ppo = []

        self.stats = {
            "dqn": {"total_reward": 0.0, "count": 0},
            "ppo": {"total_reward": 0.0, "count": 0},
        }

        self.meta_interval = 50
        self.round_counter = 0
        self.current_agent = random.choice(["dqn", "ppo"])
        self._latest_state = None

    def _build_state_vector(self, registro):
        # Debes replicar aquí lo mismo que FeatureEngineerRL / StatsHelper,
        # devolviendo un array de forma (state_dim,).
        # Por simplicidad supongamos que registro ya incluye 
        # todas las keys 'state_pos_0' … 'state_pos_{window_rl-1}', 'state_velocidad', etc.
        keys = [k for k in registro if k.startswith("state_")]
        return np.array([float(registro[k]) for k in sorted(keys)], dtype=float)

    def register_transition(self, registro):
        # 1) Actualizar round_counter
        self.round_counter += 1

        # 2) Build state y next_state
        # Asumimos que 'registro' trae las columnas de estado en 'state_pos_...' y 
        # de next_state en 'next_state_pos_...'. Si no, hay que “reconstruir” el estado.
        state_cols = {k: registro[k] for k in registro if k.startswith("state_")}
        next_cols  = {k: registro[k] for k in registro if k.startswith("next_state_")}

        state = np.array([float(state_cols[k]) for k in sorted(state_cols)], dtype=float)
        next_state = np.array([float(next_cols[k]) for k in sorted(next_cols)], dtype=float)

        action_idx = self.categories.index(registro["opcion_apuesta"])
        reward     = registro["ganancia"] / 500.0  # normalizar

        done = False  # podrías poner True si reinicias sesión, etc.

        # 3) Guardar en ambos buffers
        self.buffer_dqn.append((state, action_idx, reward, next_state, done))
        self.buffer_ppo.append((state, action_idx, reward, next_state, done))

        # 4) Actualizar estadísticas
        self.stats["dqn"]["total_reward"] += reward
        self.stats["dqn"]["count"] += 1
        self.stats["ppo"]["total_reward"] += reward
        self.stats["ppo"]["count"] += 1

        # 5) Guardar último state para choose()
        self._latest_state = state

        # 6) Cada self.meta_interval rondas, re‐evaluar agente
        if self.round_counter % self.meta_interval == 0:
            avg_dqn = (self.stats["dqn"]["total_reward"] /
                       max(1, self.stats["dqn"]["count"]))
            avg_ppo = (self.stats["ppo"]["total_reward"] /
                       max(1, self.stats["ppo"]["count"]))

            self.current_agent = "ppo" if avg_ppo >= avg_dqn else "dqn"
            # Resetear estadísticas
            self.stats["dqn"] = {"total_reward": 0.0, "count": 0}
            self.stats["ppo"] = {"total_reward": 0.0, "count": 0}

    def get_action(self):
        # 1) Seleccionar agente
        agent = self.current_agent

        # 2) Predecir acción
        state = self._latest_state
        if agent == "dqn":
            action_idx = self.dqn.select_action(state)
        else:
            action_idx, _ = self.ppo.select_action(state)

        categoria = self.categories[action_idx]
        # Por simplicidad devolvemos 1 ficha fija, pero podrías agregar money‐management
        return categoria, 1, agent

    def train_agents_online(self, batch_size=64):
        # 1) Si no hay suficientes muestras, abortar
        if len(self.buffer_dqn) < batch_size or len(self.buffer_ppo) < batch_size:
            return

        # 2) Muestreamos aleatorio sin reemplazo
        batch_dqn = random.sample(self.buffer_dqn, batch_size)
        batch_ppo = random.sample(self.buffer_ppo, batch_size)

        # 3) Extraer arrays
        states_dqn, actions_dqn, rewards_dqn, next_states_dqn, dones_dqn = zip(*batch_dqn)
        states_dqn = np.vstack(states_dqn)
        actions_dqn = np.array(actions_dqn)
        rewards_dqn = np.array(rewards_dqn, dtype=float)
        next_states_dqn = np.vstack(next_states_dqn)
        dones_dqn = np.array(dones_dqn, dtype=bool)

        states_ppo, actions_ppo, rewards_ppo, next_states_ppo, dones_ppo = zip(*batch_ppo)
        states_ppo = np.vstack(states_ppo)
        actions_ppo = np.array(actions_ppo)
        rewards_ppo = np.array(rewards_ppo, dtype=float)
        next_states_ppo = np.vstack(next_states_ppo)
        dones_ppo = np.array(dones_ppo, dtype=bool)

        # 4) Entrenar DQN
        self.dqn.train(
            batch_size = batch_size,
            states = states_dqn,
            actions = actions_dqn,
            rewards = rewards_dqn,
            next_states = next_states_dqn,
            dones = dones_dqn,
            epochs = 3
        )

        # 5) Entrenar PPO: calcular returns y ventajas
        gamma = 0.99
        returns = []
        G = 0
        # asumimos que aquí no hay “roll‐over” entre minibatches; 
        # simplemente calculamos retornos desde el final hacia atrás
        for r in rewards_ppo[::-1]:
            G = r + gamma * G
            returns.insert(0, G)
        returns = np.array(returns, dtype=float)

        # Valores estimados para states usando la cabeza de valor de PPO
        _, values = self.ppo.model.predict(states_ppo, verbose=0)
        values = values.flatten()

        advantages = returns - values
        logits, _ = self.ppo.model.predict(states_ppo, verbose=0)
        old_logp = tf.nn.log_softmax(logits).numpy()[np.arange(len(actions_ppo)), actions_ppo]

        self.ppo.train(
            states = states_ppo,
            actions = actions_ppo,
            advantages = advantages,
            returns = returns,
            old_log_probs = old_logp,
            epochs = 3,
            batch_size = batch_size
        )
