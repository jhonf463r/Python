class FibonacciStrategy:
    """
    Estrategia progresiva basada en la secuencia clásica de Fibonacci:
    [1, 1, 2, 3, 5, 8, 13, 21, ...]
    - Si pierdes: avanzas al siguiente número (hasta el tope).
    - Si ganas o alcanzas el tope: reinicias desde el principio.
    """

    def __init__(self):
        # Secuencia clásica de Fibonacci (dos "1" al inicio)
        self.sequence = [1, 1, 2, 3, 5, 8, 13, 21]
        self.index = 0
        self.last_win_fibo = False
        # El paso máximo corresponde al último índice de la secuencia
        self.max_step = len(self.sequence) - 1

    def next_bet(self) -> int:
        """
        Retorna el valor de la apuesta actual según el índice.
        """
        return self.sequence[self.index]

    def update(self, win: bool):
        """
        Actualiza el índice de la secuencia según el resultado:
        - Si gana: reinicia (index = 0) y marca last_win_fibo.
        - Si pierde y no estaba en el tope: avanza (index += 1).
        - Si pierde y estaba en el tope: reinicia también.
        """
        self.last_win_fibo = win
        if win:
            self.reset()
        else:
            if self.index < self.max_step:
                self.index += 1
            else:
                # Si ya estábamos en el tope, reiniciamos igualmente
                self.reset()

    def reset(self):
        """
        Reinicia la estrategia al comienzo de la secuencia.
        """
        self.index = 0
        self.last_win_fibo = False
