# wplay/training/rl_trainer.py

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, Any
from sklearn.utils import shuffle

from wplay.env.env_manager import EnvManager
from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.replay_buffer import ReplayBuffer
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from wplay.strategy.constants import MONTO_MAX

class RLTrainer:
    """
    Entrenador híbrido para DQN + PPO que soporta:
      1) Preentrenamiento offline desde CSV de transiciones (rl_input.csv).
      2) Entrenamiento online en un EnvManager.
      3) Evaluación de la política.
    """

    def __init__(
        self,
        rl_csv_path: str,
        strategy_manager: StrategyManagerDL,
        dqn_agent: DQNAgent,
        ppo_agent: PPOAgent,
        buffer_size: int = 10000,
        batch_size: int = 64,
        train_interval: int = 50,
        gamma: float = 0.99,
        save_dir: Optional[str] = None
    ):
        # Entorno simulado para entrenamiento-online
        self.env              = EnvManager(rl_csv_path)
        self.strategy_manager = strategy_manager
        self.dqn              = dqn_agent
        self.ppo              = ppo_agent
        self.buffer           = ReplayBuffer(max_size=buffer_size)
        self.batch_size       = batch_size
        self.train_interval   = train_interval
        self.gamma            = gamma

        # Para preentrenamiento offline
        self.rl_csv_path      = rl_csv_path

        # Directorio de guardado
        self.save_dir = save_dir or "models/rl"
        os.makedirs(self.save_dir, exist_ok=True)

    def pretrain_offline(self, epochs: int = 5) -> None:
        """
        Preentrena DQN y PPO usando rl_input.csv en modo batch:
        1) Lee y alinea columnas state / next_state.
        2) Ajusta state_dim en los agentes si cambia.
        3) Preentrena DQN con train_offline().
        4) Calcula returns y GAE advantages.
        5) Extrae old_logprobs y preentrena PPO con train_offline().
        """
        # 1) Leer CSV
        df = pd.read_csv(self.rl_csv_path)
        cols = df.columns.tolist()

        # 2) Identificar features de estado y next_state
        state_cols = [c for c in cols if c not in ("action", "reward") and not c.startswith("next_")]
        next_cols  = [f"next_{c}" for c in state_cols if f"next_{c}" in cols]
        state_cols = [c for c in state_cols if f"next_{c}" in cols]

        # 3) Extraer arrays
        states      = df[state_cols].values.astype(np.float32)
        actions     = df["action"].values.astype(np.int32)
        rewards     = df["reward"].values.astype(np.float32)
        next_states = df[next_cols].values.astype(np.float32)
        dones       = np.zeros(len(states), dtype=bool)

        # Filtrar acciones fuera de rango
        mask = (actions >= 0) & (actions < self.dqn.action_dim)
        if not mask.all():
            states      = states[mask]
            actions     = actions[mask]
            rewards     = rewards[mask]
            next_states = next_states[mask]
            dones       = dones[mask]

        # 4) Ajustar state_dim en los agentes
        sd = states.shape[1]
        if sd != self.dqn.state_dim:
            self.dqn.rebuild_network(sd)
        if sd != self.ppo.state_dim:
            self.ppo.rebuild_network(sd)

        # 5) Preentrenar DQN offline
        dqn_loss = self.dqn.train_offline(
            states      = states,
            actions     = actions,
            rewards     = rewards,
            next_states = next_states,
            dones       = dones,
            batch_size  = self.batch_size,
            epochs      = epochs
        )
        if dqn_loss is not None:
            print(f"[RLTrainer] DQN offline avg_loss={dqn_loss:.4f}")

        # 6) Calcular Monte Carlo returns
        n = len(rewards)
        returns = np.zeros(n, dtype=np.float32)
        G = 0.0
        for i in reversed(range(n)):
            if dones[i]:
                G = 0.0
            G = rewards[i] + self.gamma * G
            returns[i] = G

        # 7) Calcular ventajas con GAE
        V = self.ppo.critic.predict(states, verbose=0).flatten()
        V = np.concatenate([V, [0.0]])
        lam = 0.95
        advantages = np.zeros(n, dtype=np.float32)
        gae = 0.0
        for i in reversed(range(n)):
            mask = 1.0 - float(dones[i])
            delta = rewards[i] + self.gamma * V[i+1] * mask - V[i]
            gae = delta + self.gamma * lam * mask * gae
            advantages[i] = gae
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # 8) Extraer old_logprobs
        probs = self.ppo.actor.predict(states, verbose=0)
        old_logprobs = np.log(
            np.sum(probs * tf.one_hot(actions, self.ppo.action_dim), axis=1)
            .clip(1e-8, 1.0)
        )

        # 9) Preentrenar PPO offline
        ppo_policy_loss = self.ppo.train_offline(
            states       = states,
            actions      = actions,
            returns      = returns,
            advantages   = advantages,
            old_logprobs = old_logprobs,
            batch_size   = self.batch_size,
            epochs       = epochs
        )
        if ppo_policy_loss is not None:
            print(f"[RLTrainer] PPO offline avg_policy_loss={ppo_policy_loss:.4f}")

        print(f"[RLTrainer] Preentrenamiento offline completado (epochs={epochs})\n")

    def train(
        self,
        num_episodes: int,
        max_steps_per_episode: Optional[int] = None
    ) -> None:
        """
        Bucle de entrenamiento online:
        - Cada paso recoge transiciones con StrategyManagerDL.
        - Actualiza DQN con train_online() y PPO con update().
        """
        for ep in range(1, num_episodes + 1):
            state     = self.env.reset()
            done      = False
            step      = 0
            ep_reward = 0.0

            while not done:
                algo, action = self.strategy_manager.select(state)
                next_state, reward, done, info = self.env.step(action)
                ep_reward += reward

                # Almacenar en buffer de mezcla (solo DQN lo usa)
                self.buffer.add(state, action, reward, next_state, done)

                # Cada train_interval pasos, entrenar online ambos agentes
                if self.buffer.size() >= self.batch_size and step % self.train_interval == 0:
                    # DQN online
                    dqn_loss = self.dqn.train_online(self.batch_size)
                    # PPO online
                    self.ppo.store_transition(state, action, _, reward, done, info.get("drawdown", 0.0))
                    ppo_metrics = self.ppo.update()

                    # Actualizar StrategyManager con reward shaped
                    shaped = reward - 0.5 * info.get("drawdown", 0.0)
                    self.strategy_manager.update(algo, shaped)

                state = next_state
                step += 1
                if max_steps_per_episode and step >= max_steps_per_episode:
                    break

            print(f"[RLTrainer] Ep {ep}/{num_episodes} — Reward: {ep_reward:.2f} — Steps: {step}")
            if ep % 10 == 0:
                self._save_models(ep)

        # Guardar al final
        self._save_models("final")

    def evaluate(
        self,
        num_episodes: int,
        max_steps_per_episode: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Evalúa la política combinada en modo greedy (ε=0).
        """
        rewards = []
        for ep in range(1, num_episodes + 1):
            state     = self.env.reset()
            done      = False
            ep_reward = 0.0
            step      = 0

            while not done:
                algo, action = self.strategy_manager.select(state, eval_mode=True)
                state, reward, done, _ = self.env.step(action)
                ep_reward += reward
                step += 1
                if max_steps_per_episode and step >= max_steps_per_episode:
                    break

            rewards.append(ep_reward)
            print(f"[RLTrainer][Eval] Ep {ep}: Reward {ep_reward:.2f}")

        return {
            "avg_reward": float(np.mean(rewards)),
            "min_reward": float(np.min(rewards)),
            "max_reward": float(np.max(rewards))
        }

    def _save_models(self, tag: Any) -> None:
        """
        Guarda DQN, PPO y StrategyManager en disco.
        """
        dqn_path = os.path.join(self.save_dir, f"dqn_agent_{tag}.h5")
        ppo_path = os.path.join(self.save_dir, f"ppo_agent_{tag}.h5")
        sm_path  = os.path.join(self.save_dir, f"strategy_manager_{tag}.pkl")

        self.dqn.save(dqn_path)
        self.ppo.actor.save(ppo_path.replace('.h5', '_actor.h5'))
        self.ppo.critic.save(ppo_path.replace('.h5', '_critic.h5'))
        self.strategy_manager.save(sm_path)
        print(f"[RLTrainer] Modelos guardados con tag '{tag}'")
