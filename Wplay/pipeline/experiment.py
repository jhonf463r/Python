import os
from auth.LoginAutomation import LoginAutomation
from capture.ChromeHandler import ChromeHandler
from data.DataCollector import DataCollector
from data.DataCleaner import DataCleaner
from data.FeatureEngineerRL import FeatureEngineerRL
from env.EnvManager import EnvManager
from strategy.StrategyManagerDL import StrategyManagerDL
from trainer.RLTrainer import RLTrainer
from utils.Logger import Logger

class ExperimentPipeline:
    """
    Orquesta el flujo completo de captura, preprocesamiento, entrenamiento y evaluación.
    """
    def __init__(self, config):
        self.config = config
        self._setup_dirs()
        self.logger = Logger(config.log_dir)
        # Inicializar componentes
        self.auth = LoginAutomation(config.auth)
        self.capture = ChromeHandler(config.chrome)
        self.data_collector = DataCollector(config.data)
        self.cleaner = DataCleaner()
        self.feature_engineer = FeatureEngineerRL(config.feature)
        self.env_manager = EnvManager(config.env)
        self.strategy_manager = StrategyManagerDL(config.strategy)
        self.trainer = RLTrainer(config.trainer)

    def _setup_dirs(self):
        os.makedirs(self.config.log_dir, exist_ok=True)
        os.makedirs(self.config.checkpoint_dir, exist_ok=True)

    def run_capture(self):
        """Ejecuta la autenticación y recolección de datos"""
        self.auth.login()
        raw_data = self.capture.collect()
        self.data_collector.save_raw(raw_data)
        self.logger.info("Datos capturados y guardados.")
        return raw_data

    def preprocess(self, raw_data):
        """Limpia y genera features para RL"""
        cleaned = self.cleaner.clean(raw_data)
        states, actions, rewards, next_states = self.feature_engineer.generate_transitions(cleaned)
        self.logger.info("Preprocesamiento completado.")
        return states, actions, rewards, next_states

    def build_env(self):
        """Configura y retorna el entorno de entrenamiento"""
        env = self.env_manager.create_env()
        self.logger.info("Entorno preparado.")
        return env

    def train(self):
        """Ejecución completa del loop de entrenamiento"""
        env = self.build_env()
        self.trainer.setup(env, self.strategy_manager.agent)

        for episode in range(self.config.max_episodes):
            obs = env.reset()
            done = False
            while not done:
                action = self.strategy_manager.agent.select_action(obs)
                nxt_obs, reward, done, info = env.step(action)
                self.strategy_manager.store_transition(obs, action, reward, nxt_obs, done)
                self.trainer.step()
                obs = nxt_obs

            # Evaluación periódica
            if episode % self.config.eval_interval == 0:
                metrics = self.evaluate(env)
                self.logger.info(f"Episode {episode}: {metrics}")
                self._save_checkpoint(episode)

    def evaluate(self, env):
        """Evalúa el agente en modo evaluación sobre episodios de validación"""
        total_reward = 0
        for _ in range(self.config.eval_episodes):
            obs = env.reset()
            done = False
            while not done:
                action = self.strategy_manager.agent.select_action(obs, eval_mode=True)
                obs, reward, done, _ = env.step(action)
                total_reward += reward
        avg_reward = total_reward / self.config.eval_episodes
        return {"avg_reward": avg_reward}

    def _save_checkpoint(self, episode):
        """Guarda el estado de los agentes y trainer"""
        ckpt_path = os.path.join(self.config.checkpoint_dir, f"checkpoint_{episode}.pth")
        self.trainer.save(ckpt_path)
        self.strategy_manager.agent.save(ckpt_path)
        self.logger.info(f"Checkpoint guardado en {ckpt_path}")

    def run_full(self):
        """Pipeline completo: captura, preprocesamiento, entrenamiento"""
        raw = self.run_capture()
        self.preprocess(raw)
        self.train()

# Ejemplo de uso:
# if __name__ == '__main__':
#     from config import load_config
#     cfg = load_config('config.yaml')
#     pipeline = ExperimentPipeline(cfg)
#     pipeline.run_full()
