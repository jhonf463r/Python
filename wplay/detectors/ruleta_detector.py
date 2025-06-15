import cv2
import numpy as np
import time
import math
import random
from collections import deque
import mss
from typing import Tuple

from wplay.data.data_processor import DataProcessor  # <-- aquí
class DataProcessor:
    def __init__(self, max_angle_jump=80.0, max_velocity=500.0):
        self.max_angle_jump = max_angle_jump
        self.max_velocity = max_velocity

class RuletaDetector:
    def __init__(
        self,
        capture_fps: int = 30,
        capture_duration: float = 1.0,
        ransac_iters: int = 100,
        inlier_tol: float = 3.0,
        delay: float = 0.0,
        debug_folder: str = "debug_ruleta",
        lower_green: tuple[int,int,int] = (40, 70, 50),
        upper_green: tuple[int,int,int] = (90, 255, 180),
        min_area: int = 100,
        max_registros: int = 50
    ):
        self.capture_fps = capture_fps
        self.capture_duration = capture_duration
        self.ransac_iters = ransac_iters
        self.inlier_tol = inlier_tol
        self.delay = delay
        self.debug_folder = debug_folder
        self.lower_green = np.array(lower_green, dtype=np.uint8)
        self.upper_green = np.array(upper_green, dtype=np.uint8)
        self.min_area = min_area
        self.registros = deque(maxlen=max_registros)
        self.data_processor = DataProcessor(max_angle_jump=80.0, max_velocity=500.0)

    def capturar_frames(self, coords):
        """
        Captura una secuencia de frames con MSS y devuelve lista de (timestamp, frame)
        """
        x, y, w, h = coords
        total_frames = int(self.capture_fps * self.capture_duration)
        frames = []
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            for _ in range(total_frames):
                t = time.time()
                sct_img = sct.grab(monitor)
                frame = np.array(sct_img)[..., :3]
                frames.append((t, cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)))
                if self.delay:
                    time.sleep(self.delay)
        return frames

    def calcular_centro_masa(self, mask: np.ndarray):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None, 0.0
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < self.min_area:
            return None, None, 0.0
        M = cv2.moments(c)
        return int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]), area
    
    def calcular_angulo(self, frame_bgr: np.ndarray, cx: int, cy: int) -> float:
        """
        Calcula el ángulo (en grados) del punto (cx,cy) respecto al centro del frame.
        Devuelve un valor en [-180, +180].
        """
        h, w = frame_bgr.shape[:2]
        center_x, center_y = w // 2, h // 2
        # atan2 retorna radianes; lo convertimos a grados
        ang = math.degrees(math.atan2(cy - center_y, cx - center_x))
        return ang


    def detectar_color_verde(self, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    def ransac_angular_velocity(self, times, angles):
        best_vel = None
        best_inliers = []
        n = len(times)
        for _ in range(self.ransac_iters):
            i, j = random.sample(range(n), 2)
            dt = times[j] - times[i]
            if dt <= 0:
                continue
            dv = angles[j] - angles[i]
            vel_candidate = dv / dt
            # count inliers
            inliers = []
            for k in range(n):
                pred = angles[i] + vel_candidate * (times[k] - times[i])
                if abs(pred - angles[k]) <= self.inlier_tol:
                    inliers.append(k)
            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_vel = vel_candidate
        return best_vel, best_inliers

    def detectar_giro(self, coords, data_processor, numero_caido=None):
            """
            Variante mejorada: captura continua de frames, calc. timestamps reales,
            filtrado de ángulos, y RANSAC para velocidad angular.
            """
            if coords is None:
                return None
            # Captura N frames con MSS/OpenCV
            seq = self.capturar_frames(coords)
            times, frames = zip(*seq)

            # Extraer ángulos y áreas
            angles, areas = [], []
            for f in frames:
                mask = self.detectar_color_verde(f)
                cx, cy, area = self.calcular_centro_masa(mask)
                if area == 0:
                    angles.append(None)
                    areas.append(0)
                    continue
                ang = self.calcular_angulo(f, cx, cy)
                angles.append(ang)
                areas.append(area)

            # Filtrar frames inválidos antes de RANSAC
            valid = []  # (t_i, ang_i)
            for i, (t, ang) in enumerate(zip(times, angles)):
                if ang is None:
                    continue
                if i > 0:
                    if angles[i-1] is None:
                        continue
                    if abs(ang - angles[i-1]) > data_processor.max_angle_jump:
                        continue
                    if abs(areas[i] - areas[i-1]) > 0.3 * areas[i-1]:
                        continue
                valid.append((t, ang))
            if len(valid) < 5:
                return None

            # RANSAC para velocidad angular
            times_v, angs_v = zip(*valid)
            vel, inliers = self.ransac_angular_velocity(times_v, angs_v)
            if vel is None or abs(vel) > data_processor.max_velocity:
                return None

            direction = 'horario' if vel > 0 else 'antihorario'
            self.registros.append({
                'velocity': vel,
                'direction': direction,
                'numero': numero_caido,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return vel, direction, numero_caido
   