import logging
import numpy as np
import os
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Any

class PBTManager:
    """
    Population-Based Training manager para entrenadores RL.
    Realiza exploit‐explore sobre una población de RLTrainer clonados,
    que internamente contienen su HyperParams.
    """

    def __init__(
        self,
        trainers: List[Any],
        hyperparam_keys: List[str],
        perturb_fns: Dict[str, Callable[[Any], Any]],
        top_fraction: float = 0.5,
        checkpoint_dir: str = "pbt_checkpoints",
        seed: int = None
    ):
        self.trainers = trainers
        self.hyperparam_keys = hyperparam_keys
        self.perturb_fns = perturb_fns
        self.pop_size = len(trainers)
        self.topk = max(1, int(self.pop_size * top_fraction))
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        # RNG propio para reproducibilidad
        self.rng = np.random.RandomState(seed)

        logging.info(f"[PBT] Inicializado pop_size={self.pop_size}, topk={self.topk}, seed={seed}")

        # Validar que los hyperparam_keys existan en HyperParams
        for k in hyperparam_keys:
            assert hasattr(trainers[0].hp, k), f"HyperParams no tiene atributo '{k}'"

    def run_generation(
        self,
        episodes_per_trainer: int,
        parallel: bool = True,
    ) -> List[float]:
        """
        Entrena cada RLTrainer en modo online y devuelve lista de avg rewards.
        Registra estadísticas de la generación.
        """
        if parallel:
            with ThreadPoolExecutor(max_workers=self.pop_size) as executor:
                rewards = list(executor.map(lambda tr: tr.train_online(episodes_per_trainer), self.trainers))
        else:
            rewards = [tr.train_online(episodes_per_trainer) for tr in self.trainers]

        mean_reward = float(np.mean(rewards))
        std_reward  = float(np.std(rewards))
        min_reward  = float(np.min(rewards))
        max_reward  = float(np.max(rewards))
        logging.info(f"[PBT] Gen stats → mean: {mean_reward:.4f}, std: {std_reward:.4f}, "
                     f"min: {min_reward:.4f}, max: {max_reward:.4f}")

        for tr, avg in zip(self.trainers, rewards):
            logging.info(f"[PBT] {tr.name} avg_reward={avg:.4f}")

        return rewards

    def exploit_and_explore(self, rewards: List[float]) -> None:
        """
        Reemplaza a los peores trainers por copias de los mejores y perturba hiperparámetros.
        Aplica elitismo: los topk no cambian.
        """
        ranks = np.argsort(rewards)[::-1]
        top_idxs = ranks[:self.topk]
        bot_idxs = ranks[self.topk:]

        for b in bot_idxs:
            t = int(self.rng.choice(top_idxs))
            top = self.trainers[t]
            bot = self.trainers[b]

            # --- EXPLOIT: copiar redes completas ---
            # DQN
            bot.dqn_agent.q_network.set_weights(top.dqn_agent.q_network.get_weights())
            bot.dqn_agent.target_network.set_weights(top.dqn_agent.target_network.get_weights())
            # PPO
            bot.ppo_agent.actor.set_weights(top.ppo_agent.actor.get_weights())
            bot.ppo_agent.critic.set_weights(top.ppo_agent.critic.get_weights())
            # Meta-selector
            bs = bot.strategy_manager
            ts = top.strategy_manager
            bs.model.set_weights(ts.model.get_weights())
            bs.counts, bs.values = ts.counts.copy(), ts.values.copy()
            bs.total_counts, bs.successes, bs.failures = ts.total_counts, ts.successes.copy(), ts.failures.copy()

            # --- EXPLORE: mutar hiperparámetros ---
            for key in self.hyperparam_keys:
                if key in self.perturb_fns:
                    old_hp = getattr(top.hp, key)
                    new_hp = self.perturb_fns[key](old_hp)
                    setattr(bot.hp, key, new_hp)
                    logging.debug(f"[PBT] {bot.name}.hp.{key}: {old_hp} → {new_hp}")

                    # Propagar al agente DQN
                    if hasattr(bot.dqn_agent, key):
                        setattr(bot.dqn_agent, key, new_hp)
                        # Ejemplo: actualizar lr si aplica
                        try:
                            bot.dqn_agent.optimizer.learning_rate.assign(new_hp)
                        except Exception:
                            pass

                    # Propagar al agente PPO
                    if hasattr(bot.ppo_agent, key):
                        setattr(bot.ppo_agent, key, new_hp)
                        try:
                            bot.ppo_agent.actor_optimizer.learning_rate.assign(new_hp)
                            bot.ppo_agent.critic_optimizer.learning_rate.assign(new_hp)
                        except Exception:
                            pass

                    # Ajuste específico del selector
                    if key == 'meta_window' and hasattr(bs, 'window'):
                        bs.window = new_hp

    def step(self, episodes_per_trainer: int, generation: int) -> List[float]:
        """
        Ejecuta una generación completa (train + exploit_explore) y guarda:
         - Checkpoint JSON (hp y reward)
         - Pesos de los topk modelos bajo            
        """
        rewards = self.run_generation(episodes_per_trainer)
        self.exploit_and_explore(rewards)

        # Guardar snapshot de hp y rewards
        snapshot = []
        for tr, r in zip(self.trainers, rewards):
            snapshot.append({'name': tr.name, 'reward': r, 'hp': tr.hp.__dict__})
        path = os.path.join(self.checkpoint_dir, f"pop_gen{generation}.json")
        with open(path, 'w') as f:
            json.dump(snapshot, f, indent=2)
        logging.info(f"[PBT] Checkpoint guardado: {path}")

        # Guardar pesos de los mejores
        for idx in np.argsort(rewards)[-self.topk:]:
            tr = self.trainers[idx]
            tr.dqn_agent.save(os.path.join(self.checkpoint_dir, f"{tr.name}_dqn_gen{generation}"))
            tr.ppo_agent.save(os.path.join(self.checkpoint_dir, f"{tr.name}_ppo_gen{generation}"))

        return rewards

    def clone(self) -> 'PBTManager':
        """
        Retorna una copia profunda de este PBTManager (con trainers clonados).
        """
        cloned_trainers = [tr.clone() for tr in self.trainers]
        return PBTManager(
            trainers=cloned_trainers,
            hyperparam_keys=list(self.hyperparam_keys),
            perturb_fns=dict(self.perturb_fns),
            top_fraction=self.topk / self.pop_size,
            checkpoint_dir=self.checkpoint_dir,
            seed=None
        )
