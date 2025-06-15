import time
import threading
import cv2
import numpy as np
import pyautogui
from typing import Dict, Tuple, Any

from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.detectors.numero_detector import NumeroDetector



class DataCollector:
    """
    Acumula datos de un giro de ruleta:
      - Extrae ángulos de la rueda a lo largo del giro.
      - Calcula velocidades angulares.
      - Detecta el número final.
    Funciona lanzando un hilo que, tras notify desde SpinController,
    captura la región de la ruleta hasta que ésta se detiene.
    """

    def __init__(
        self,
        ruleta_detector: RuletaDetector,
        numero_detector: NumeroDetector,
    ):
        """
        :param ruleta_detector: detector que, dado un recorte de la ruleta,
                                devuelve el ángulo actual (en grados) y
                                sabe cuándo la rueda se ha detenido.
        :param numero_detector: detector que, al final del giro, lee y
                                devuelve el número ganador.
        """
        self.ruleta_detector = ruleta_detector
        self.numero_detector = numero_detector

        # Buffers internos:
        self._angles = []        # ángulos sucesivos
        self._timestamps = []    # marcas de tiempo de cada ángulo
        self._velocities = []    # velocidades angulares calculadas
        self._final_number = None

        # Estado de la captura:
        self._collecting = False
        self._lock = threading.Lock()

    def reset_spin_buffer(self) -> None:
        """
        Limpia todos los buffers antes de iniciar un nuevo giro.
        """
        with self._lock:
            self._angles.clear()
            self._timestamps.clear()
            self._velocities.clear()
            self._final_number = None
            self._collecting = False

    def accumulate_spin(self, roi_map: Dict[str, Tuple[int, int, int, int]]) -> None:
        """
        Inicia la captura de un giro en un hilo separado.
        :param roi_map: diccionario con clave "ruleta" → (x, y, w, h)
                        definida por SpinController.
        """
        with self._lock:
            if self._collecting:
                # Si ya estamos recogiendo, no lanzamos otro hilo
                return
            self._collecting = True

        # Extraemos la región de interés de la ruleta
        x, y, w, h = roi_map["ruleta"]

        def _collect_loop():
            prev_angle = None
            prev_time = None

            while True:
                # 1) Captura pantalla y recorta ROI
                screen = np.array(pyautogui.screenshot())
                bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                roi = gray[y : y + h, x : x + w]

                # 2) Detectar ángulo actual
                angle = self.ruleta_detector.get_angle(roi)
                now = time.time()

                # 3) Calcular velocidad si tenemos un prev
                if prev_angle is not None and prev_time is not None:
                    delta_ang = (angle - prev_angle + 180) % 360 - 180
                    vel = delta_ang / (now - prev_time)
                    with self._lock:
                        self._velocities.append(vel)

                # Registrar datos y preparar siguiente iteración
                with self._lock:
                    self._angles.append(angle)
                    self._timestamps.append(now)
                prev_angle = angle
                prev_time = now

                # 4) Si la ruleta está parada, leemos el número y salimos
                if self.ruleta_detector.is_stopped(roi):
                    number = self.numero_detector.get_number(roi)
                    with self._lock:
                        self._final_number = number
                        self._collecting = False
                    break

                # Breve pausa para no saturar la CPU
                time.sleep(0.01)

        # Lanzamos la recolección en background
        thread = threading.Thread(target=_collect_loop, daemon=True)
        thread.start()

    def spin_complete(self) -> bool:
        """
        :return: True cuando la captura del giro ha finalizado.
        """
        with self._lock:
            return not self._collecting

    def get_spin_stats(self) -> Dict[str, Any]:
        """
        Llama una vez spin_complete() retorna True.
        :return: dict con:
                 - 'avg_velocity': velocidad angular media (grados/s)
                 - 'final_number' : número donde terminó la bola
                 - 'data_points'  : número de muestras de velocidad tomadas
        """
        with self._lock:
            if not self._timestamps:
                return {"avg_velocity": None, "final_number": None, "data_points": 0}

            avg_vel = sum(self._velocities) / len(self._velocities)
            return {
                "avg_velocity": avg_vel,
                "final_number": self._final_number,
                "data_points": len(self._velocities),
            }
