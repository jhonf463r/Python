import logging
import os
import time
import math
import cv2
import numpy as np
import pyautogui
from collections import deque
from typing import Tuple, Optional, List
from wplay.data.data_processor import DataProcessor

class RuletaDetector:
    def __init__(
        self,
        delay: float = 0.5,
        debug_folder: str = "debug_ruleta",
        lower_green: Tuple[int, int, int] = (40, 70, 50),
        upper_green: Tuple[int, int, int] = (90, 255, 180),
        min_area: int = 100,
        max_registros: int = 50,
        max_saved_masks: int = 20
    ):
        self.delay = delay
        self.capture_fps = 1.0 / delay
        self.debug_folder = debug_folder
        os.makedirs(self.debug_folder, exist_ok=True)

        self.lower_green = np.array(lower_green, dtype=np.uint8)
        self.upper_green = np.array(upper_green, dtype=np.uint8)
        self.min_area = min_area

        self.data_proc = DataProcessor(max_angle_jump=80.0, max_velocity=500.0)
        self.diff_threshold = 500   # px mínimo para diferenciar máscaras
        self.max_saved_masks = max_saved_masks

        self.tracking = False
        self.current_angle = None
        self.last_angle = None

        # Intentar crear TrackerCSRT en distintos namespaces
        self.tracker = None
        for ctor in (
            ("cv2.legacy.TrackerCSRT_create", lambda: cv2.legacy.TrackerCSRT_create()),
            ("cv2.TrackerCSRT_create",      lambda: cv2.TrackerCSRT_create()),
            ("cv2.Tracker_create('CSRT')",  lambda: cv2.Tracker_create("CSRT")),
        ):
            try:
                self.tracker = ctor[1]()
                break
            except Exception:
                self.tracker = None

    def guardar_imagen(self, imagen: np.ndarray, nombre: str):
        """
        Guarda la imagen en debug_folder y, si es una máscara numerada
        (mask_frame_XX.png), mantiene solo las últimas self.max_saved_masks.
        """
        ruta = os.path.join(self.debug_folder, nombre)
        cv2.imwrite(ruta, imagen)

        if nombre.startswith("mask_frame_") and nombre.endswith(".png"):
            # listar y ordenar
            files = sorted(f for f in os.listdir(self.debug_folder)
                           if f.startswith("mask_frame_") and f.endswith(".png"))
            # eliminar las más antiguas
            for old in files[:-self.max_saved_masks]:
                os.remove(os.path.join(self.debug_folder, old))

    def capturar_ruleta(self, coords: Tuple[int, int, int, int]) -> Tuple[np.ndarray, float]:
        x, y, w, h = coords
        shot = pyautogui.screenshot(region=(x, y, w, h))
        ts = time.time()
        frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
        return frame, ts

    def detectar_color_verde(self, frame: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        k = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
        return mask

    def calcular_centro_masa(self, mask: np.ndarray) -> Tuple[Optional[int], Optional[int], float]:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None, None, 0.0
        c = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < self.min_area:
            return None, None, 0.0
        M = cv2.moments(c)
        if M['m00'] == 0:
            return None, None, 0.0
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        return cx, cy, area

    def calcular_angulo(self, frame: np.ndarray, cx: int, cy: int) -> float:
        h, w = frame.shape[:2]
        return math.degrees(math.atan2(cy - h // 2, cx - w // 2))

    def init_tracker(self, frame: np.ndarray) -> bool:
        mask = self.detectar_color_verde(frame)
        cx, cy, area = self.calcular_centro_masa(mask)
        if cx is None:
            return False
        side = int(math.sqrt(area) * 2)
        x = max(cx - side // 2, 0)
        y = max(cy - side // 2, 0)
        bbox = (x, y, side, side)
        self.tracking = self.tracker.init(frame, bbox)
        return self.tracking

    def update_tracker(self, frame: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        _ = self.detectar_color_verde(frame)
        ok, bbox = self.tracker.update(frame)
        if not ok:
            self.tracking = False
            return None, None
        x, y, w, h = [int(v) for v in bbox]
        return x + w // 2, y + h // 2

    def detectar_giro(
        self,
        coords: Tuple[int, int, int, int],
        n_frames: int = 5
    ) -> Optional[Tuple[float, str]]:
        """
        Captura n_frames espaciados por self.delay, genera sus máscaras,
        descarta pares demasiado similares y elige la velocidad angular
        más lenta válida dentro de max_velocity.
        Si no se encuentra ninguna velocidad válida, retorna el último
        valor conocido (self.last_velocity, self.last_direction).
        """
        frames: List[np.ndarray] = []
        masks:  List[np.ndarray] = []
        times:  List[float]      = []

        # 1) Captura sincronizada
        for i in range(n_frames):
            frame, ts = self.capturar_ruleta(coords)
            mask = self.detectar_color_verde(frame)
            self.guardar_imagen(mask, f"mask_frame_{i+1:02d}.png")
            frames.append(frame)
            masks.append(mask)
            times.append(ts)
            time.sleep(self.delay)

        candidatos: List[Tuple[float, str]] = []

        # 2) Función interna para comparar dos índices
        def procesa_par(i: int, j: int):
            dt = times[j] - times[i]
            diff = cv2.absdiff(masks[i], masks[j])
            num_diff = cv2.countNonZero(diff)
            if num_diff < self.diff_threshold:
            #    logging.debug(f"[GIRO] Par {i}->{j} diff={num_diff} < threshold={self.diff_threshold}")
                return

            # Obtener centros
            if self.tracking and self.tracker:
                cx1, cy1 = self.update_tracker(frames[i])
                cx2, cy2 = self.update_tracker(frames[j])
            else:
                cx1, cy1, _ = self.calcular_centro_masa(masks[i])
                cx2, cy2, _ = self.calcular_centro_masa(masks[j])
                if i == 0 and cx1 is not None and self.tracker:
                    self.init_tracker(frames[i])

            if None in (cx1, cy1, cx2, cy2):
            #    logging.debug(f"[GIRO] Centros inválidos para par {i}->{j}")
                return

            ang1 = self.calcular_angulo(frames[i], cx1, cy1)
            ang2 = self.calcular_angulo(frames[j], cx2, cy2)
            vel  = self.data_proc.calcular_velocidad_angular(ang1, ang2, times[i], times[j])
            direc = (
                'sin cambio' if abs(ang2 - ang1) < 1 else
                'horario'   if (ang2 - ang1) > 0 else
                'antihorario'
            )
            candidatos.append((vel, direc))
          #  logging.debug(f"[GIRO] Par {i}->{j}: vel={vel:.2f} deg/s, dir={direc}")

        # 3) Primero pares consecutivos
        for k in range(n_frames - 1):
            procesa_par(k, k + 1)

        # 4) Si no hubo candidatos, probar saltos desde el primer frame
        if not candidatos:
            for k in range(2, n_frames):
                procesa_par(0, k)
                if candidatos:
                    break

        # 5) Filtrar y elegir el más lento dentro de lo permitido
        validos = [c for c in candidatos if c[0] <= self.data_proc.max_velocity]
        if validos:
            mejor = min(validos, key=lambda x: x[0])
            # Guardar para fallback
            self.last_velocity, self.last_direction = mejor
          #  logging.debug(f"[GIRO] Velocidad válida seleccionada: {mejor[0]:.2f}, dir={mejor[1]}")
            return mejor

        # 6) Fallback: devolver último valor conocido o cero
        fallback_vel = getattr(self, "last_velocity", 0.0)
        fallback_dir = getattr(self, "last_direction", "desconocido")
       # logging.warning(f"[GIRO] No se encontró velocidad válida; usando fallback {fallback_vel:.2f}, dir={fallback_dir}")
        return fallback_vel, fallback_dir

    def get_current_angle(self, frame: np.ndarray) -> Optional[float]:
        """
        Devuelve el ángulo actual respecto al centro del frame.
        Usa tracker si está activo, o centro de masa si no.
        """
        try:
            if self.tracking and self.tracker:
                cx, cy = self.update_tracker(frame)
            else:
                # ⚠️ Validar que el frame tiene 3 canales (evita crash si es una máscara)
                if frame.ndim != 3 or frame.shape[2] != 3:
                    print("[WARNING] [get_current_angle] Frame inválido: no es imagen BGR.")
                    return None
                mask = self.detectar_color_verde(frame)
                cx, cy, _ = self.calcular_centro_masa(mask)

            if cx is None or cy is None:
                return None

            angulo = self.calcular_angulo(frame, cx, cy)
            return angulo
        except Exception as e:
            print(f"[WARNING] [get_current_angle] Error al calcular ángulo: {e}")
            return None
