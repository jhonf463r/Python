import os
import json
import logging
import numpy as np
import tensorflow as tf
from tensorflow.keras import mixed_precision
from concurrent.futures import ThreadPoolExecutor
from wplay.wplay_config.hyperparams import HyperParams
from wplay.env.env_manager import EnvModel
from wplay.strategy.pbt import PBTManager
from wplay.strategy.meta_strategy_selector import MetaStrategySelector
from wplay.models.hypernetwork import build_hypernetwork
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from wplay.training.rl_trainer import RLTrainer
import random

# ——— Semilla global ———
SEED = 42
os.environ['PYTHONHASHSEED'] = str(SEED)
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

# ——— Politica de precisión mixta ———
# Elige UNA sola de estas:
mixed_precision.set_global_policy('mixed_float16')  # para acelerar GPU
# mixed_precision.set_global_policy('float32')     # para máxima compatibilidad

# ——— Logging ———
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# ——— Configuración de hilos y GPU (sin tocar mixed_precision de nuevo) ———
tf.config.threading.set_intra_op_parallelism_threads(os.cpu_count())
tf.config.threading.set_inter_op_parallelism_threads(os.cpu_count())

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    logging.info(f"GPUs disponibles: {gpus}")
else:
    logging.warning("No se detectó GPU, usando CPU.")
# ─── Perturbaciones serializables (nivel módulo) ───
def perturb_dqn_lr(x: float) -> float:
    return float(np.clip(x * np.random.uniform(0.8, 1.2), 1e-5, 1e-1))

def perturb_dqn_gamma(x: float) -> float:
    return float(np.clip(x + np.random.normal(0, 0.01), 0.9, 0.999))

def perturb_ppo_eps_clip(x: float) -> float:
    return float(np.clip(x * np.random.uniform(0.8, 1.2), 0.05, 0.3))

def perturb_meta_window(x: int) -> int:
    return int(np.clip(x + np.random.randint(-5, 6), 10, 100))


