# Archivo: wplay/strategy/fibonacci.py

from typing import List
from .base import BettingStrategy

class FibonacciStrategy(BettingStrategy):
    """
    Estrategia Fibonacci:
      - Al perder, avanza un paso en la serie.
      - Al ganar, retrocede un paso (mínimo 0).
      - Si supera el tope (`max_step`), mantiene en el tope y puede resetearse si conviene.
    """

    def __init__(self, max_step: int = 10):
        """
        :param max_step: número máximo de pasos en la serie de Fibonacci.
                         También define la longitud de la serie precomputada.
        """
        super().__init__()  # Inicialización de la clase base, si la hubiera
        self.max_step = max_step

        # Pre-genera la secuencia de Fibonacci hasta max_step
        self.sequence: List[int] = [1, 1]
        for i in range(2, max_step + 1):
            self.sequence.append(self.sequence[-1] + self.sequence[-2])

        # Índice actual en la serie
        self.index: int = 0

    def next_bet(self, last_win: bool) -> int:
        """
        Calcula el próximo valor de apuesta según la regla de Fibonacci:
          - Si se ganó la apuesta anterior, retroceder un paso (sin bajar de 0).
          - Si se perdió, avanzar un paso (hasta max_step).
        :param last_win: True si la apuesta anterior fue ganadora.
        :return: valor de la siguiente apuesta (bounded by sequence[max_step]).
        """
        if last_win:
            # Retroceder un paso pero no por debajo de 0
            self.index = max(0, self.index - 1)
        else:
            # Avanzar un paso pero no pasar de max_step
            self.index = min(self.index + 1, self.max_step)

        # Devolver la cuota correspondiente en la serie
        return self.sequence[self.index]

    def reset(self) -> None:
        """
        Resetea la estrategia al primer término de la serie.
        Útil tras una racha de victorias o cuando quieras reiniciar manualmente.
        """
        self.index = 0
