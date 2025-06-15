# wplay/capture/data_collector.py

from collections import deque
import time
import cv2
import numpy as np
import pyautogui
import pytesseract
import pandas as pd
from typing import List, Tuple, Dict, Optional

from wplay.data.data_processor import DataProcessor
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.capture.numero_detector import NumeroDetector
from wplay.data.data_cleaner import DataCleaner           # Clase de limpieza avanzada
from wplay.data.feature_engineer_deep import FeatureEngineerDeep  # Ingeniería de features profunda

MAX_SPIN_BUFFER = 50

class DataCollector:
    """
    Clase principal para la captura y preprocesado inicial de datos de la ruleta:
      - Captura velocidad y dirección del giro.
      - Detecta el número ganador y cuenta de jugadores.
      - Calcula ganancias de apuestas.
      - Orquesta la limpieza avanzada (DataCleaner) y la ingeniería de features profunda.
      - Genera datasets unificados, para LSTM y para RL listos para modelado.
    """
   
        
    def __init__(
        self,
        ruleta_detector: RuletaDetector,
        numero_detector: NumeroDetector,
        regions: Dict[str, List[Dict[str, int]]], max_buffer=20
    ):
        self.ruleta_detector = ruleta_detector
        self.spin_buffer = deque(maxlen=max_buffer)
        # Detectores y regiones para OCR y visión por computadora
        self.ruleta_detector = ruleta_detector
        self.numero_detector = numero_detector
        self.regions = regions
        self.directions = deque(maxlen=max_buffer)

        # Buffers temporales para estadísticas del giro
        self.vel_buffer: List[float] = []
        self.directions: List[str] = []
        self.last_direction: str = ""
        self.spin_buffer: List[int] = []

        # Procesador auxiliar para interpretación de regiones
        self.data_processor = DataProcessor()
    def get_ruleta_roi(self) -> Optional[tuple[int,int,int,int]]:
        """
        Devuelve la primera ROI de 'ruleta' como (x, y, w, h),
        o None si no existe.
        """
        lista = self.regions.get("ruleta", [])
        if not lista:
            return None
        r = lista[0]
        return r["x"], r["y"], r["w"], r["h"]
    def reset_spin_buffer(self) -> None:
        """Reinicia buffers de velocidad, dirección y spins."""
        self.vel_buffer.clear()
        self.directions.clear()
        self.last_direction = ""
        self.spin_buffer.clear()

    def accumulate_spin(self, coords: tuple[int,int,int,int]):
        """
        Llama repetidamente a detectar_giro y añade lecturas limpias al buffer.
        """
        result = self.ruleta_detector.detectar_giro(coords, self.ruleta_detector.data_processor)
        if result is None:
            return
        vel, direction, numero = result
        # Filtrado estadístico ligero: descartar velocidades atípicas en buffer
        if len(self.spin_buffer) > 2:
            vals = list(self.spin_buffer)
            mu = sum(vals) / len(vals)
            sigma = (sum((v - mu)**2 for v in vals) / len(vals))**0.5
            if abs(vel - mu) > 1.5 * sigma:
                return
        self.spin_buffer.append(vel)


    def get_spin_stats(self) -> Tuple[float, str]:
        """
        Calcula estadísticas robustas del giro:
          - Velocidad mediana.
          - Dirección predominante.
        """
        if not self.vel_buffer:
            return 0.0, ""
        vel = float(np.median(self.vel_buffer))
        dir_ = max(set(self.directions), key=self.directions.count)
        return vel, dir_

    def read_result(self, detected_regions: Dict[str, Tuple[int,int,int,int]]) -> Tuple[Optional[int], int]:
        """
        Detecta el número ganador y la cantidad de jugadores mediante OCR.
        Actualiza el buffer circular de últimos spins.
        """
        numero = self.numero_detector.detectar_numero()
        if numero is None:
            return None, 0

        # Mantener tamaño máximo del buffer
        self.spin_buffer.append(numero)
        if len(self.spin_buffer) > MAX_SPIN_BUFFER:
            self.spin_buffer.pop(0)

        # OCR para contar jugadores en pantalla
        jugadores = 0
        regs_j = self.regions.get("jugadores")
        if regs_j and isinstance(regs_j, list):
            x, y, w, h = regs_j[0]["x"], regs_j[0]["y"], regs_j[0]["w"], regs_j[0]["h"]
            img = np.array(pyautogui.screenshot(region=(x, y, w, h)))
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            txt = pytesseract.image_to_string(
                gray,
                config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
            ).strip()
            jugadores = int(txt) if txt.isdigit() else 0

        return numero, jugadores

    def compute_gain(
        self,
        numero: int,
        categoria: str,
        fichas: int,
        valor_ficha: int = 500
    ) -> Tuple[bool, float]:
        """
        Dada la apuesta previa (categoria y fichas), calcula si se ganó y la ganancia neta.
        Usa payout 2×.
        """
        rojos = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        color = "rojo" if numero in rojos else "negro"
        paridad = "par" if (numero != 0 and numero % 2 == 0) else "impar"
        rango = "1-18" if 1 <= numero <= 18 else "19-36" if 19 <= numero <= 36 else None

        ganaste = categoria in {color, paridad, rango}
        neto = valor_ficha * fichas * (2 if ganaste else -1)
        return ganaste, neto

    def capture_screen(self) -> np.ndarray:
        """Captura y devuelve la pantalla entera en formato BGR."""
        img = np.array(pyautogui.screenshot())
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def get_last_number(self) -> Optional[int]:
        """Devuelve el último número detectado, si existe."""
        return self.spin_buffer[-1] if self.spin_buffer else None

    def get_spin_info(self) -> Tuple[str, float]:
        """Devuelve la dirección y velocidad del giro actual."""
        vel, dir_ = self.get_spin_stats()
        return dir_, vel

    def run_data_pipeline(
        self,
        raw_src: str,
        clean_csv: str,
        unified_csv: str = "data/unified_features.csv",
        lstm_csv: str    = "data/lstm_input.csv",
        rl_csv: str      = "data/rl_input.csv"
    ) -> None:
        """
        Orquesta todo el flujo de datos:
          1) Limpia datos crudos con DataCleaner → clean_csv
          2) Carga clean_csv en DataFrame
          3) Aplica FeatureEngineerDeep → df_feats
          4) Genera y guarda:
             - unified_features.csv
             - lstm_input.csv (formato [n_samples, window, features])
             - rl_input.csv  (vectores planos de estado)
        """
        # 1) Limpieza avanzada
        cleaner = DataCleaner(raw_src=raw_src, clean_csv=clean_csv)
        cleaner.clean()

        # 2) Leer CSV limpio (asegurar parseo de fechas)
        df_clean = pd.read_csv(clean_csv, parse_dates=["fecha_hora"])

        # 3) Ingeniería de features profunda
        fe = FeatureEngineerDeep(
            time_lag_max=cleaner.max_interval,
            accel_window=cleaner.accel_window,
            player_window=cleaner.player_window,
            strategy_window=cleaner.strategy_window
        )
        df_feats = fe.transform(df_clean)

        # 4a) Guardar dataset unificado
        df_feats.to_csv(unified_csv, index=False)
        print(f"[✓] Guardado unified_features en {unified_csv}")

        # 4b) Generar y guardar LSTM input
        df_lstm = fe.to_lstm_input(df_feats)
        df_lstm.to_csv(lstm_csv, index=False)
        print(f"[✓] Guardado lstm_input en {lstm_csv}")

        # 4c) Generar y guardar RL input
        df_rl = fe.to_rl_input(df_feats)
        df_rl.to_csv(rl_csv, index=False)
        print(f"[✓] Guardado rl_input en {rl_csv}")

    def get_payout(self) -> float:
        """Interfaz placeholder para BettingEngine (por implementar)."""
        return 0.0

    # ——————————————————————————————————————————————————————————
    # MÉTODOS DE INGENIERÍA DE CARACTERÍSTICAS SIMPLES (legacy)
    # ——————————————————————————————————————————————————————————

    def build_feature_dataset(self, output_path: Optional[str] = None) -> pd.DataFrame:
        """
        (Legacy) Genera un DataFrame con estadísticas básicas de spin_buffer:
          últimos 5 números, media, varianza, velocidad y dirección.
        """
        if len(self.spin_buffer) < 5:
            return pd.DataFrame()

        vel, dir_ = self.get_spin_stats()
        features = {
            "n_actual": self.spin_buffer[-1],
            "n_1":      self.spin_buffer[-2],
            "n_2":      self.spin_buffer[-3],
            "n_3":      self.spin_buffer[-4],
            "n_4":      self.spin_buffer[-5],
            "media":    np.mean(self.spin_buffer),
            "moda":     max(set(self.spin_buffer), key=self.spin_buffer.count),
            "min":      min(self.spin_buffer),
            "max":      max(self.spin_buffer),
            "range":    max(self.spin_buffer) - min(self.spin_buffer),
            "var":      np.var(self.spin_buffer),
            "vel":      vel,
            "dir":      dir_
        }
        df = pd.DataFrame([features])
        if output_path:
            df.to_csv(output_path, index=False)
        return df

    def generate_unified_features(self, output_path: str = "data/unified_features.csv") -> None:
        """
        (Legacy) Genera un CSV sencillo con categorías y shifts.
        Recomendado usar `run_data_pipeline` y FeatureEngineerDeep en su lugar.
        """
        if len(self.spin_buffer) < 10:
            print("Insuficientes datos para generar características.")
            return

        df = pd.DataFrame({"numero": self.spin_buffer})
        df["color"]   = df["numero"].apply(
            lambda x: "rojo" if x in {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36} else "negro"
        )
        df["paridad"] = df["numero"].apply(
            lambda x: "par" if x % 2 == 0 and x != 0 else "impar"
        )
        df["rango"]   = df["numero"].apply(
            lambda x: "1-18" if 1 <= x <= 18 else "19-36" if 19 <= x <= 36 else "otro"
        )

        df["prev_1"]     = df["numero"].shift(1)
        df["prev_2"]     = df["numero"].shift(2)
        df["diferencia"] = df["numero"].diff()

        vel, dir_ = self.get_spin_stats()
        df["velocidad"]  = vel
        df["direccion"]  = dir_

        df.dropna(inplace=True)
        df.to_csv(output_path, index=False)
        print(f"[✓] unified_features.csv guardado en: {output_path}")

    def incremental_spin(self, coords: tuple[int,int,int,int]) -> None:
        """
        Muestra incremental de velocidad:
        - Captura un solo frame usando capturar_frames (MSS/OpenCV).
        - Calcula centro de masa y ángulo.
        - Si hay muestra previa, calcula velocidad angular instantánea.
        - Almacena velocidad y dirección en los buffers.
        """
        # 1) Capturar un frame y timestamp
        seq = self.ruleta_detector.capturar_frames(coords)
        if not seq:
            return
        t, frame = seq[0]  # tomamos solo el primer frame

        # 2) Máscara y centro de masa
        mask = self.ruleta_detector.detectar_color_verde(frame)
        cx, cy, area = self.ruleta_detector.calcular_centro_masa(mask)
        if area == 0 or cx is None:
            return

        # 3) Ángulo actual
        ang = self.ruleta_detector.calcular_angulo(frame, cx, cy)

        # 4) Si hay muestra previa, calcular velocidad angular
        if hasattr(self, "_last_ang") and hasattr(self, "_last_t"):
            # Δt real
            dt = t - self._last_t
            if dt > 0:
                # velocidad en °/s
                vel = self.data_processor.calcular_velocidad_angular(
                    self._last_ang, ang, self._last_t, t
                )
                # dirección según signo de Δangulo
                diff = (ang - self._last_ang + 360) % 360
                dire = "horario" if diff < 180 else "antihorario"
                # acumulamos
                self.spin_buffer.append(vel)
                # asegurarnos de tener un buffer directions en DataCollector
                if not hasattr(self, "directions"):
                    self.directions = deque(maxlen=self.spin_buffer.maxlen)
                self.directions.append(dire)

        # 5) Guardar como última muestra
        self._last_ang = ang
        self._last_t   = t
