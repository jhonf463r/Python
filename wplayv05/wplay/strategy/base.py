# wplay/strategies/base.py

from abc import ABC, abstractmethod

class BettingStrategy(ABC):
    """
    Interfaz base para estrategias de apuesta.
    Cada estrategia debe implementar cómo decidir la siguiente apuesta
    y cómo actualizar su estado tras el resultado.
    """

    @abstractmethod
    def next_bet(self, last_win: bool) -> int:
        """
        Calcula cuántas fichas apostar en la siguiente ronda.
        
        :param last_win: True si la última apuesta fue ganadora.
        :return: número de fichas a apostar (entero ≥ 1).
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Reinicia el estado interno de la estrategia (por ejemplo, índices,
        contadores, series) para comenzar de cero.
        """
        pass
