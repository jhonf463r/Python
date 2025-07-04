# worker.py
from wplay.training.rl_trainer import RLTrainer
from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent

def worker_train(config):
    # 1) Reconstruir el RLTrainer con sus parámetros básicos
    trainer = RLTrainer(
        rl_csv_path      = config["rl_csv_path"],
        strategy_manager = StrategyManagerDL,   # o usar una factory si necesitas pasar kwargs
        dqn_agent_cls    = DQNAgent,
        ppo_agent_cls    = PPOAgent,
        dqn_kwargs       = config["dqn_kwargs"],
        ppo_kwargs       = config["ppo_kwargs"],
        buffer_size      = config["buffer_size"],
        batch_size       = config["batch_size"],
        train_interval   = config["train_interval"],
        gamma            = config["gamma"],
        save_dir         = config["save_dir"]
    )
    # 2) Ejecutar el entrenamiento online
    avg = trainer.train_online(config["episodes_per_trainer"])
    return avg
