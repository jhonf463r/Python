# wplay/detectors/ruleta_detector.py

import os
import cv2
import numpy as np
import pyautogui
import time
import math
from collections import deque
from wplay.config import TEMPLATES_DIR
from wplay.data.data_processor import DataProcessor

class RuletaDetector:
    """
    Detector de la rueda de la ruleta basado en color (franja verde) y cálculo de giro.

    Firma compatible con GiroDetector y NumeroDetector:
      - pattern: ruta glob a plantillas (no usada en la lógica actual)
      - threshold: umbral opcional (no usado en la lógica actual)

    Parámetros:
      pattern (str): glob para plantillas, por defecto 'templates/ruleta_*.png'
      threshold (float): umbral de similitud
      delay (float): segundos entre capturas para estimar velocidad
      debug_folder (str): carpeta de debug
      lower_green, upper_green (tuple): rango HSV para la franja verde
      min_area (int): área mínima para el contorno
      max_registros (int): registros máximos en memoria
    """
    def __init__(
        self,
        pattern: str = os.path.join(TEMPLATES_DIR, "ruleta_*.png"),
        threshold: float = 0.85,
        delay: float = 0.5,
        debug_folder: str = os.path.join("debug", "ruleta"),
        lower_green: tuple[int,int,int] = (40, 70, 50),
        upper_green: tuple[int,int,int] = (90, 255, 180),
        min_area: int = 100,
        max_registros: int = 50
    ):
        # Compatibilidad
        self.pattern = pattern
        self.threshold = threshold

        # Parámetros de detección
        self.delay = delay
        self.debug_folder = debug_folder
        self.lower_green = np.array(lower_green, dtype=np.uint8)
        self.upper_green = np.array(upper_green, dtype=np.uint8)
        self.min_area = min_area
        self.registros = deque(maxlen=max_registros)

        os.makedirs(self.debug_folder, exist_ok=True)

        # Procesador de datos para filtrar saltos y velocidades anómalas
        self.data_processor = DataProcessor(max_angle_jump=80.0, max_velocity=500.0)

    def guardar_imagen(self, imagen: np.ndarray, nombre: str):
        ruta = os.path.join(self.debug_folder, nombre)
        cv2.imwrite(ruta, imagen)

    def capturar_ruleta(self, coords: tuple[int,int,int,int]) -> np.ndarray | None:
        if coords is None:
            return None
        x, y, w, h = coords
        shot = pyautogui.screenshot(region=(x, y, w, h))
        return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    def detectar_color_verde(self, frame_bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def calcular_centro_masa(self, mask: np.ndarray) -> tuple[int,int,float]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None, 0.0
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < self.min_area:
            return None, None, 0.0
        M = cv2.moments(c)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return cx, cy, area

    def calcular_angulo(self, frame_bgr: np.ndarray, cx: int, cy: int) -> float:
        h, w = frame_bgr.shape[:2]
        center_x, center_y = w // 2, h // 2
        return math.degrees(math.atan2(cy - center_y, cx - center_x))

    def detectar_giro(
        self,
        coords: tuple[int, int, int, int],
        numero_caido: int | None = None
    ) -> tuple[float, float, float, str, int] | None:
        """
        Captura varios frames de la ruleta, calcula ángulos, velocidad y dirección,
        y filtra resultados anómalos con DataProcessor.
        """
        if coords is None:
            return None

        # Captura ROI (debug)
        roi = self.capturar_ruleta(coords)
        if roi is None:
            return None
        self.guardar_imagen(roi, "spin_roi.png")

        # Serie de frames
        frames = []
        for _ in range(5):
            f = self.capturar_ruleta(coords)
            if f is None:
                return None
            frames.append(f)
            time.sleep(self.delay)

        resultados = []
        for i in range(1, len(frames)):
            f1, f2 = frames[i-1], frames[i]
            m1, m2 = self.detectar_color_verde(f1), self.detectar_color_verde(f2)
            cx1, cy1, a1 = self.calcular_centro_masa(m1)
            cx2, cy2, a2 = self.calcular_centro_masa(m2)
            if not a1 or not a2:
                continue

            ang1 = self.calcular_angulo(f1, cx1, cy1)
            ang2 = self.calcular_angulo(f2, cx2, cy2)
            t1 = time.time()
            t2 = t1 + self.delay
            vel = self.data_processor.calcular_velocidad_angular(ang1, ang2, t1, t2)
            diff = ang2 - ang1
            direc = "sin cambio" if abs(diff) < 1 else ("horario" if diff > 0 else "antihorario")

            resultados.append((ang1, ang2, vel, direc, numero_caido))
            self.registros.append({
                "t1": t1, "t2": t2,
                "angle1": ang1, "angle2": ang2,
                "velocity": vel, "direction": direc,
                "numero": numero_caido,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        # Filtrar y escoger el resultado más estable
        mejor = None
        for r in resultados:
            a1, a2, v, d, num = r
            if abs(a2 - a1) <= self.data_processor.max_angle_jump and v <= self.data_processor.max_velocity:
                if mejor is None or v < mejor[2]:
                    mejor = r

        return mejor
