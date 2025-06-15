# wplay/detectors/numero_detector.py

import os
import cv2
import glob
import numpy as np
from wplay.config import TEMPLATES_DIR

class NumeroDetector:
    """
    Detector del número final de la ruleta basado en plantillas múltiples.

    Firma compatible con GiroDetector y RuletaDetector:
      - pattern: ruta glob a plantillas ('templates/numero_*.png')
      - threshold: umbral opcional para futura similitud

    Parámetros:
      pattern (str): glob o ruta directa a plantillas (por defecto 'templates/numero_*.png')
      threshold (float): umbral de similitud (no usado en la lógica actual)
      debug_folder (str): carpeta donde guardar capturas de debug
    """
    def __init__(
        self,
        pattern: str = os.path.join(TEMPLATES_DIR, "numero_*.png"),
        threshold: float = 0.9,
        debug_folder: str = os.path.join("debug", "numero")
    ):
        # Compatibilidad de firma
        self.pattern = pattern
        self.threshold = threshold  # reservado para futuras mejoras
        self.debug_folder = debug_folder
        os.makedirs(self.debug_folder, exist_ok=True)

        # Resolver glob o ruta directa
        if any(c in pattern for c in "*?[]"):
            self.template_paths = glob.glob(pattern)
        else:
            self.template_paths = [pattern]

        if not self.template_paths:
            raise FileNotFoundError(f"No se encontraron plantillas con patrón: {pattern}")

        # Pre-carga de plantillas en escala de grises
        self.templates = []
        for tpl_path in self.template_paths:
            img = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"No se pudo leer la plantilla: {tpl_path}")
            self.templates.append(img)

    def guardar_debug(self, imagen: np.ndarray, nombre: str):
        """
        Guarda una imagen de debug en la carpeta correspondiente.
        """
        ruta = os.path.join(self.debug_folder, nombre)
        cv2.imwrite(ruta, imagen)

    def detectar_numero(self, frame_gray: np.ndarray):
        """
        Hace matchTemplate con todas las plantillas de número y devuelve
        la mejor coincidencia.

        Args:
            frame_gray (np.ndarray): captura en escala de grises de la región del número.

        Returns:
            Tuple (max_val, max_loc, template_size, tpl_path) si supera el threshold,
            o None en caso contrario.
        """
        best_val = 0.0
        best_loc = None
        best_size = None
        best_path = None

        for tpl, path in zip(self.templates, self.template_paths):
            res = cv2.matchTemplate(frame_gray, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_size = (tpl.shape[1], tpl.shape[0])  # (w, h)
                best_path = path

        if best_val >= self.threshold:
            # debug: guardar la ROI detectada
            self.guardar_debug(frame_gray, "numero_region.png")
            return best_val, best_loc, best_size, best_path

        return None
