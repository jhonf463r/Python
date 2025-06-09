# wplay/capture/data_collector.py

import time
import cv2
import numpy as np
import pyautogui
import pytesseract
from typing import List, Tuple, Dict, Optional

from wplay.data.data_processor import DataProcessor
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.capture.numero_detector import NumeroDetector

# Tamaño máximo del buffer de spins para construir estados
MAX_SPIN_BUFFER = 50

class DataCollector:
    """
    Encapsula la captura de datos de la ruleta:
     - Acumula velocidades y direcciones de giro.
     - Acumula los últimos números resultantes (spin_buffer).
     - Lee el resultado (número y jugadores).
     - Calcula la ganancia de una apuesta previa.
     - Provee captura de pantalla y métodos auxiliares.
    """

    def __init__(
        self,
        ruleta_detector: RuletaDetector,
        numero_detector: NumeroDetector,
        regions: Dict[str, List[Dict[str, int]]]
    ):
        self.ruleta_detector = ruleta_detector
        self.numero_detector = numero_detector
        self.regions = regions

        # Buffers internos
        self.vel_buffer: List[float] = []
        self.directions: List[str] = []
        self.last_direction: str = ""
        self.spin_buffer: List[int] = []

        # Procesador auxiliar
        self.data_processor = DataProcessor()


    def reset_spin_buffer(self) -> None:
        """Limpia los buffers de velocidad y de spins entre rondas."""
        self.vel_buffer.clear()
        self.directions.clear()
        self.last_direction = ""
        self.spin_buffer.clear()

    def accumulate_spin(self, detected_regions: Dict[str, Tuple[int,int,int,int]]) -> None:
        """
        Debe llamarse continuamente mientras la ruleta gira.
        Detecta velocidad y dirección y las acumula en vel_buffer.
        """
        coords = detected_regions.get("ruleta")
        if not coords:
            return

        result = self.ruleta_detector.detectar_giro(coords, self.data_processor)
        if not result:
            return

        _, _, velocity, direction, _ = result
        self.vel_buffer.append(velocity)
        self.directions.append(direction)

    def get_spin_stats(self) -> Tuple[float, str]:
        """
        Devuelve la velocidad “robusta” y la dirección más frecuente.
        """
        if not self.vel_buffer:
            return 0.0, ""
        vel = float(np.median(self.vel_buffer))
        dir_ = max(set(self.directions), key=self.directions.count)
        return vel, dir_

    def read_result(self, detected_regions: Dict[str, Tuple[int,int,int,int]]) -> Tuple[Optional[int], int]:
        """
        Lee el número ganador y la cantidad de jugadores presentes.
        También actualiza el spin_buffer.
        """
        numero = self.numero_detector.detectar_numero()
        if numero is None:
            return None, 0

        self.spin_buffer.append(numero)
        if len(self.spin_buffer) > MAX_SPIN_BUFFER:
            self.spin_buffer.pop(0)

        jugadores = 0
        regs_j = self.regions.get("jugadores")
        if regs_j and isinstance(regs_j, list):
            r = regs_j[0]
            x, y, w, h = r["x"], r["y"], r["w"], r["h"]
            img_j = np.array(pyautogui.screenshot(region=(x, y, w, h)))
            gray_j = cv2.cvtColor(img_j, cv2.COLOR_RGB2GRAY)
            txt_j = pytesseract.image_to_string(
                gray_j,
                config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
            ).strip()
            jugadores = int(txt_j) if txt_j.isdigit() else 0

        return numero, jugadores

    def compute_gain(
        self,
        numero: int,
        categoria: str,
        fichas: int,
        valor_ficha: int = 500
    ) -> Tuple[bool, float]:
        """
        Dada la apuesta anterior (categoria, fichas):
        - Determina color, paridad y rango del número.
        - Calcula si ganaste y la ganancia neta (payout 2×).
        """
        rojos   = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        color   = "rojo" if numero in rojos else "negro"
        paridad = "par" if (numero != 0 and numero % 2 == 0) else "impar"
        rango   = "1-18" if 1 <= numero <= 18 else "19-36" if 19 <= numero <= 36 else None

        ganaste    = categoria in {color, paridad, rango}
        # **Usar payout 2× (multiplicador = 2)**
        multiplier = 2
        neto       = valor_ficha * fichas * (multiplier if ganaste else -1)
        return ganaste, neto


    # ——— Métodos añadidos para integration con BettingEngine ———

    def capture_screen(self) -> np.ndarray:
        """
        Captura la pantalla completa y devuelve frame en formato BGR (OpenCV).
        """
        img = np.array(pyautogui.screenshot())
        # pyautogui devuelve en RGB, convertimos a BGR para OpenCV
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def get_last_number(self) -> Optional[int]:
        """
        Retorna el último número detectado en el buffer de spins.
        """
        return self.spin_buffer[-1] if self.spin_buffer else None

    def get_spin_info(self) -> Tuple[str, float]:
        """
        Retorna (dirección, velocidad) calculada hasta el momento.
        """
        vel, dir_ = self.get_spin_stats()
        return dir_, vel

    def get_payout(self) -> float:
        """
        Si se ha hecho una apuesta, calcula la ganancia neta
        usando compute_gain sobre el último número y la última apuesta.
        (Debe guardarse la última apuesta en el motor de apuestas).
        """
        # Esta implementación asume que el BettingEngine llamará a compute_gain()
        # directamente; aquí devolvemos siempre 0.0 por compatibilidad.
        return 0.0
