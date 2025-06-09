# Archivo: wplay/strategy/fibonacci_adaptive.py

class FibonacciAdaptive:
    """
    Estrategia de apuesta basada en Fibonacci por categoría.
    Se adapta según los aciertos y sigue la predicción LSTM como guía.
    """

    def __init__(self, categorias, max_valor=13):
        self.categorias = categorias
        self.max_valor = max_valor
        self.secuencias = {c: [1, 2] for c in categorias}
        self.indices = {c: 0 for c in categorias}
        self.ultimos_resultados = {c: [] for c in categorias}

    def _next_valor(self, cat: str) -> int:
        idx = self.indices[cat]
        sec = self.secuencias[cat]
        if idx >= len(sec):
            next_val = sec[-1] + sec[-2]
            if next_val > self.max_valor:
                self.indices[cat] = 0
                return sec[0]
            sec.append(next_val)
        return sec[self.indices[cat]]

    def registrar_resultado(self, categoria: str, win: bool):
        """
        Informa si la apuesta en 'categoria' fue ganadora o no.
        Reinicia o avanza la secuencia según resultado.
        """
        if categoria not in self.indices:
            return
        if win or self._next_valor(categoria) >= self.max_valor:
            self.indices[categoria] = 0
        else:
            self.indices[categoria] += 1

    def decidir_apuesta(self, prediccion_lstm: str = None) -> tuple:
        """
        Elige la categoría y valor a apostar.
        Si hay predicción LSTM, la prioriza.
        """
        if prediccion_lstm in self.categorias:
            cat = prediccion_lstm
        else:
            # fallback: elige la que tenga mayor valor Fibonacci actual
            cat = max(self.categorias, key=lambda c: self._next_valor(c))

        return cat, self._next_valor(cat)
