# pipeline/evaluation.py
import os
import glob
from env.EnvManager import EnvManager
from strategy.StrategyManagerDL import StrategyManagerDL
from utils.Logger import Logger

class EvaluationManager:
    """
    Ejecuta un agente en modo evaluación sobre uno o varios checkpoints,
    calcula métricas y exporta reportes o CSVs.
    """
    def __init__(self, config):
        self.config = config
        self.logger = Logger(config.log_dir)
        # Crear entorno y estrategia
        self.env = EnvManager(config.env).create_env()
        self.strategy = StrategyManagerDL(config.strategy)

    def load_checkpoint(self, ckpt_path: str):
        """Carga los pesos del agente desde un checkpoint."""
        self.strategy.agent.load(ckpt_path)
        self.logger.info(f"Checkpoint cargado: {ckpt_path}")

    def run_episode(self) -> float:
        """Ejecuta un episodio en modo evaluation, devuelve la recompensa total."""
        obs = self.env.reset()
        total_reward = 0.0
        done = False
        while not done:
            action = self.strategy.agent.select_action(obs, eval_mode=True)
            obs, reward, done, _ = self.env.step(action)
            total_reward += reward
        return total_reward

    def evaluate(self, ckpt_paths=None) -> dict:
        """
        Para cada checkpoint en la lista, ejecuta N episodios y devuelve métricas.
        Si no se proveen rutas, busca en config.checkpoint_dir.
        """
        if ckpt_paths is None:
            pattern = os.path.join(self.config.checkpoint_dir, "checkpoint_*.pth")
            ckpt_paths = sorted(glob.glob(pattern))

        results = {}
        for ckpt in ckpt_paths:
            self.load_checkpoint(ckpt)
            rewards = []
            for _ in range(self.config.eval_episodes):
                rewards.append(self.run_episode())
            avg = sum(rewards) / len(rewards)
            results[os.path.basename(ckpt)] = {
                "avg_reward": avg,
                "min_reward": min(rewards),
                "max_reward": max(rewards),
                # Se pueden añadir métricas adicionales aquí
            }
            self.logger.info(f"Evaluado {ckpt}: {results[os.path.basename(ckpt)]}")
        return results

# Ejemplo de uso en evaluate.py:
# from config import load_config
# from pipeline.evaluation import EvaluationManager
#
# if __name__ == '__main__':
#     cfg = load_config('config.yaml')
#     evaluator = EvaluationManager(cfg)
#     report = evaluator.evaluate()
#     print(report)
