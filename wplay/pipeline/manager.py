# pipeline/manager.py
"""
PipelineManager: clase de alto nivel que orquesta todo el flujo desde la configuración,
pasando por capturas, entrenamiento, evaluación, checkpoints y visualización.
"""
from pipeline.config import ConfigManager
from pipeline.experiment import ExperimentPipeline
from pipeline.evaluation import EvaluationManager
from pipeline.checkpoint import CheckpointManager
from pipeline.visualization import VisualizationManager

class PipelineManager:
    """
    Coordina la ejecución completa del experimento:
      1) Carga de config
      2) Captura y preprocess
      3) Entrenamiento
      4) Guardado y limpieza de checkpoints
      5) Evaluación de checkpoints
      6) Visualización de métricas
    """
    def __init__(self, config_path: str):
        """
        Args:
            config_path (str): ruta al YAML de configuración.
        """
        # Cargar y validar configuración global
        self.config = ConfigManager(config_path)

        # Inicializar managers modulares
        self.pipeline = ExperimentPipeline(self.config)
        self.checkpoint_mgr = CheckpointManager(self.config)
        self.evaluator = EvaluationManager(self.config)
        self.visualizer = VisualizationManager(self.config.visualization)

    def run(self):
        """
        Ejecuta el flujo completo:
          - Captura y preprocessing
          - Entrenamiento y checkpointing
          - Evaluación de todos los checkpoints guardados
          - Visualización de métricas
        """
        # 1. Ejecutar pipeline completo (incluye entrenamiento)
        self.pipeline.run_full()

        # 2. Listar checkpoints guardados por el pipeline
        ckpts = self.checkpoint_mgr.list_checkpoints()

        # 3. Evaluar cada checkpoint
        report = self.evaluator.evaluate(ckpts)

        # 4. Generar curvas de aprendizaje a partir de report
        # Extraer avg_reward por checkpoint
        learning_curve = {ckpt: metrics['avg_reward'] for ckpt, metrics in report.items()}
        history = {
            'learning_curve': learning_curve
            # 'rewards' y 'drawdowns' pueden venir del pipeline o trainer si se almacenan
        }
        self.visualizer.plot_learning_curve(learning_curve,
                                            title='Evolución de recompensa promedio',
                                            filename='learning_curve.png')

        print("=== Evaluación de Checkpoints ===")
        for ckpt, metrics in report.items():
            print(f"{ckpt}: avg={metrics['avg_reward']:.2f}, min={metrics['min_reward']:.2f}, max={metrics['max_reward']:.2f}")

        print("Flujo completado. Gráficos y reportes generados en:", self.config.visualization['output_dir'])

# Ejemplo de uso:
# if __name__ == '__main__':
#     manager = PipelineManager('config.yaml')
#     manager.run()
