import time
from typing import Callable, Dict, Tuple

from wplay.utils.helpers import human_click


class BetController:
    """
    Encapsula la lógica de colocar una apuesta en la mesa de ruleta:
      - Gestiona cooldown entre apuestas para evitar clicks dobles.
      - Divide el monto total en fichas (denominaciones de 500 y 5000).
      - Hace click en el centro de la región correspondiente a la categoría de apuesta.
    """

    def __init__(
        self,
        table_map: Dict[str, Tuple[int, int, int, int]],
        click_fn: Callable[[int, int], None],
        cooldown: float = 1.0
    ):
        """
        :param table_map: mapeo categoría → (x, y, w, h) de la casilla en la mesa
        :param click_fn: función para hacer click en pantalla (p.ej. human_click)
        :param cooldown: tiempo mínimo (s) entre apuestas sucesivas
        """
        self.table_map = table_map
        self.click_fn = click_fn
        self.cooldown = cooldown
        self._last_bet_time = 0.0

    def can_bet(self) -> bool:
        """
        True si ha pasado cooldown desde la última apuesta.
        """
        return (time.time() - self._last_bet_time) >= self.cooldown

    def place_bet(self, category: str, total_amount: int) -> bool:
        """
        1) Check cooldown.
        2) Divide el monto en fichas de 5000/500.
        3) Hace clicks en el centro de la región.
        4) Actualiza timestamp.
        """
        if not self.can_bet():
            print("⚠ En cooldown de apuesta.")
            return False

        region = self.table_map.get(category)
        if not region:
            print(f"⚠ Categoría desconocida: '{category}'")
            return False

        x, y, w, h = region
        cx, cy = x + w//2, y + h//2
        chip = 5000 if total_amount % 5000 == 0 else 500
        n = total_amount // chip
        print(f"[DEBUG] Apostando {total_amount} en {category}: {n}×{chip}")
        for _ in range(n):
            self.click_fn(cx, cy)
            time.sleep(0.05)

        self._last_bet_time = time.time()
        return True
