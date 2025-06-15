# pipeline/visualization.py
"""
VisualizationManager: clase para graficar métricas de entrenamiento y evaluación.
Genera y guarda gráficos de recompensas, drawdown y curvas de aprendizaje.
"""
import os
import matplotlib.pyplot as plt

class VisualizationManager:
    """
    Gestiona la generación de gráficos para las métricas de un experimento.
    """
    def __init__(self, config):
        """
        Inicializa la ruta de salida para los gráficos.

        Args:
            config: objeto de configuración que debe contener:
                - output_dir: directorio donde guardar las figuras.
        """
        self.output_dir = config.output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def plot_rewards(self, rewards: list, title: str = 'Recompensa por episodio', filename: str = 'rewards.png'):
        """
        Grafica la recompensa obtenida en cada episodio.

        Args:
            rewards (list of float): recompensas totales por episodio.
            title (str): título del gráfico.
            filename (str): nombre del archivo de salida.
        """
        plt.figure()
        plt.plot(rewards)
        plt.title(title)
        plt.xlabel('Episodio')
        plt.ylabel('Recompensa')
        output_path = os.path.join(self.output_dir, filename)
        plt.savefig(output_path)
        plt.close()

    def plot_drawdown(self, drawdowns: list, title: str = 'Drawdown acumulado', filename: str = 'drawdown.png'):
        """
        Grafica el drawdown acumulado a lo largo de los episodios.

        Args:
            drawdowns (list of float): valores de drawdown por episodio.
            title (str): título del gráfico.
            filename (str): nombre del archivo de salida.
        """
        plt.figure()
        plt.plot(drawdowns)
        plt.title(title)
        plt.xlabel('Episodio')
        plt.ylabel('Drawdown')
        output_path = os.path.join(self.output_dir, filename)
        plt.savefig(output_path)
        plt.close()

    def plot_learning_curve(self, metrics: dict, key: str = 'avg_reward',
                            title: str = 'Curva de aprendizaje', filename: str = 'learning_curve.png'):
        """
        Grafica una métrica específica a lo largo de los checkpoints o episodios.

        Args:
            metrics (dict): mapa de identificador -> valor de métrica. Por ejemplo:
                {'checkpoint_10.pth': 5.2, 'checkpoint_50.pth': 7.8, ...}
            key (str): nombre de la métrica (para etiquetas y título).
            title (str): título del gráfico.
            filename (str): nombre del archivo de salida.
        """
        # Extraer ejes: ordenamos por clave (p.ej. nombre de checkpoint numérico)
        xs = list(metrics.keys())
        ys = [metrics[x] for x in xs]

        plt.figure()
        plt.plot(ys)
        plt.title(title)
        plt.xlabel('Paso / Checkpoint')
        plt.ylabel(key)
        plt.xticks(range(len(xs)), xs, rotation=45, ha='right')
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, filename)
        plt.savefig(output_path)
        plt.close()

    def plot_all(self, history: dict):
        """
        Grafica recompensas, drawdown y curva de aprendizaje usando un histórico completo.

        Args:
            history (dict): debe contener las listas bajo claves:
                - 'rewards': list of float
                - 'drawdowns': list of float
                - 'learning_curve': dict identifier->metric
        """
        if 'rewards' in history:
            self.plot_rewards(history['rewards'])
        if 'drawdowns' in history:
            self.plot_drawdown(history['drawdowns'])
        if 'learning_curve' in history:
            self.plot_learning_curve(history['learning_curve'])
