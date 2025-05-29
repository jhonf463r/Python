# wplay/strategy/manager.py

import random
import sqlite3
from typing import Dict

class StrategyManager:
    """
    Implementa un gestor de estrategias con Q-learning o ε-greedy
    y martingalas (D'Alembert, Fibonacci).
    """
    def __init__(self, db_path: str, epsilon: float = 0.1,
                 max_dalembert: int = 5, max_fibonacci: int = 7):
        self.db_path = db_path
        self.epsilon = epsilon
        self.max_dalembert = max_dalembert
        self.max_fibonacci = max_fibonacci

        self.q_values = self._load_q_values()

        # Estados de progresión para estrategias
        self.dalembert_step = 1
        self.fibonacci_seq = [1, 1]
        self.fibo_index = 0

    def _load_q_values(self) -> Dict[str, float]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    name TEXT PRIMARY KEY,
                    q REAL
                )
            """)
            conn.commit()

            # Asegurar estrategias por defecto
            defaults = self._default_strategies()
            for strat in defaults:
                cur.execute("INSERT OR IGNORE INTO strategies(name, q) VALUES (?, ?)", (strat, 0.0))
            conn.commit()

            cur.execute("SELECT name, q FROM strategies")
            rows = cur.fetchall()
            return {name: q for name, q in rows}
        finally:
            conn.close()

    def _save_q_value(self, strategy: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO strategies(name, q) VALUES (?, ?)",
            (strategy, self.q_values[strategy])
        )
        conn.commit()
        conn.close()

    def _default_strategies(self) -> Dict[str, float]:
        return {"dalembert": 0.0, "fibonacci": 0.0}

    def elegir_estrategia(self) -> str:
        """Alias en español para compatibilidad con betting_engine."""
        return self.choose()

    def choose(self) -> str:
        """
        Selecciona una estrategia usando ε-greedy según q_values.
        """
        if not self.q_values or random.random() < self.epsilon:
            estr = random.choice(list(self._default_strategies().keys()))
            print(f"[ESTRATEGIA][DEBUG] exploración → '{estr}'")
            return estr
        estr = max(self.q_values, key=self.q_values.get)
        print(f"[ESTRATEGIA][DEBUG] explotación → '{estr}' (Q={self.q_values[estr]:.3f})")
        return estr

    def bet_amount(self, strategy: str, won: bool) -> int:
        """
        Devuelve cuántas fichas apostar según la estrategia seleccionada.
        """
        if strategy == "dalembert":
            if won:
                self.dalembert_step = max(1, self.dalembert_step - 1)
            else:
                self.dalembert_step += 1
            return min(self.dalembert_step, self.max_dalembert)

        elif strategy == "fibonacci":
            if won:
                self.fibo_index = max(0, self.fibo_index - 2)
            else:
                self.fibo_index += 1
                if self.fibo_index >= len(self.fibonacci_seq):
                    next_val = self.fibonacci_seq[-1] + self.fibonacci_seq[-2]
                    self.fibonacci_seq.append(next_val)

            return min(self.fibonacci_seq[self.fibo_index], self.max_fibonacci)

        return 1  # Fallback seguro

    def get_apuesta(self, strategy: str, won: bool) -> int:
        """Alias requerido por BettingEngine para bet_amount()."""
        return self.bet_amount(strategy, won)


    def update_q(self, strategy: str, reward: float):
        """
        Actualiza el Q-value de la estrategia con la recompensa dada.
        """
        if strategy not in self.q_values:
            self.q_values[strategy] = 0.0
        alpha = 0.5  # tasa de aprendizaje
        old = self.q_values[strategy]
        self.q_values[strategy] = (1 - alpha) * old + alpha * reward
        print(f"[ESTRATEGIA][DEBUG] Q('{strategy}') {old:.3f} → {self.q_values[strategy]:.3f} (reward={reward})")
        # persiste en BD
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO strategies(name,q) VALUES (?,?)",
            (strategy, self.q_values[strategy])
        )
        conn.commit()
        conn.close()