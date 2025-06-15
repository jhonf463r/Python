import time
from typing import Dict, Tuple

from wplay.detectors.region_finder import RegionFinder
from wplay.detectors.data_collector import DataCollector


class SpinController:
    """
    Gestiona la detección del giro de la ruleta **solo** tras una apuesta válida.
    - Espera al flanco de subida de la plantilla "giro".
    - Extrae la ROI de la "ruleta" para pasarla al DataCollector.
    - Resetea y desactiva el modo de espera cuando el spin ha terminado.
    """

    def __init__(
        self,
        region_finder: RegionFinder,
        data_collector: DataCollector,
    ):
        """
        :param region_finder: instancia de RegionFinder para detectar plantillas.
        :param data_collector: instancia de DataCollector que acumula velocidades/números.
        """
        self.rf = region_finder
        self.dc = data_collector

        # Flag que indica si estamos esperando el próximo "giro"
        self._awaiting_spin = False
        # Estado anterior de la plantilla "giro" (para detectar flancos)
        self._prev_has_giro = False
    def notify_bet_placed(self) -> None:
        """
        Llamar justo tras place_bet() → habilita escucha de 'giro' y resetea buffers.
        """
        self._awaiting_spin = True
        self._prev_has_giro = False
        self.dc.reset_spin_buffer()
        self._spin_start_time = time.time()

    def update(self, timeout: float = 10.0) -> None:
        """
        Llamar en cada iteración. Si estamos esperando giro:
         1) detecta flanco de 'giro' → dc.accumulate_spin()
         2) desactiva cuando dc.spin_complete()
         3) cancela tras timeout
        """
        if not self._awaiting_spin:
            return
        if time.time() - self._spin_start_time > timeout:
            print("⚠ Timeout esperando giro.")
            self._awaiting_spin = False
            return

        regs = self.rf.find_all()
        has = "giro" in regs
        if has and not self._prev_has_giro:
            print("[DEBUG] Giro detectado.")
            roi = regs.get("ruleta")
            if roi:
                self.dc.accumulate_spin({"ruleta": roi})
            else:
                print("⚠ No hay ROI 'ruleta'.")

        self._prev_has_giro = has

        if self.dc.spin_complete():
            stats = self.dc.get_spin_stats()
            print(f"[DEBUG] Spin complete: {stats}")
            self._awaiting_spin = False
