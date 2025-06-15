# wplay/strategy/meta_manager.py

import random
import numpy as np
import tensorflow as tf

class MetaStrategyManager:
    """
    Meta‐gestor que elige entre DQN y PPO usando un esquema ε-greedy
    y ajusta dinámicamente el agente preferido según reward histórico.
    """

    def __init__(self, dqn_agent, ppo_agent, categories, eps: float = 0.1):
        self.dqn = dqn_agent
        self.ppo = ppo_agent
        self.categories = categories

        # Buffers de transiciones para entrenamiento online
        self.buffer_dqn = []
        self.buffer_ppo = []

        # Estadísticas acumuladas de reward y conteos
        self.stats = {
            "dqn": {"total_reward": 0.0, "count": 0},
            "ppo": {"total_reward": 0.0, "count": 0},
        }

        # Cada cuántas rondas re‐evaluar el mejor agente
        self.meta_interval = 50
        self.round_counter = 0

        # ε para ε-greedy (exploración vs explotación)
        self.eps = eps

        # Agente “óptimo” actual (inicial al azar)
        self.current_agent = random.choice(["dqn", "ppo"])

        # Último estado observado
        self._latest_state = None

    def _build_state_vector(self, registro):
        """
        (Opcional) Reconstruye el vector de estado desde el registro.
        Aquí se asume que ya tienes 'state_...' en registro.
        """
        keys = [k for k in registro if k.startswith("state_")]
        return np.array([float(registro[k]) for k in sorted(keys)], dtype=float)

    def register_transition(self, registro):
        """
        1) Añade la transición (s, a, r, s') a ambos buffers.
        2) Acumula reward en stats.
        3) Cada `meta_interval` rondas, recalcula `current_agent`
           según el average reward de DQN vs PPO.
        """
        # ——— 1) Ronda ———
        self.round_counter += 1

        # ——— 2) Extraer state / next_state / acción / reward ———
        state_cols = {k: registro[k] for k in registro if k.startswith("state_")}
        next_cols  = {k: registro[k] for k in registro if k.startswith("next_state_")}
        state      = np.array([float(state_cols[k]) for k in sorted(state_cols)], dtype=float)
        next_state = np.array([float(next_cols[k]) for k in sorted(next_cols)], dtype=float)
        action_idx = self.categories.index(registro["opcion_apuesta"])
        reward     = registro["ganancia"] / 500.0  # normalizar por valor ficha base
        done       = False

        # ——— 3) Almacenar en buffers ———
        self.buffer_dqn.append((state, action_idx, reward, next_state, done))
        self.buffer_ppo.append((state, action_idx, reward, next_state, done))

        # ——— 4) Estadísticas ———
        for a in ("dqn", "ppo"):
            self.stats[a]["total_reward"] += reward
            self.stats[a]["count"]       += 1

        # ——— 5) Guardar último estado ———
        self._latest_state = state

        # ——— 6) Re‐evaluar agente cada `meta_interval` rondas ———
        if self.round_counter % self.meta_interval == 0:
            avg_dqn = self.stats["dqn"]["total_reward"] / max(1, self.stats["dqn"]["count"])
            avg_ppo = self.stats["ppo"]["total_reward"] / max(1, self.stats["ppo"]["count"])
            # Elegir agente con mejor average reward
            self.current_agent = "ppo" if avg_ppo >= avg_dqn else "dqn"
            # Resetear estadísticas
            self.stats = {
                "dqn": {"total_reward": 0.0, "count": 0},
                "ppo": {"total_reward": 0.0, "count": 0},
            }

    def get_action(self):
        """
        Devuelve la acción mediante ε-greedy:
          - con prob ε → explora (elige DQN o PPO al azar)
          - con prob 1-ε → explota (elige self.current_agent)
        Retorna: (categoría:str, fichas:int, etiqueta:str)
        """
        if self._latest_state is None:
            # Sin estado, fallback: categoría por defecto con DQN
            return self.categories[0], 1, "dqn"

        # ε-greedy
        if random.random() < self.eps:
            agent = random.choice(["dqn", "ppo"])
        else:
            agent = self.current_agent

        # Seleccionar acción del agente elegido
        if agent == "dqn":
            idx = self.dqn.select_action(self._latest_state)
        else:
            idx, _ = self.ppo.select_action(self._latest_state)

        cat = self.categories[idx]
        # Aquí fijo apuesta de 1 ficha; puedes ampliar money‐management
        return cat, 1, agent

    def train_agents_online(self, batch_size=64):
        """
        Entrena ambos agentes usando muestras de sus buffers.
        Se invoca típicamente tras cada `register_transition`.
        """
        # 1) Suficientes datos?
        if len(self.buffer_dqn) < batch_size or len(self.buffer_ppo) < batch_size:
            return

        # 2) Muestreo aleatorio sin reemplazo
        batch_dqn = random.sample(self.buffer_dqn, batch_size)
        batch_ppo = random.sample(self.buffer_ppo, batch_size)

        # 3) Separar arrays
        states_dqn, actions_dqn, rewards_dqn, next_states_dqn, dones_dqn = zip(*batch_dqn)
        states_dqn      = np.vstack(states_dqn)
        actions_dqn     = np.array(actions_dqn)
        rewards_dqn     = np.array(rewards_dqn, dtype=float)
        next_states_dqn = np.vstack(next_states_dqn)
        dones_dqn       = np.array(dones_dqn, dtype=bool)

        states_ppo, actions_ppo, rewards_ppo, next_states_ppo, dones_ppo = zip(*batch_ppo)
        states_ppo      = np.vstack(states_ppo)
        actions_ppo     = np.array(actions_ppo)
        rewards_ppo     = np.array(rewards_ppo, dtype=float)
        next_states_ppo = np.vstack(next_states_ppo)
        dones_ppo       = np.array(dones_ppo, dtype=bool)

        # 4) Entrenar DQN
        self.dqn.train(
            batch_size = batch_size,
            states     = states_dqn,
            actions    = actions_dqn,
            rewards    = rewards_dqn,
            next_states= next_states_dqn,
            dones      = dones_dqn,
            epochs     = 3
        )

        # 5) Entrenar PPO: calcular returns y ventajas
        gamma = 0.99
        returns = []
        G = 0.0
        for r in rewards_ppo[::-1]:
            G = r + gamma * G
            returns.insert(0, G)
        returns = np.array(returns, dtype=float)

        # Predicción de valores y logits
        logits, values = self.ppo.model.predict(states_ppo, verbose=0)
        values = values.flatten()
        advantages = returns - values
        old_logp = tf.nn.log_softmax(logits).numpy()[np.arange(len(actions_ppo)), actions_ppo]

        self.ppo.train(
            states        = states_ppo,
            actions       = actions_ppo,
            advantages    = advantages,
            returns       = returns,
            old_log_probs = old_logp,
            epochs        = 3,
            batch_size    = batch_size
        )
