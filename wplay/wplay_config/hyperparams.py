# wplay/wplay_config/hyperparams.py

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class HyperParams:
    # — DQN —
    dqn_lr: float = 1e-3
    dqn_lr_decay_rate: float = 0.5
    dqn_buffer_capacity: int = 100000
    dqn_gamma: float = 0.99
    dqn_tau: float = 0.005
    dqn_eps_start: float = 1.0
    dqn_eps_mid: float   = 0.2
    dqn_eps_final: float = 0.01
    dqn_phase1: int      = 10000
    dqn_phase2: int      = 50000
    dqn_hidden: List[int] = field(default_factory=lambda: [64, 64])

    # — PPO —
    ppo_lr_actor: float = 1e-4
    ppo_lr_critic: float = 3e-4
    ppo_use_lr_schedule: bool = False
    ppo_lr_decay_steps: int = 10000
    ppo_lr_decay_rate: float = 0.9
    ppo_gamma: float = 0.99
    ppo_lam: float = 0.95
    ppo_eps_clip: float = 0.2
    ppo_K_epochs: int = 4
    ppo_entropy_coef: float = 0.01
    ppo_value_coef: float = 0.5
    ppo_actor_hidden: List[int] = field(default_factory=lambda: [64, 64])
    ppo_critic_hidden: List[int] = field(default_factory=lambda: [64, 64])

    # — MetaStrategySelector —
    meta_model_path: str = "wplay/models/meta_strategy_selector.keras"
    meta_strategies: List[str] = field(default_factory=lambda: ["dqn", "ppo", "skip"])
    meta_window: int = 100
    meta_lr: float = 1e-3
    meta_epochs: int = 1
    meta_batch_size: Optional[int] = None  # si None, usa meta_window
    meta_ucb_c: float = 1.0
    meta_use_ts: bool = True
    L_thresh: float = 0.5
    H_thresh: float = 0.7
    ENT_thresh: float = 1.0

    # — Hypernetwork —
    meta_stats_dim: int = 4
    hyper_num_coeffs: int = 4
    hyper_hidden_units: List[int] = field(default_factory=lambda: [32, 32])
    hyper_model_path: Optional[str] = None

    # — EnvModel —
    env_shuffle: bool = False
    env_seed: Optional[int] = None

    # — Paths y modelos —
    clean_csv_path: str = "wplay/data/clean_records.csv"
    rl_input_path: str    = "wplay/data/rl_input.csv"
    lstm_input_path: str  = "wplay/data/lstm_input.csv"
    transformer_model_path: str = "wplay/models/transformer.keras"

    # → Nuevo atributo para el pipeline offline
    model_base_path: str = "wplay/models"

    # — RLTrainer parameters (aliases para la clase RLTrainer) —
    rl_buffer_size: int = 20000
    rl_batch_size: int   = 128
    rl_train_interval: int = 50
    rl_gamma: float        = 0.99
    
    # Aliases que RLTrainer busca
    buffer_size: int    = field(init=False)
    batch_size: int     = field(init=False)
    train_interval: int = field(init=False)
    gamma: float        = field(init=False)

    # — RLTrainer paths —
    rl_save_dir: str = "wplay/models/rl"
    feature_list_filename: str = "feature_list.json"

    # — PBTManager —
    pbt_top_fraction: float = 0.5

    # — BettingEngine u otros —
    cooldown: float = 1.0
    wager_value: int = 10
    max_drawdown: float = 0.2
    gain_reset_threshold: float = 0.05

    def __post_init__(self):
        # Asegurar batch_size de meta si no se especificó
        if self.meta_batch_size is None:
            self.meta_batch_size = self.meta_window

        # Inicializar los aliases de RLTrainer
        self.buffer_size    = self.rl_buffer_size
        self.batch_size     = self.rl_batch_size
        self.train_interval = self.rl_train_interval
        self.gamma          = self.rl_gamma
