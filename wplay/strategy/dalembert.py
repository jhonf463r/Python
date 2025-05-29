# Archivo: wplay/strategy/dalembert.py

from .base import BettingStrategy

class DalembertStrategy(BettingStrategy):
    """
    Estrategia D'Alembert:
      - Aumenta 1 ficha tras perder.
      - Disminuye 1 ficha tras ganar, sin bajar de 1.
      - Si supera el tope (`max_step`), resetea a 1.
    """

    def __init__(self, max_step: int = 8):
        """
        :param max_step: número máximo de fichas a apostar antes de resetear.
        """
        super().__init__()  # Inicialización de la clase base, si existe
        self.max_step = max_step
        self.current = 1

    def next_bet(self, last_win: bool) -> int:
        """
        Devuelve el siguiente valor de apuesta según D'Alembert.
        :param last_win: True si la apuesta anterior fue ganadora.
        :return: valor de la siguiente apuesta.
        """
        if last_win:
            # Retractarse un paso pero no menos que 1
            self.current = max(1, self.current - 1)
        else:
            # Avanzar un paso
            self.current += 1

        # Si supera el máximo, reiniciar
        if self.current > self.max_step:
            self.current = 1

        return self.current

    def reset(self) -> None:
        """
        Resetea la apuesta al valor mínimo (1 ficha).
        """
        self.current = 1
