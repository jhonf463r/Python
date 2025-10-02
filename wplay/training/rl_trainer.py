import logging
import os
import json
import numpy as np
import random     
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, Any
from copy import deepcopy
from wplay.env.env_manager import EnvModel
from wplay.strategy.replay_buffer import ReplayBuffer
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from tqdm import trange
from wplay.wplay_config.hyperparams import HyperParams
class RLTrainer:
    def __init__(
        self,
        clean_csv_path: str,
        rl_csv_path: str,
        strategy_manager,
        dqn_agent_cls,
        ppo_agent_cls,
        *args,
        **kwargs
    ):
        # Semilla global para reproducibilidad
        seed = None
        if 'hp' in kwargs and hasattr(kwargs['hp'], 'env_seed'):
            seed = kwargs['hp'].env_seed
        if seed is not None:
            os.environ['PYTHONHASHSEED'] = str(seed)
            random.seed(seed)
            np.random.seed(seed)
            tf.random.set_seed(seed)

        # MODO NUEVO
        if 'hp' in kwargs:
            hp: HyperParams = kwargs.pop('hp')
            save_dir = kwargs.pop('save_dir', None)

            # 0) Guardar configuraciones
            self.hp = hp
            self.clean_csv_path = clean_csv_path
            self.rl_csv_path = rl_csv_path
            self.strategy_manager = strategy_manager
            self.dqn_agent_cls = dqn_agent_cls
            self.ppo_agent_cls = ppo_agent_cls
            self.save_dir = save_dir or hp.rl_save_dir
            os.makedirs(self.save_dir, exist_ok=True)
            self.name = os.path.basename(self.save_dir) or "RLTrainer"

            # 1) Hypernetwork para MetaSelector
            from wplay.models.hypernetwork import build_hypernetwork
            self.hypernet = build_hypernetwork(hp)

            # 2) Parámetros RL
            self.buffer_size    = hp.rl_buffer_size
            self.batch_size     = hp.rl_batch_size
            self.train_interval = hp.rl_train_interval
            self.gamma          = hp.rl_gamma

            # 3) Rutas modelos
            dqn_path = os.path.join(self.save_dir, 'dqn_model')
            ppo_path = os.path.join(self.save_dir, 'ppo_model')
            self.dqn_model_path = dqn_path
            self.ppo_model_path = ppo_path

            # 4) Entorno con CSVs correctos
            self.env = EnvModel(
                state_csv      = clean_csv_path,
                transition_csv = rl_csv_path,
                shuffle        = hp.env_shuffle,
                seed           = hp.env_seed
            )

            # 5) Dimensiones
            df_rl = pd.read_csv(self.rl_csv_path, usecols=['action'])
            self.action_dim = int(df_rl['action'].max()) + 1
            self.state_dim = getattr(self.strategy_manager, 'state_dim_total', self.env.state_dim)
            self.state_dim_total = self.state_dim

            # 6) Replay buffer
            self.buffer = ReplayBuffer(max_size=hp.rl_buffer_size)

            # 7) Lista de features offline
            feature_file = os.path.join(self.save_dir, hp.feature_list_filename)
            if os.path.exists(feature_file):
                with open(feature_file, 'r') as f:
                    self.feature_cols = json.load(f)
            else:
                df_head = pd.read_csv(self.rl_csv_path, nrows=1)
                self.feature_cols = [
                    c for c in df_head.columns
                    if c not in ('action','reward','done') and not c.startswith('next_')
                ]
                with open(feature_file, 'w') as f:
                    json.dump(self.feature_cols, f)

            # 8) Agentes
            self.dqn_agent = dqn_agent_cls(
                state_dim=self.state_dim,
                action_dim=self.action_dim,
                hp=hp
            )
            self.ppo_agent = ppo_agent_cls(
                state_dim=self.state_dim,
                action_dim=self.action_dim,
                hp=hp
            )
            self.dqn = self.dqn_agent
            self.ppo = self.ppo_agent

            # 9) Intentar cargar pesos precargados (modo offline skip)
            self._skip_offline = False

            # Para DQN, buscamos archivos *_q_network.h5 y *_target_network.h5
            dqn_q_path      = os.path.join(self.save_dir, 'dqn_model_q_network.h5')
            dqn_target_path = os.path.join(self.save_dir, 'dqn_model_target_network.h5')
            # Para PPO, actor y critic
            ppo_actor_path  = os.path.join(self.save_dir, 'ppo_model_actor.h5')
            ppo_critic_path = os.path.join(self.save_dir, 'ppo_model_critic.h5')

            # Cargar DQN si existen ambas redes
            if os.path.exists(dqn_q_path) and os.path.exists(dqn_target_path):
                try:
                    self.dqn_agent.q_network.load_weights(dqn_q_path)
                    self.dqn_agent.target_network.load_weights(dqn_target_path)
                    logging.info(f"[RLTrainer] DQN redes cargadas desde {dqn_q_path} y {dqn_target_path}")
                    self._skip_offline = True
                except Exception as e:
                    logging.warning(f"[RLTrainer] Falló carga DQN: {e}")

            # Cargar PPO si existen actor y critic
            if os.path.exists(ppo_actor_path) and os.path.exists(ppo_critic_path):
                try:
                    self.ppo_agent.actor.load_weights(ppo_actor_path)
                    self.ppo_agent.critic.load_weights(ppo_critic_path)
                    logging.info(f"[RLTrainer] PPO actor/critic cargados desde {ppo_actor_path} y {ppo_critic_path}")
                    self._skip_offline = True
                except Exception as e:
                    logging.warning(f"[RLTrainer] Falló carga PPO: {e}")

            # 10) Metadata
            meta_file = os.path.join(self.save_dir, 'meta.json')
            with open(meta_file, 'w') as f:
                json.dump({'state_dim': self.state_dim, 'action_dim': self.action_dim}, f)

            return

        # MODO LEGACY: construir hp mínimo
        dqn_kwargs     = kwargs.pop('dqn_kwargs', {})
        ppo_kwargs     = kwargs.pop('ppo_kwargs', {})
        buffer_size    = kwargs.pop('buffer_size', 10000)
        batch_size     = kwargs.pop('batch_size', 64)
        train_interval = kwargs.pop('train_interval', 50)
        gamma          = kwargs.pop('gamma', 0.99)
        save_dir       = kwargs.pop('save_dir', None)

        partial_hp = HyperParams(
            dqn_lr              = dqn_kwargs.get('learning_rate', 1e-3),
            dqn_lr_decay_rate   = 0.5,
            dqn_gamma           = dqn_kwargs.get('gamma', gamma),
            dqn_tau             = dqn_kwargs.get('tau', 0.005),
            dqn_eps_start       = dqn_kwargs.get('eps_start', 1.0),
            dqn_eps_mid         = dqn_kwargs.get('eps_mid', 0.2),
            dqn_eps_final       = dqn_kwargs.get('eps_final', 0.01),
            dqn_phase1          = dqn_kwargs.get('phase1', 10000),
            dqn_phase2          = dqn_kwargs.get('phase2', 50000),
            dqn_hidden          = dqn_kwargs.get('hidden_units', [64,64]),
            dqn_buffer_capacity = buffer_size,
            ppo_lr_actor        = ppo_kwargs.get('lr_actor', 1e-4),
            ppo_lr_critic       = ppo_kwargs.get('lr_critic', 3e-4),
            ppo_use_lr_schedule = False,
            ppo_lr_decay_steps  = 10000,
            ppo_lr_decay_rate   = 0.9,
            ppo_gamma           = ppo_kwargs.get('gamma', gamma),
            ppo_lam             = ppo_kwargs.get('lam', 0.95),
            ppo_eps_clip        = ppo_kwargs.get('eps_clip', 0.2),
            ppo_K_epochs        = 3,
            ppo_entropy_coef    = 0.01,
            ppo_value_coef      = 0.5,
            ppo_actor_hidden    = ppo_kwargs.get('actor_hidden_units', [64,64]),
            ppo_critic_hidden   = ppo_kwargs.get('critic_hidden_units', [64,64]),
            meta_model_path     = "",
            meta_strategies     = ["dqn","ppo","skip"],
            meta_window         = 30,
            meta_lr             = 1e-3,
            meta_epochs         = 1,
            meta_batch_size     = 30,
            meta_ucb_c          = 1.0,
            meta_use_ts         = True,
            L_thresh            = 0.4,
            H_thresh            = 0.6,
            ENT_thresh          = 0.8,
            meta_stats_dim      = 4,
            hyper_num_coeffs    = 4,
            hyper_hidden_units  = [32,32],
            hyper_model_path    = None,
            env_shuffle         = False,
            env_seed            = seed,
            rl_buffer_size      = buffer_size,
            rl_batch_size       = batch_size,
            rl_train_interval   = train_interval,
            rl_gamma            = gamma,
            rl_save_dir         = save_dir or "models/rl",
            feature_list_filename = "feature_list.json",
            pbt_top_fraction    = 0.5,
            cooldown            = 1.0,
            wager_value         = 1,
            max_drawdown        = 1.0,
            gain_reset_threshold = 1.0
        )

        # Reusar modo nuevo
        new = RLTrainer(
            clean_csv_path,
            rl_csv_path,
            strategy_manager,
            dqn_agent_cls,
            ppo_agent_cls,
            hp=partial_hp,
            save_dir=save_dir
        )
        self.__dict__.update(new.__dict__)

    def pretrain_offline(self, epochs: int = 5) -> None:
        """
        Preentrenamiento batch desde rl_csv_path.
        - Si self._skip_offline es True, se omite.
        - Usa siempre self.feature_cols para construir estados y next_states.
        - Reconstruye agentes según state_dim_dqn y state_dim_total.
        - Restaura la dimensión original al final.
        """
        import pandas as pd
        import numpy as np
        import logging

        if self._skip_offline:
            logging.info("[RLTrainer] Saltando preentrenamiento offline (pesos precargados).")
            return

        # 1) Columnas de estado y next_state
        state_cols      = self.feature_cols
        next_state_cols = [f"next_{c}" for c in state_cols]
        sd_total = len(state_cols)   # dim total para PPO
        sd_dqn   = getattr(self.strategy_manager, "state_dim_dqn", sd_total)

        logging.info(f"[RLTrainer] Preentrenando offline con {sd_total} features.")

        # 2) Reconstruir agentes para offline
        logging.info(f"[RLTrainer] Reconstruyendo DQN a state_dim={sd_dqn}")
        self.dqn_agent.rebuild_network(sd_dqn)
        logging.info(f"[RLTrainer] Reconstruyendo PPO a state_dim={sd_total}")
        self.ppo_agent.rebuild_network(sd_total)

        # 3) Cargar CSV completo de transiciones
        df = pd.read_csv(self.rl_csv_path)
        for col in ("action", "reward", "done"):
            if col not in df.columns:
                logging.error(f"[RLTrainer] Falta columna '{col}' en {self.rl_csv_path}")
                return

        # 4) Asegurar next_* en el DataFrame
        for col in state_cols:
            ncol = f"next_{col}"
            if ncol not in df.columns:
                df[ncol] = df[col].shift(-1)
        df = df.iloc[:-1].reset_index(drop=True)

        # 5) Convertir a numpy
        S_full      = df[state_cols].to_numpy(np.float32)
        S_next_full = df[next_state_cols].to_numpy(np.float32)
        A           = df["action"].to_numpy(np.int32)
        R           = df["reward"].to_numpy(np.float32)
        D           = df["done"].to_numpy(bool)

        # 6) Filtrar acciones fuera de rango
        valid = (A >= 0) & (A < self.action_dim)
        if not valid.any():
            logging.error("[RLTrainer] No hay acciones válidas en el CSV offline.")
            return
        S_full      = S_full[valid]
        S_next_full = S_next_full[valid]
        A           = A[valid]
        R           = R[valid]
        D           = D[valid]

        # 7) Preparar arrays para DQN (solo primeras sd_dqn columnas)
        S_dqn      = S_full[:, :sd_dqn]
        S_next_dqn = S_next_full[:, :sd_dqn]

        # 8) Entrenar DQN offline
        dqn_loss = self.dqn_agent.train_offline(
            states      = S_dqn,
            actions     = A,
            rewards     = R,
            next_states = S_next_dqn,
            dones       = D,
            batch_size  = self.batch_size,
            epochs      = epochs
        )
        if dqn_loss is not None:
            logging.info(f"[RLTrainer] DQN offline avg_loss={dqn_loss:.4f}")

        # 9) Calcular retornos y ventajas para PPO
        n = len(R)
        returns = np.zeros(n, dtype=np.float32)
        G = 0.0
        for i in reversed(range(n)):
            if D[i]:
                G = 0.0
            G = R[i] + self.gamma * G
            returns[i] = G

        # La red crítica de PPO espera state_full (todas las dimensiones)
        V = self.ppo_agent.critic.predict(S_full, verbose=0).flatten()
        V = np.concatenate([V, [0.0]], axis=0)
        lam = getattr(self.ppo_agent, 'lam', 0.95)

        advantages = np.zeros(n, dtype=np.float32)
        gae = 0.0
        for i in reversed(range(n)):
            mask = 1.0 - float(D[i])
            delta = R[i] + self.gamma * V[i+1] * mask - V[i]
            gae = delta + self.gamma * lam * mask * gae
            advantages[i] = gae
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        probs = self.ppo_agent.actor.predict(S_full, verbose=0)
        actions_onehot = np.eye(self.action_dim, dtype=np.float32)[A]
        old_logprobs = np.log((probs * actions_onehot).sum(axis=1).clip(1e-8,1.0))

        # 10) Entrenar PPO offline
        ppo_loss = self.ppo_agent.train_offline(
            states       = S_full,
            actions      = A,
            returns      = returns,
            advantages   = advantages,
            old_logprobs = old_logprobs,
            batch_size   = self.batch_size,
            epochs       = epochs
        )
        if ppo_loss is not None:
            logging.info(f"[RLTrainer] PPO offline avg_policy_loss={ppo_loss:.4f}")

        logging.info(f"[RLTrainer] Preentrenamiento offline completado (epochs={epochs})")

        # 11) Guardar pesos entrenados
        try:
            self.dqn_agent.save(self.dqn_model_path)
        except Exception as e:
            logging.warning(f"[RLTrainer] ERROR guardando DQN: {e}")
        try:
            self.ppo_agent.save(self.ppo_model_path)
        except Exception as e:
            logging.warning(f"[RLTrainer] ERROR guardando PPO: {e}")

          # 12) Restaurar a la dimensión de producción (features filtradas)
        runtime_dim = len(self.feature_cols)
        logging.info(f"[RLTrainer] Restaurando DQN a state_dim={runtime_dim}")
        self.dqn_agent.rebuild_network(runtime_dim)
        logging.info(f"[RLTrainer] Restaurando PPO a state_dim={runtime_dim}")
        self.ppo_agent.rebuild_network(runtime_dim)
        logging.info("[RLTrainer] Preentrenamiento offline completado y agentes listos para online.")


    def train(
        self,
        num_episodes: int,
        max_steps_per_episode: Optional[int] = None,
        reward_shaping_factor: float = 0.5
    ) -> None:
        """
        Entrenamiento online en el entorno, mezclando DQN y PPO.
        - Usa select_strategy(state) para coherencia.
        - Consume estados ya preprocesados por EnvModel.pipeline.
        - Aplica reward_shaping_factor sobre drawdown almacenado en StrategyManagerDL.last_state.
        - Usa el flag `done` para resetear los hidden states de DQN/PPO tras cada episodio.
        """
        for ep in range(1, num_episodes + 1):
            # 1) Estado inicial (preprocesado)
            state = self.env.reset()  # np.ndarray shape (state_dim,)
            done = False
            step = 0
            ep_reward = 0.0

            while not done:
                # 2) Selección de estrategia
                strat = self.strategy_manager.select_strategy(state)

                # 3) Acción y transición
                if strat == 'skip':
                    next_state, reward, done = self.env.step(None)
                    action = None
                else:
                    agent = getattr(self, f"{strat}_agent")
                    action = agent.select_action(state)  # recibe (state_dim,)
                    next_state, reward, done = self.env.step(action)

                # 4) Reward shaping usando drawdown del último estado
                last_state = getattr(self.strategy_manager, 'last_state', None)
                if last_state is not None and last_state.size >= 2:
                    drawdown = float(last_state[-2])
                else:
                    drawdown = 0.0
                shaped_reward = reward - reward_shaping_factor * drawdown
                ep_reward += reward

                # 5) Almacenar transacción para DQN y PPO
                self.buffer.add(state, action, reward, next_state, done)
                # PPO internamente guarda la transición con done:
                self.ppo_agent.store_transition(state, action, reward, next_state, done)

                # 6) Actualizaciones periódicas
                if self.buffer.size() >= self.batch_size and step % self.train_interval == 0:
                    # Actualiza DQN
                    self.dqn_agent.train_online(self.batch_size)
                    # Actualiza PPO (usa sus propios batches internos)
                    self.ppo_agent.update()
                    # Actualiza meta‐selector con la recompensa shaped
                    self.strategy_manager.update(strat, shaped_reward)

                # 7) Si este paso cerró un episodio, resetear hidden states
                if done:
                    # Limpia las memorias internas de RNN o LSTM de cada agente
                    try:
                        self.dqn_agent.reset_hidden_state()
                    except AttributeError:
                        pass
                    try:
                        self.ppo_agent.reset_hidden_state()
                    except AttributeError:
                        pass

                # 8) Avanzar ciclo
                state = next_state
                step += 1
                if max_steps_per_episode and step >= max_steps_per_episode:
                    break

            # 9) Logging de fin de episodio
            logging.info(f"[RLTrainer] Ep {ep}/{num_episodes} — Reward raw: {ep_reward:.2f} — Steps: {step}")

            # 10) Checkpoints cada 10 episodios
            if ep % 10 == 0:
                self._save_models(ep)

        # 11) Guardar al final
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
            state = self.env.reset()
            done = False
            ep_reward = 0.0
            step = 0

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
        Guarda DQN, PPO y StrategyManager en disco con un tag.
        Se corrigen los nombres de atributos: usa self.dqn_agent y self.ppo_agent.
        """
        dqn_path = os.path.join(self.save_dir, f"dqn_agent_{tag}.keras")
        ppo_path = os.path.join(self.save_dir, f"ppo_{tag}")  # actor y critic
        sm_path  = os.path.join(self.save_dir, f"strategy_manager_{tag}.pkl")

        # Guardar DQN
        try:
            self.dqn_agent.save(dqn_path)
            logging.info(f"[RLTrainer] DQN guardado en {dqn_path}")
        except Exception as e:
            logging.error(f"[RLTrainer] Error guardando DQN con tag '{tag}': {e}")

        # Guardar PPO (actor y critic)
        try:
            self.ppo_agent.save(ppo_path)
            logging.info(f"[RLTrainer] PPO guardado en {ppo_path}")
        except Exception as e:
            logging.error(f"[RLTrainer] Error guardando PPO con tag '{tag}': {e}")

        # Guardar StrategyManager
        try:
            with open(sm_path, 'wb') as f:
                import pickle
                pickle.dump(self.strategy_manager, f)
            logging.info(f"[RLTrainer] StrategyManager guardado en {sm_path}")
        except Exception as e:
            logging.error(f"[RLTrainer] Error guardando strategy_manager con tag '{tag}': {e}")


    def train_online(self, episodes: int) -> float:
        """
        Ejecuta 'episodes' episodios en simulación usando:
        • self.env
        • self.strategy_manager (MetaStrategySelector)
        • self.dqn_agent, self.ppo_agent
        Retorna la recompensa media, mostrando una barra de progreso.
        """
        total_reward = 0.0

        for ep in trange(episodes, desc=f"{self.name} train_online", unit="ep", leave=False):
            # 1) Estado inicial preprocesado
            state = self.env.reset()  # np.ndarray shape (state_dim,)
            done  = False
            ep_reward = 0.0

            # 2) Loop por pasos del episodio
            while not done:
                # 2.1) Elegir estrategia
                strat = self.strategy_manager.select_strategy(state)

                # 2.2) Obtener acción y transición
                if strat == 'skip':
                    next_state, reward, done = self.env.step(None)
                    action = None
                else:
                    agent = getattr(self, f"{strat}_agent")
                    action = agent.select_action(state)  # recibe shape (state_dim,)
                    next_state, reward, done = self.env.step(action)

                # 2.3) Acumular recompensa
                ep_reward += reward

                # 2.4) Avanzar estado
                state = next_state

            total_reward += ep_reward

        # 3) Calcular y loggear recompensa media
        avg = total_reward / episodes
        logging.info(f"[RLTrainer] {self.name} train_online avg_reward={avg:.4f}")
        return avg


    def clone(self) -> 'RLTrainer':
        """
        Clona este RLTrainer para PBT:
        - deepcopy de HyperParams
        - deepcopy del strategy_manager
        - nuevo save_dir
        """
        # 1) Clonar hyperparams y strategy_manager
        new_hp = deepcopy(self.hp)
        new_sm = deepcopy(self.strategy_manager)

        # 2) Definir nuevo directorio de guardado
        clone_dir = os.path.join(self.save_dir, f"{self.name}_clone")

        # 3) Instanciar el clon
        clone = RLTrainer(
            clean_csv_path   = self.clean_csv_path,
            rl_csv_path      = self.rl_csv_path,
            strategy_manager = new_sm,
            dqn_agent_cls    = self.dqn_agent_cls,
            ppo_agent_cls    = self.ppo_agent_cls,
            hp               = new_hp,
            save_dir         = clone_dir
        )

        # 4) Logging para verificar los hyperparams del clon
        logging.info(f"[RLTrainer.clone] Clon creado: {clone.name}")
        logging.debug(f"[RLTrainer.clone] HP clon: {clone.hp.__dict__}")

        return clone
