import datetime
import os
import time
import cv2
import numpy as np
import pandas as pd
import pyautogui
import pytesseract
import logging

from collections import deque
from typing import List, Tuple, Dict, Optional

from wplay.data.data_processor import DataProcessor
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.capture.numero_detector import NumeroDetector
from wplay.data.data_cleaner import DataCleaner
from wplay.data.feature_engineer_deep import FeatureEngineerDeep
from wplay.utils.chaos import compute_hurst, compute_lyapunov, shannon_entropy
from wplay.utils.constants import MIN_DT, MAX_DT, MIN_ACCEL_POINTS, MIN_PLAYER_POINTS, MIN_CHAOS_POINTS, CHAOS_WINDOW_SIZE

logging.getLogger('pytesseract').setLevel(logging.WARNING)
MAX_SPIN_BUFFER    = 50
LOW_VEL_THRESHOLD  = 20.0   # Umbral para velocidad baja
LOW_VEL_MAX_COUNT  = 3      # Máximo número de bajas seguidas antes de recargar

class DataCollector:
    """
    
    Captura y preprocesado de datos de la ruleta:
    - Velocidad y dirección del giro.
    - Número ganador y conteo de jugadores.
    - Cálculo de ganancias y orquestación de pipelines de datos.
    """
    ROJOS = {
        1, 3, 5, 7, 9, 12, 14, 16, 18,
        19, 21, 23, 25, 27, 30, 32, 34, 36
    }

    def __init__(self,
                 ruleta_detector: RuletaDetector,
                 numero_detector: NumeroDetector,
                 regions: Dict[str, List[Dict[str, int]]],
                 max_buffer: int = 20,
                 history_file: Optional[str] = None,
                 preload_n: int = 50,
                 accel_window: int = 2,
                 player_window: int = 1,
                 chaos_window: int = CHAOS_WINDOW_SIZE):
        """
        Captura y preprocesado de datos de la ruleta, con precarga de histórico.

        Args:
        - ruleta_detector: detector de giro.
        - numero_detector: detector OCR de número.
        - regions: regiones de pantalla.
        - max_buffer: tamaño de buffers de giro offline.
        - history_file: ruta a CSV con columnas ['timestamp','numero','velocity','jugadores_presentes'].
        - preload_n: cuántos registros últimos cargar.
        """
        # Detectores y configuración
        self.ruleta_detector = ruleta_detector
        self.numero_detector = numero_detector
        self.regions         = regions

        # Buffers offline para estadísticas de giro
        self.vel_buffer = deque(maxlen=max_buffer)
        self.dir_buffer = deque(maxlen=max_buffer)

        # Buffers online para features en tiempo real
        self.spin_times       = []                     # timestamps de cada spin
        self.velocity_history = []                     # velocidades calculadas
        self.jugadores_buffer = []                     # recuento de jugadores
        
        self.spin_event_times   = []     # timestamps de cada SPIN (no de frame)
        self.jugadores_history  = []     # conteo de jugadores post-SPIN
        # Parámetros de normalización de tiempo entre giros
        self.min_dt = 0.5   # p. ej. giro más rápido en 0.5 s
        self.max_dt = 20.0  # p. ej. giro más lento en 20 s
        self.accel_window  = accel_window
        self.player_window = player_window
        self.chaos_window  = chaos_window

        # Para procesamiento adicional o limpieza
        self.data_processor = DataProcessor()
        self.low_vel_count  = 0

        # Buffers auxiliares offline
        self.spin_records   = []
        self.angle_history  = []

        # Historial de números
        self.spin_nums = deque(maxlen=MAX_SPIN_BUFFER)
        

        # --- Precarga de histórico si se proporciona archivo ---
        if history_file:
            try:
                df_hist = pd.read_csv(history_file, usecols=[
                    'timestamp', 'numero', 'velocity', 'jugadores_presentes'
                ])
                tail = df_hist.tail(preload_n)
                for _, row in tail.iterrows():
                    self.spin_times.append(float(row['timestamp']))
                    self.velocity_history.append(float(row['velocity']))
                    self.jugadores_buffer.append(int(row['jugadores_presentes']))
                    self.spin_nums.append(int(row['numero']))

                logging.info(f"[DataCollector] Precargados {len(self.spin_times)} registros históricos")
                logging.debug(f"   → spin_times peek: {self.spin_times[:5]} …")
                logging.debug(f"   → velocity_history peek: {self.velocity_history[:5]} …")
                logging.debug(f"   → jugadores_buffer peek: {self.jugadores_buffer[:5]} …")
                logging.debug(f"   → spin_nums peek: {list(self.spin_nums)[:5]} …")
            except Exception as e:
                logging.warning(f"[DataCollector] Error precargando histórico: {e}")


    def setup_detection(self):
        coords = self.get_ruleta_roi()
        if coords is None:
            raise RuntimeError("No se encontró ROI de ruleta para calibración.")

        self.ruleta_detector.calibrate_hsv(coords, samples=10)
        print(f"[SETUP] HSV calibrado: {self.ruleta_detector.lower_green} – {self.ruleta_detector.upper_green}")

        frame, _ = self.ruleta_detector.capturar_ruleta(coords)
        mask = self.ruleta_detector.detectar_color_verde(frame)
        ok = self.ruleta_detector.init_tracker(frame, mask)
        print(f"[SETUP] Tracker CSRT iniciado: {ok}")

    def reset_spin_buffer(self) -> None:
        self.vel_buffer.clear()
        self.dir_buffer.clear()
        print("[DEBUG] Buffers de giro reseteados.")

    def get_ruleta_roi(self) -> Optional[Tuple[int, int, int, int]]:
        lst = self.regions.get("ruleta", [])
        if not lst:
            return None
        r = lst[0]
        return (r["x"], r["y"], r["w"], r["h"])

    def reset_buffers(self):
        """
        Limpia solo los buffers temporales de cada muestreo, sin afectar el historial
        necesario para el cálculo de features online:

        - Se vacían:
            • spin_records    (registros de ángulos/giro temporales)
            • angle_history   (historial de ángulos dentro de un muestreo)
        - Se conserva:
            • spin_times
            • velocity_history
            • jugadores_buffer
            • spin_nums
        """
        # Buffers temporales de tracking angular
        self.spin_records = []
        self.angle_history = []


    def detectar_jugadores(self, momento: str = "") -> Optional[int]:
        """
        Detecta cuántos jugadores hay usando OCR sobre la región de jugadores.
        """
        try:
            coords = self.regions.get("jugadores", [])[0]
            x, y, w, h = coords["x"], coords["y"], coords["w"], coords["h"]

            # Captura de pantalla en la zona de jugadores
            img = pyautogui.screenshot(region=(x, y, w, h))
            img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Preprocesado: escalado y binarización
            upscaled = cv2.resize(
                img_np,
                None,
                fx=2.0,
                fy=2.0,
                interpolation=cv2.INTER_LINEAR
            )
            gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
            morph = cv2.morphologyEx(
                gray,
                cv2.MORPH_CLOSE,
                np.ones((3, 3), np.uint8)
            )

            # OCR en modo completamente silencioso
            import io, contextlib
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                text = pytesseract.image_to_string(
                    morph,
                    config="--oem 3 --psm 7 --quiet"
                ).strip()

            # Si no es dígito válido, devolvemos None
            return int(text) if text.isdigit() else None

        except Exception:
            return None

    def accumulate_spin(self, coords: Tuple[int, int, int, int]):
        """
        1) Reinicia buffers internos de ángulo.
        2) Captura número de jugadores ANTES del giro.
        3) Mide giro (velocidad + dirección).
        4) Captura número de jugadores DESPUÉS del giro.
        5) Filtra giros inválidos.
        6) Guarda velocidad cruda y dirección (offline).
        7) Captura UNÁ vez: ángulo y timestamp del momento 'post-spin'.
        8) Calcula velocidad instántanea basada en delta-ángulo / delta-spin-time.
        9) Almacena en buffers (acotados a MAX_SPIN_BUFFER).
        10) Logea el estado.
        """
        import time, logging

        # 1) Reiniciar solo buffers de ángulo temporales
        self.reset_buffers()

        # 2) Jugadores antes
        jugadores_antes = self.detectar_jugadores("ANTES")

        # 3) Medir giro
        res = self.ruleta_detector.detectar_giro(coords)
        velocidad, direccion = res if res else (0.0, "")

        # 4) Filtrar giros inválidos
        if velocidad < self.min_dt or direccion == "":
            logging.warning(
                f"[accumulate_spin] Giro inválido: vel={velocidad:.2f}, dir='{direccion}' → omitido"
            )
            return

        # 5) Jugadores después
        jugadores_despues = self.detectar_jugadores("DESPUÉS")
        jugadores = jugadores_despues if jugadores_despues is not None else (jugadores_antes or 0)

        # 6) Estadísticas offline
        self.vel_buffer.append(velocidad)
        self.dir_buffer.append(direccion)

        # 7) Captura UN ángulo y timestamp POST-spin
        now = time.time()
        try:
            frame, _ = self.ruleta_detector.capturar_ruleta(coords)
            angle = self.ruleta_detector.get_current_angle(frame)
        except Exception as e:
            angle = self.angle_history[-1] if self.angle_history else 0.0
            logging.warning(f"[accumulate_spin] get_current_angle falló: {e}")

        # 8) Velocidad instantánea = Δángulo / Δtiempo ENTRE SPINS
        if self.angle_history and self.spin_times:
            dt = now - self.spin_times[-1]
            da = angle - self.angle_history[-1]
            inst_vel = da / dt if dt > 1e-6 else 0.0
            # filtrar outliers
            if inst_vel < 0 or inst_vel > max(self.vel_buffer):
                inst_vel = self.velocity_history[-1] if self.velocity_history else 0.0
        else:
            inst_vel = 0.0

         # 9) Almacenar en buffers history para features online
        self.angle_history.append(angle)
        self.spin_times.append(now)
        self.velocity_history.append(inst_vel)
        self.jugadores_buffer.append(jugadores)
         # → buffers específicos de spin events
        self.spin_event_times.append(now)
        self.jugadores_history.append(jugadores)

        maxlen = self.vel_buffer.maxlen or MAX_SPIN_BUFFER
        self.angle_history    = self.angle_history[-maxlen:]
        self.spin_times       = self.spin_times[-maxlen:]
        self.velocity_history = self.velocity_history[-maxlen:]
        self.jugadores_buffer = self.jugadores_buffer[-maxlen:]

     
    def get_spin_stats(self) -> Tuple[float, str]:
        """
        Devuelve:
          - mediana de velocidades registradas (self.vel_buffer)
          - la dirección más frecuente (self.dir_buffer)
        Si no hay datos, retorna (0.0, "").
        """
        if len(self.vel_buffer) == 0:
            return 0.0, ""

        # mediana
        med_vel = float(np.median(list(self.vel_buffer)))
        # moda simple
        direction = max(set(self.dir_buffer), key=self.dir_buffer.count)
        return med_vel, direction
    def read_result(self, present_regions: List[str]) -> Tuple[Optional[int], int]:
        """
        Detecta:
          - el número ganador (reintentando hasta 3 veces)
          - el conteo de jugadores (mediana de 3 lecturas OCR)
        Devuelve siempre (numero, jugadores), donde numero puede ser None
        si falla la detección tras 3 intentos, y jugadores = 0 en caso de fallo.
        """
        # --- 1) Detección del número ganador con retry ---
        numero = None
        for intento in range(1, 4):
            numero = self.numero_detector.detectar_numero()
            if numero is not None:
                break
            print(f"[WARN] Intento {intento} para detectar número: fallido")
            time.sleep(0.1)

        if numero is None:
            print("[ERROR] No se pudo detectar el número ganador tras 3 intentos.")
            return None, 0

        # Guardar en historial de giros
        self.spin_nums.append(numero)

        # --- 2) Conteo de jugadores por OCR (mediana de 3 muestras) ---
        jugadores = 0
        regs_j = self.regions.get("jugadores", [])
        if regs_j:
            x, y, w, h = regs_j[0]["x"], regs_j[0]["y"], regs_j[0]["w"], regs_j[0]["h"]
            muestras = []
            for _ in range(3):
                try:
                    img = np.array(pyautogui.screenshot(region=(x, y, w, h)))
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                    gray = cv2.equalizeHist(gray)
                    _, thresh = cv2.threshold(
                        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                    )

                    # --- aquí suprimimos cualquier salida de Tesseract ---
                    import io, contextlib
                    with contextlib.redirect_stdout(io.StringIO()), \
                         contextlib.redirect_stderr(io.StringIO()):
                        txt = pytesseract.image_to_string(
                            thresh,
                            config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789 --quiet"
                        ).strip()

                    val = int(txt) if txt.isdigit() else 0
                except Exception:
                    val = 0

                muestras.append(val)
                time.sleep(0.05)

            jugadores = int(np.median(muestras))
        else:
            jugadores = 0

        return numero, jugadores

    def compute_gain(
        self,
        numero: Optional[int],
        categoria: str,
        fichas: int,
        valor_ficha: int = 500
    ) -> Tuple[bool, float]:
        """
        Calcula si la apuesta fue ganadora y el neto obtenido.

        Parámetros:
        - numero: Número ganador de la ruleta (1-36) o None si la lectura falló.
        - categoria: Categoría apostada ("rojo", "negro", "par", "impar", "1-18", "19-36" o "skip").
        - fichas: Número de fichas apostadas.
        - valor_ficha: Valor monetario de cada ficha (por defecto 500).

        Retorna:
        - tupla (ganaste: bool, neto: float), donde neto incluye el stake en caso de victoria
        (2x el stake al ganar, -1x al perder).
        """
        # 1) Filtrado de 'skip': nunca computar ganancia real
        if categoria == "skip":
            logging.debug(f"[GAIN] categoría 'skip' detectada: omitiendo cálculo.")
            return False, 0.0

        # 2) Validación de entrada
        if numero is None:
            logging.warning("[GAIN] compute_gain recibió numero=None, omitiendo cálculo.")
            return False, 0.0
        if categoria not in {"rojo", "negro", "par", "impar", "1-18", "19-36"}:
            logging.error(f"[GAIN] categoría inválida: {categoria}")
            return False, 0.0

        # 3) Determinación de atributos del número
        color = "rojo" if numero in self.ROJOS else "negro"
        paridad = "par" if numero % 2 == 0 else "impar"
        if 1 <= numero <= 18:
            rango = "1-18"
        else:
            rango = "19-36"

        # 4) Comparación de categoría y cálculo de neto
        ganaste = (categoria == color) or (categoria == paridad) or (categoria == rango)
        stake = valor_ficha * fichas
        payout_multiplier = 2 if ganaste else -1
        neto = stake * payout_multiplier

        # 5) Log detallado
        logging.debug(
        f"[GAIN] numero={numero}, categoria='{categoria}', fichas={fichas}, valor_ficha={valor_ficha} "
        f"→ ganaste={ganaste}, neto={neto} (mult={payout_multiplier})"
    )

        return ganaste, float(neto)



    def process_spin_cycle(self) -> None:
        coords = self.get_ruleta_roi()
        if coords is None:
            return

        self.accumulate_spin(coords)
        avg_vel, _ = self.get_spin_stats()
        numero, jugadores = self.read_result(self.regions)

        if avg_vel < LOW_VEL_THRESHOLD:
            self.low_vel_count += 1
            print(f"[WARN] Velocidad baja ({avg_vel:.1f}) [{self.low_vel_count}/{LOW_VEL_MAX_COUNT}]")
            if self.low_vel_count >= LOW_VEL_MAX_COUNT:
                pyautogui.hotkey("f5")
                time.sleep(2)
                self.low_vel_count = 0
        else:
            self.low_vel_count = 0

    def run_data_pipeline(
        self,
        raw_src: str,
        clean_csv: str,
        unified_csv: str = "data/unified_features.csv",
        lstm_csv: str = "data/lstm_input.csv",
        rl_csv: str = "data/rl_input.csv"
    ) -> None:
        cleaner = DataCleaner(raw_src=raw_src, clean_csv=clean_csv)
        cleaner.clean()

        df_clean = pd.read_csv(clean_csv, parse_dates=["fecha_hora"])
        fe = FeatureEngineerDeep(
            time_lag_max=cleaner.max_interval,
            accel_window=cleaner.accel_window,
            player_window=cleaner.player_window,
            strategy_window=cleaner.strategy_window
        )
        df_feats = fe.transform(df_clean)

        os.makedirs(os.path.dirname(unified_csv), exist_ok=True)
        df_feats.to_csv(unified_csv, index=False)
        df_feats.to_csv(lstm_csv, index=False)
        df_feats.to_csv(rl_csv, index=False)

        feat_dir = os.path.join("models", "rl")
        os.makedirs(feat_dir, exist_ok=True)
        feat_list = df_feats.columns.tolist()
        with open(os.path.join(feat_dir, "feature_list.json"), "w") as f:
            import json
            json.dump(feat_list, f)
        print(f"[DataCollector] Feature list guardada ({len(feat_list)} cols) en models/rl/feature_list.json")


    def get_payout(self) -> float:
        return 0.0
    def compute_online_features(self, timestamp: float = None) -> Dict[str, float]:
        """
        Calcula y retorna las features dinámicas y caóticas para el spin actual,
        validando umbrales mínimos y usando imputación basada en el último valor válido
        cuando no hay suficiente histórico.
        """
        import time
        import logging
        import numpy as np
        import pandas as pd

        # mejoras: usar constantes y utilitarios compartidos
        from wplay.utils.constants     import MIN_DT, MAX_DT, MIN_CHAOS_POINTS
        from wplay.utils.time_features import get_time_sin_cos
        from wplay.utils.chaos         import compute_hurst, compute_lyapunov, shannon_entropy

        # 1) Timestamp actual o proporcionado
        ts = timestamp if timestamp is not None else time.time()

        # 2) delta_time_norm: normaliza entre MIN_DT y MAX_DT
        if len(self.spin_times) >= 2:
            dt      = self.spin_times[-1] - self.spin_times[-2]
            dt_norm = min(1.0, max(0.0, (dt - MIN_DT) / (MAX_DT - MIN_DT)))
        else:
            dt_norm = getattr(self, 'dt_norm', 0.0)
            logging.debug("[compute_online_features] dt_norm imputado por falta de histórico")

        # 3) Hora y día de la semana usando utilitario común
        hour_sin, hour_cos, dow_sin, dow_cos = get_time_sin_cos(ts)

        # 4) Aceleración: diff de últimas self.accel_window velocidades
        if len(self.velocity_history) >= self.accel_window:
            v     = np.array(self.velocity_history[-self.accel_window:])
            t     = np.array(self.spin_times[-self.accel_window:])
            accel = np.diff(v) / np.diff(t)
            accel_mean = float(accel.mean())
            accel_std  = float(accel.std())
            # accel_skew
            accel_skew = float(pd.Series(accel).skew()) if len(accel) >= 3 else getattr(self, 'accel_skew', 0.0)
        else:
            accel_mean = getattr(self, 'accel_mean', 0.0)
            accel_std  = getattr(self, 'accel_std',  0.0)
            accel_skew = getattr(self, 'accel_skew', 0.0)
            logging.debug("[compute_online_features] accel imputado por falta de histórico")

        # 5) Estadística de jugadores con ventana self.player_window
        if len(self.jugadores_buffer) >= self.player_window:
            p             = np.array(self.jugadores_buffer[-self.player_window:])
            players_mean  = float(p.mean())
            players_std   = float(p.std())
            # players_skew
            players_skew  = float(pd.Series(p).skew()) if len(p) >= 3 else getattr(self, 'players_skew', 0.0)
        else:
            players_mean  = getattr(self, 'players_mean', 0.0)
            players_std   = getattr(self, 'players_std',  0.0)
            players_skew  = getattr(self, 'players_skew', 0.0)
            logging.debug("[compute_online_features] players imputado por falta de histórico")

        # 6) Indicadores de caos en últimos self.chaos_window números
        window = list(self.spin_nums)[-self.chaos_window:]
        if len(window) >= MIN_CHAOS_POINTS:
            try:
                hurst = compute_hurst(window)
                lyap  = compute_lyapunov(window)
                ent   = shannon_entropy(window)
            except Exception as e:
                logging.warning(f"[compute_online_features] error caos: {e}")
                hurst    = getattr(self, 'hurst',    0.0)
                lyap     = getattr(self, 'lyapunov', 0.0)
                ent      = getattr(self, 'entropy',  0.0)
        else:
            hurst    = getattr(self, 'hurst',    0.0)
            lyap     = getattr(self, 'lyapunov', 0.0)
            ent      = getattr(self, 'entropy',  0.0)
            logging.debug(f"[compute_online_features] caos imputado ({len(window)}/{MIN_CHAOS_POINTS})")

        # 7) Dirección del spin: asumir self.last_direction definido en accumulate_spin
        dir_bin = 1 if getattr(self, 'last_direction', '') == "horario" else 0

        # 8) Guardar valores para futuras imputaciones
        for name, val in [
            ('dt_norm', dt_norm),
            ('accel_mean', accel_mean), ('accel_std', accel_std), ('accel_skew', accel_skew),
            ('players_mean', players_mean), ('players_std', players_std), ('players_skew', players_skew),
            ('hurst', hurst), ('lyapunov', lyap), ('entropy', ent),
            ('dir_bin', dir_bin)
        ]:
            setattr(self, name, val)

        # 9) Log inicial cuando hay datos reales suficientes
        if len(self.spin_times) == 2:
            logging.info("[compute_online_features] Primer cálculo con datos reales:")
            logging.info(f"   dt_norm={dt_norm:.3f}, accel_mean={accel_mean:.3f}, players_mean={players_mean:.3f}")
            logging.info(f"   hurst={hurst:.3f}, lyapunov={lyap:.3f}, entropy={ent:.3f}")

        # 10) Retornar diccionario de features ampliado
        return {
            "delta_time_norm": dt_norm,
            "hour_sin":        hour_sin,
            "hour_cos":        hour_cos,
            "dow_sin":         dow_sin,
            "dow_cos":         dow_cos,
            "accel_mean":      accel_mean,
            "accel_std":       accel_std,
            "accel_skew":      accel_skew,
            "players_mean":    players_mean,
            "players_std":     players_std,
            "players_skew":    players_skew,
            "hurst":           hurst,
            "lyapunov":        lyap,
            "entropy":         ent,
            "dir_bin":         dir_bin
        }
