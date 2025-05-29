import random
import numpy as np
from typing import List, Tuple, Dict

# Número máximo de jugadores usado para normalización en el vector de estado
MAX_JUGADORES = 20

class StatsHelper:
    """
    Proporciona métodos para seleccionar la categoría de apuesta
    basada en ausencias históricas y un poco de exploración (epsilon-greedy),
    y construcción de vector de estado para RL.
    """
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(self, historial: List[int], window_size: int = 50, epsilon: float = 0.1):
        """
        :param historial: lista de los últimos números salidos
        :param window_size: cuántos últimos resultados considerar para ausencias y para el vector
        :param epsilon: probabilidad de exploración (elegir categoría aleatoria)
        """
        self.historial = historial
        self.window_size = window_size
        self.epsilon = epsilon

    def update_historial(self, numero: int) -> None:
        """
        Agrega el número recién salido al historial y recorta al window_size.
        """
        self.historial.append(numero)
        if len(self.historial) > self.window_size:
            del self.historial[0]

    def _compute_absences(self) -> Dict[str, int]:
        """
        Cuenta ausencias consecutivas de cada categoría en el historial
        (la más reciente al final de la lista).
        """
        absences = {c: 0 for c in self.CATEGORIES}
        for num in reversed(self.historial[-self.window_size:]):
            belongs = {
                "rojo":   num in {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36},
                "negro":  num in {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35},
                "par":    (num != 0 and num % 2 == 0),
                "impar":  (num % 2 == 1),
                "1-18":   (1 <= num <= 18),
                "19-36":  (19 <= num <= 36),
            }
            for cat, was in belongs.items():
                if not was:
                    absences[cat] += 1
                else:
                    absences[cat] = 0
            if all(v == 0 for v in absences.values()):
                break
        return absences

    def select_categoria(self) -> Tuple[str, float]:
        """
        Selecciona la categoría de apuesta:
         - Con probabilidad epsilon explora al azar.
         - Si no, elige la categoría con mayor ausencia histórica.
        Devuelve (categoria, score) donde score = ausencias / window_size.
        """
        if random.random() < self.epsilon:
            cat = random.choice(self.CATEGORIES)
            return cat, 0.0

        absences = self._compute_absences()
        max_abs = max(absences.values()) or 1
        categoria, abs_count = max(absences.items(), key=lambda kv: kv[1])
        score = abs_count / self.window_size
        return categoria, score

    def build_state_vector(self, registro: Dict, recent_spins: List[int]) -> np.ndarray:
        """
        Construye un vector de estado para RL:
          - ventana de últimos números (normalizados 0..1)
          - velocidad (normalizada)
          - dirección (binaria)
          - jugadores presentes (normalizado)
        """
        # Asegurar longitud de ventana
        hist = recent_spins[-self.window_size:]
        if len(hist) < self.window_size:
            hist = [0] * (self.window_size - len(hist)) + hist
        # Normalizar posiciones
        state = [num / 36.0 for num in hist]
        # Características actuales del registro
        state.append(registro.get('velocity', 0.0) / 100.0)
        state.append(1 if registro.get('direction', '') == 'horario' else 0)
        state.append(registro.get('jugadores_presentes', 0) / MAX_JUGADORES)
        return np.array(state)
