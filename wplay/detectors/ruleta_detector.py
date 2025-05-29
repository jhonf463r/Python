# wplay/detectors/ruleta_detector.py

import cv2
import numpy as np
import pyautogui
import time
import os
import math
from collections import deque
from wplay.data.data_processor import DataProcessor

class RuletaDetector:
    def __init__(
        self,
        delay: float = 0.5,
        debug_folder: str = "debug_ruleta",
        lower_green: tuple[int,int,int] = (40, 70, 50),
        upper_green: tuple[int,int,int] = (90, 255, 180),
        min_area: int = 100,
        max_registros: int = 50
    ):
        """
        :param delay: tiempo entre capturas para estimar velocidad
        :param debug_folder: carpeta donde guardar imágenes de debug
        :param lower_green, upper_green: rango HSV para detectar la franja verde
        :param min_area: área mínima de contorno para ser válido
        :param max_registros: cuántos registros de giro guardar en memoria
        """
        self.delay = delay
        self.debug_folder = debug_folder
        self.lower_green = np.array(lower_green, dtype=np.uint8)
        self.upper_green = np.array(upper_green, dtype=np.uint8)
        self.min_area = min_area
        self.registros = deque(maxlen=max_registros)
        os.makedirs(self.debug_folder, exist_ok=True)
        # Creamos un DataProcessor interno para validar saltos y velocidades
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
        ang = math.degrees(math.atan2(cy - center_y, cx - center_x))
        return ang

    def detectar_giro(
        self,
        coords: tuple[int, int, int, int],
        data_processor,
        numero_caido: int | None = None
    ) -> tuple[float, float, float, str, int] | None:
        """
        Toma varias capturas de la ruleta, procesa cada par de imágenes para calcular
        el ángulo, la velocidad y la dirección del giro, y utiliza data_processor
        para filtrar resultados. Devuelve el mejor (angle1, angle2, velocity, direction, numero_caido).
        """

        # 1) Debug: ROI
        if coords is None:
            print("[giro][DEBUG] coords=None: no se puede capturar la ruleta.")
            return None
        x, y, w, h = coords
        roi_img = pyautogui.screenshot(region=(x, y, w, h))
        roi_bgr = cv2.cvtColor(np.array(roi_img), cv2.COLOR_RGB2BGR)
        os.makedirs(os.path.join(self.debug_folder, "spin_roi"), exist_ok=True)
        roi_path = os.path.join(self.debug_folder, "spin_roi", "roi.png")
        cv2.imwrite(roi_path, roi_bgr)
      #  print(f"[giro][DEBUG] ROI guardado en {roi_path} → coords={coords}")

        # 2) Capturas sucesivas
        frames: list[np.ndarray] = []
        for i in range(5):
            f = self.capturar_ruleta(coords)
            if f is None:
                print(f"[giro][WARN] captura {i} falló, abortando.")
                return None
            frames.append(f)
            time.sleep(self.delay)

        # 3) Procesar pares consecutivos
        resultados = []
        spin_dir = os.path.join(self.debug_folder, "spin")
        os.makedirs(spin_dir, exist_ok=True)

        for i in range(1, len(frames)):
            f1, f2 = frames[i-1], frames[i]
            # máscaras
            m1 = self.detectar_color_verde(f1)
            m2 = self.detectar_color_verde(f2)
            cv2.imwrite(os.path.join(spin_dir, f"frame_{i-1}.png"), f1)
            cv2.imwrite(os.path.join(spin_dir, f"mask_{i-1}.png"), m1)
         #   print(f"[giro][DEBUG] guardado frame_{i-1}.png y mask_{i-1}.png")

            # centros de masa
            cx1, cy1, area1 = self.calcular_centro_masa(m1)
            cx2, cy2, area2 = self.calcular_centro_masa(m2)
            if area1 == 0 or area2 == 0:
           #     print(f"[giro][DEBUG] contorno no válido en par {i-1}/{i}: area1={area1}, area2={area2}")
                continue

            # ángulos y tiempos
            ang1 = self.calcular_angulo(f1, cx1, cy1)
            ang2 = self.calcular_angulo(f2, cx2, cy2)
            t1 = time.time()
            t2 = t1 + self.delay
            vel = data_processor.calcular_velocidad_angular(ang1, ang2, t1, t2)
            diff = ang2 - ang1
            direc = "sin cambio" if abs(diff) < 1 else ("horario" if diff > 0 else "antihorario")

          #  print(f"[giro][DEBUG] par {i-1}->{i}: ang1={ang1:.1f}, ang2={ang2:.1f}, "f"vel={vel:.1f}, dir={direc}")

            resultados.append((ang1, ang2, vel, direc, numero_caido))
            self.registros.append({
                "t1": t1, "t2": t2,
                "angle1": ang1, "angle2": ang2,
                "velocity": vel, "direction": direc,
                "numero": numero_caido,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        # 4) Filtrar por saltos y velocidad, elegir el más estable
        mejor = None
        for r in resultados:
            a1, a2, v, d, num = r
            if abs(a2 - a1) <= data_processor.max_angle_jump and v <= data_processor.max_velocity:
                if mejor is None or v < mejor[2]:
                    mejor = r

        if mejor is None:
            print("[giro][WARN] Ningún resultado válido tras filtrar saltos y velocidad.")
      #  else:
          #  print(f"[giro][OK] mejor resultado → angle1={mejor[0]:.1f}, "
           #     f"angle2={mejor[1]:.1f}, vel={mejor[2]:.1f}, dir={mejor[3]}")

        return mejor
