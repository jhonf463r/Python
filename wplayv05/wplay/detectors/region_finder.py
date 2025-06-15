import time
import cv2
import numpy as np
import pyautogui
from typing import List, Dict, Tuple

# Importa aquí tus detectores concretos; cada uno debe exponer:
#   - un atributo `name` (string único)
#   - un método `match(template_img: np.ndarray) -> Tuple[int,int,int,int] | None`
from wplay.detectors.giro_detector import GiroDetector
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.detectors.numero_detector import NumeroDetector
# … cualquier otro detector que uses en tu proyecto


class RegionFinder:
    """
    Centraliza todas las detecciones por plantilla (matchTemplate).
    Cada detector encapsula:
      - la imagen de la plantilla,
      - la lógica de umbral,
      - y devuelve coordenadas (x, y, w, h) de la primera coincidencia válida.

    RegionFinder toma una lista de detectores y, en cada llamada a `find_all()`,
    captura la pantalla completa, la convierte a escala de grises y ejecuta
    cada detector contra ese screenshot.
    """

    def __init__(self, detectors: List):
        """
        :param detectors: lista de objetos detector, cada uno con:
                          - `name: str`
                          - `match(screen_gray: np.ndarray) -> Tuple[int,int,int,int] | None`
        """
        self.detectors = detectors

    def find_all(self) -> Dict[str, Tuple[int, int, int, int]]:
        """
        Toma un screenshot, lo pasa a gris y ejecuta cada detector.
        Devuelve {detector.name: (x,y,w,h)} sólo si match ≥ threshold.
        """
        # 1) Captura y convert a BGR→Gray
        screen = np.array(pyautogui.screenshot())
        screen_bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        regions: Dict[str, Tuple[int,int,int,int]] = {}
        for detector in self.detectors:
            try:
                m = detector.match(screen_gray)
            except Exception as e:
                print(f"[WARN] Detector {detector.name} falló: {e}")
                continue
            if m:
                x, y, w, h = m
                regions[detector.name] = (x, y, w, h)
        return regions


# -----------------------
# Ejemplo de inicialización en tu flujo principal:
#
# detectors = [
#     GiroDetector(template_path="templates/giro.png", threshold=0.8),
#     RuletaDetector(template_path="templates/ruleta_coords.png", threshold=0.9),
#     NumeroDetector(template_path="templates/numero_*.png", threshold=0.85),
#     # ...otros detectores que uses...
# ]
#
# rf = RegionFinder(detectors)
#
# # En cualquier parte:
# regs = rf.find_all()
# if "giro" in regs:
#     # procesa el giro…
# -----------------------
