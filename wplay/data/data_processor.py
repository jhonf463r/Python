# wplay/data/data_processor.py

import time
from typing import Tuple

class DataProcessor:
    """
    Procesa pares de ángulos y tiempos de captura para calcular
    velocidad angular y validar saltos máximos.
    """

    def __init__(self, max_angle_jump: float = 80.0, max_velocity: float = 500.0):
        self.max_angle_jump = max_angle_jump
        self.max_velocity = max_velocity

    def calcular_velocidad_angular(
        self,
        angle1: float,
        angle2: float,
        t1: float,
        t2: float
    ) -> float:
        """
        Calcula la velocidad angular en grados/segundo entre dos ángulos
        y dos instantes de tiempo.

        :param angle1: Ángulo en el instante t1 (grados).
        :param angle2: Ángulo en el instante t2 (grados).
        :param t1: Tiempo inicial (segundos desde epoch o similar).
        :param t2: Tiempo final.
        :return: Velocidad angular absoluta (grados/segundo).
        """
        delta_angle = angle2 - angle1
        delta_time = t2 - t1 if t2 > t1 else 0.0
        if delta_time <= 0:
            return 0.0
        return abs(delta_angle) / delta_time

    def validar_salto_angulo(self, angle1: float, angle2: float) -> bool:
        """
        Comprueba que la diferencia absoluta de ángulos no exceda
        el salto máximo permitido.

        :return: True si abs(angle2 - angle1) ≤ max_angle_jump.
        """
        return abs(angle2 - angle1) <= self.max_angle_jump

    def validar_velocidad(self, velocity: float) -> bool:
        """
        Comprueba que la velocidad angular no exceda el máximo permitido.

        :return: True si velocity ≤ max_velocity.
        """
        return velocity <= self.max_velocity

    def procesar_par(
        self,
        angle1: float,
        angle2: float,
        t1: float,
        t2: float
    ) -> Tuple[float, bool, bool]:
        """
        Calcula velocidad y valida ambos criterios:
         - salto de ángulo
         - límite de velocidad

        :return: (velocity, salto_ok, velocidad_ok)
        """
        vel = self.calcular_velocidad_angular(angle1, angle2, t1, t2)
        salto_ok = self.validar_salto_angulo(angle1, angle2)
        vel_ok = self.validar_velocidad(vel)
        return vel, salto_ok, vel_ok
