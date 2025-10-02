# wplay/strategies/epsilon_greedy.py

import random
from .base import BettingStrategy

class EpsilonGreedyStrategy(BettingStrategy):
    """
    Selector ε‑greedy entre varias estrategias.
    Mantiene Q‑values para aprender qué estrategia da mejor ganancia.
    """

    def __init__(self, strategies: dict[str, BettingStrategy], epsilon: float = 0.1):
        """
        :param strategies: mapeo nombre → instancia de BettingStrategy
        """
        self.strategies = strategies
        self.epsilon = epsilon
        self.q_values = {name: 0.0 for name in strategies}
        self.counts = {name: 0 for name in strategies}
        self.last_choice: str | None = None

    def next_bet(self, last_win: bool) -> int:
        # Elegir estrategia
        if random.random() < self.epsilon:
            choice = random.choice(list(self.strategies))
        else:
            choice = max(self.q_values, key=self.q_values.get)

        # Delegar a la estrategia elegida
        bet = self.strategies[choice].next_bet(last_win)
        self.last_choice = choice
        return bet

    def update(self, reward: float) -> None:
        """
        Tras recibir la recompensa de la última apuesta,
        actualizar Q‑value de la estrategia usada.
        """
        if self.last_choice is None:
            return

        self.counts[self.last_choice] += 1
        alpha = 1.0 / self.counts[self.last_choice]
        q = self.q_values[self.last_choice]
        # Q ← Q + α * (r − Q)
        self.q_values[self.last_choice] = q + alpha * (reward - q)

    def reset(self) -> None:
        for strat in self.strategies.values():
            strat.reset()
        self.last_choice = None
        # opcional: limpiar Q‑values/counters si quieres reiniciar el aprendizaje