def main():
    # 1) Parámetros de experimento
    pop_size         = 5
    generations      = 10
    episodes_per_gen = 20

    # 2) HyperParams base
    base_hp = HyperParams(
        # DQN
        dqn_lr=1e-3, dqn_lr_decay_rate=0.5, dqn_gamma=0.99, dqn_tau=0.005,
        dqn_eps_start=1.0, dqn_eps_mid=0.2, dqn_eps_final=0.01,
        dqn_phase1=10000, dqn_phase2=50000, dqn_hidden=[64,64],
        dqn_buffer_capacity=100000,
        # PPO
        ppo_lr_actor=1e-4, ppo_lr_critic=3e-4, ppo_use_lr_schedule=False,
        ppo_lr_decay_steps=10000, ppo_lr_decay_rate=0.9,
        ppo_gamma=0.99, ppo_lam=0.95, ppo_eps_clip=0.2,
        ppo_K_epochs=3, ppo_entropy_coef=0.01, ppo_value_coef=0.5,
        ppo_actor_hidden=[64,64], ppo_critic_hidden=[64,64],
        # MetaStrategySelector
        meta_model_path="wplay/models/meta_strategy_selector.keras",
        meta_strategies=["dqn","ppo","skip"], meta_window=30,
        meta_lr=1e-3, meta_epochs=3, meta_batch_size=32,
        meta_ucb_c=1.0, meta_use_ts=True,
        L_thresh=0.4, H_thresh=0.6, ENT_thresh=0.8,
        # Hypernetwork
        meta_stats_dim=4, hyper_num_coeffs=4,
        hyper_hidden_units=[32,32], hyper_model_path=None,
        # RLTrainer
        env_shuffle=False, env_seed=42,
        rl_buffer_size=20000, rl_batch_size=128,
        rl_train_interval=50, rl_gamma=0.99,
        rl_save_dir="wplay/models/rl",
        feature_list_filename="feature_list.json",
        # PBTManager
        pbt_top_fraction=0.5,
        # BettingEngine (opcional)
        cooldown=1.0, wager_value=10,
        max_drawdown=0.2, gain_reset_threshold=0.05
    )

    # 3) Rutas a CSVs
    CLEAN_CSV = os.path.join("wplay","wplay","data","clean_records.csv")
    RL_CSV    = os.path.join("wplay","wplay","data","rl_input.csv")

    # 4) Construir entorno (usa rl_input.csv para reward/done)
    env = EnvModel(
    state_csv      = CLEAN_CSV,
    transition_csv = RL_CSV,
    shuffle        = base_hp.env_shuffle,
    seed           = base_hp.env_seed
)
    hypernet = build_hypernetwork(base_hp)
    selector = MetaStrategySelector(
        state_dim=env.state_dim,
        action_dim=env.action_dim,
        hypernet=hypernet,
        hp=base_hp
    )
    # 4.1) Forzar que se use feature_list.json si existe
    feature_list_path = os.path.join("wplay", "wplay", "models", base_hp.feature_list_filename)
    if os.path.exists(feature_list_path):
        with open(feature_list_path, "r") as f:
            selected_features = json.load(f)
        env.filter_state_features(selected_features)
        logging.info(f"[run_pbt] Usando features filtrados: {len(selected_features)} columnas")
    else:
        logging.warning("[run_pbt] No se encontró feature_list.json, usando todas las columnas.")


    # 5) Función para generar RLTrainer con CSV invertidos
    def make_trainer(hp: HyperParams) -> RLTrainer:
        return RLTrainer(
            clean_csv_path   = CLEAN_CSV,  # solo para features
            rl_csv_path      = RL_CSV,     # para transiciones
            strategy_manager = selector,
            dqn_agent_cls    = DQNAgent,
            ppo_agent_cls    = PPOAgent,
            hp               = hp,
            save_dir         = None
        )

       # ─── 6) Inicializar población y PBTManager ───
    trainers = [make_trainer(base_hp) for _ in range(pop_size)]
    pbt = PBTManager(
        trainers        = trainers,
        hyperparam_keys = [
            'dqn_lr','dqn_gamma','ppo_eps_clip','meta_window'
        ],
        perturb_fns     = {
            'dqn_lr':       perturb_dqn_lr,
            'dqn_gamma':    perturb_dqn_gamma,
            'ppo_eps_clip': perturb_ppo_eps_clip,
            'meta_window':  perturb_meta_window
        },
        top_fraction   = base_hp.pbt_top_fraction,
        checkpoint_dir = "pbt_checkpoints",
        seed           = SEED         # <— aquí
    )


    # ─── 7) Ejecutar PBT ───
    for gen in range(generations):
        logging.info(f"=== Generación {gen} ===")
        rewards = pbt.step(episodes_per_gen, generation=gen)

    # ─── 8) Evaluar final y guardar mejores parámetros y modelos ───
    logging.info("🏁 Evaluando agentes finales…")
    final_rewards = [t.train_online(episodes_per_gen) for t in pbt.trainers]
    best_idx = int(np.argmax(final_rewards))
    best_trainer = pbt.trainers[best_idx]
    best_hp = best_trainer.hp

    # Guardar hiperparámetros
    with open("best_hyperparams.json", "w") as f:
        json.dump(best_hp.__dict__, f, indent=2)
    logging.info("✅ Mejores hiperparámetros guardados en best_hyperparams.json")

    # Guardar modelos DQN y PPO
    best_trainer.dqn.save("wplay/models/dqn.h5")
    best_trainer.ppo.save("wplay/models/ppo.h5")
    logging.info("✅ Pesos DQN y PPO guardados en wplay/models/")

    # Guardar MetaStrategySelector (modelo + estado)
    selector.save_model("wplay/models/meta_selector")
    logging.info("✅ MetaStrategySelector guardado en wplay/models/meta_selector")


if __name__ == '__main__':
    main()
