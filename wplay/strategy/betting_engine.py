import os
import time
import numpy as np
import pandas as pd
import pyautogui
import threading
import json
import ast
import logging
from typing import List
from wplay import trainer
from wplay.capture.jugadores_detector import JugadoresDetector
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from wplay.auth.login import paste_text
from wplay.capture.data_collector import DataCollector
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager
from wplay.data.db_reader import DBReader
from wplay.data.feature_engineer_deep import FeatureEngineerDeep
from wplay.data.model_trainer import ModelTrainer
from wplay.data.transformer_trainer import TransformerTrainer
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.constants import MONTO_MAX
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.training.rl_trainer import RLTrainer
from sklearn.ensemble import RandomForestClassifier

class BettingEngine:

    def __init__(
        self,
        region_finder,
        data_collector,
        stats_helper,
        db_manager,
        place_bet_fn,
        strategy_manager: Optional[StrategyManagerDL] = None,
        login_handler=None,
        login_url: str = None,
        cooldown: float = 12.0,
        wager_value: int = 500,
    ):
        """
        Inicialización de BettingEngine:
         - Asigna dependencias.
         - Inicializa estado de balance y riesgo.
         - Configura pipeline offline si no hay strategy_manager pre-entrenado.
         - Prepara detección paralela de regiones.
        """
        # Dependencias y parámetros
        self.region_finder    = region_finder
        self.data_collector   = data_collector
        self.stats_helper     = stats_helper
        self.db_manager       = db_manager
        self.place_bet        = place_bet_fn
        self.strategy_manager = strategy_manager
        # Si recibimos un StrategyManagerDL pre-entrenado, extraemos su hypernet
        if self.strategy_manager is not None:
            self.hypernet = self.strategy_manager.hypernet

        self.login_handler       = login_handler
        self.login_url           = login_url
        self.cooldown            = cooldown
        self.wager_value         = wager_value
        self.reactivate_threshold = wager_value
        self.offline_mode        = (strategy_manager is None)

        # Estado de balance y riesgo
        self.saldo               = 0.0
        self.balance_current     = 0.0
        self.balance_start_day   = 0.0
        self.peak_balance        = 0.0
        self.stop_loss_daily     = float('inf')
        self.spin_nums           = []
        self.paused              = False
        self._reset_daily()

        self.max_drawdown          = 0.70   # 70%
        self.gain_reset_threshold  = 0.10   # 10% recuperación
        self.max_consecutive_skips = 5

        # Historia para RL
        self.balance_history      = []
        self.recent_returns       = []
        self.velocity_history     = []
        self.color_history        = []
        self.spins_since_last_win = 0

        # Flags de apuesta y skip-classifier
        self.apuesta_en_curso   = False
        self.last_cat           = None
        self.last_amt           = 0
        self.last_strat         = None
        self.skip_clf           = RandomForestClassifier(n_estimators=50, random_state=0)
        self.skip_reward_scale  = 1.0
        self._skip_counter      = 0

        # Datos del último giro
        self.giro_data = {"velocity": 0.0, "direction": "", "jugadores": 0}

        # Rutas de datos y modelos
        DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
        CLEAN_CSV   = os.path.join(DATA_DIR, "clean_records.csv")
        LSTM_CSV    = os.path.join(DATA_DIR, "lstm_input.csv")
        RL_CSV      = os.path.join(DATA_DIR, "rl_input.csv")
        MODELS_DIR  = os.path.join(os.path.dirname(__file__), "models")
        LSTM_MODEL  = os.path.join(MODELS_DIR, "lstm.h5")
        TRANS_MODEL = os.path.join(MODELS_DIR, "transformer.h5")
        DQN_MODEL   = os.path.join(MODELS_DIR, "dqn.h5")
        PPO_MODEL   = os.path.join(MODELS_DIR, "ppo.h5")
        self._bad_speed_count = 0

        if self.strategy_manager is not None:
            print("[INIT] StrategyManager preentrenado recibido → omitiendo pipeline offline.")
            # Asegurarnos de que el meta-selector esté construido
            self.strategy_manager._rebuild_meta()
            self.feature_engineer_rl = FeatureEngineerDeep(
                clean_csv=CLEAN_CSV,
                lstm_csv=LSTM_CSV,
                rl_csv=RL_CSV,
                window=50,
                window_rl=10,
            )
        else:
            print("[INIT] Ejecutando pipeline offline completo...")
            os.makedirs(os.path.dirname(CLEAN_CSV), exist_ok=True)
            os.makedirs(os.path.dirname(LSTM_MODEL), exist_ok=True)

            # 1) Limpieza de datos
            print("🔄 DataCleaner: limpiando registros…")
            df_raw = DBReader().load_rounds()
            df_raw.to_csv(CLEAN_CSV, index=False)
            print(f"✔️ CSV limpio guardado en '{CLEAN_CSV}'")

            # 2) Ingeniería de features
            print("🔄 FeatureEngineerDeep: generando características…")
            fe = FeatureEngineerDeep(
                clean_csv=CLEAN_CSV,
                lstm_csv=LSTM_CSV,
                rl_csv=RL_CSV,
                window=50,
                window_rl=10,
            )
            fe.transform()
            self.feature_engineer_rl = fe
            print(f"✔️ Características RL guardadas en '{RL_CSV}'")

            # 3) Entrenar LSTM
            print("🔄 ModelTrainer: entrenando LSTM…")
            if os.path.exists(LSTM_MODEL):
                os.remove(LSTM_MODEL)
            ModelTrainer(
                feat_csv=LSTM_CSV,
                model_type='lstm',
                window=50,
                test_size=0.2,
                learning_rate=1e-3,
                epochs=20,
                dropout_rate=0.2
            ).train_model(output_model_path=LSTM_MODEL)
            print(f"✔️ LSTM guardado en '{LSTM_MODEL}'")

            # 4) Entrenar Transformer
            print("🔄 TransformerTrainer: entrenando Transformer…")
            try:
                TransformerTrainer(
                    feat_csv=LSTM_CSV,
                    model_type='transformer',
                    window=11,
                    test_size=0.2,
                    learning_rate=1e-4,
                    epochs=10,
                    dropout_rate=0.2
                ).train_model(output_model_path=TRANS_MODEL)
                print(f"✔️ Transformer guardado en '{TRANS_MODEL}'")
            except Exception as e:
                print("[WARN] TransformerTrainer falló:", e)

            # 5) Pre-entrenamiento offline DQN/PPO
            print("🔄 Preentrenando agentes DQN/PPO offline…")
            cols = pd.read_csv(RL_CSV, nrows=1).columns
            state_dim  = sum(
                1 for c in cols
                if c not in ("action", "reward", "done") and not c.startswith("next_")
            )
            action_dim = len(StrategyManagerDL.CATEGORIES) * (self.wager_value + 1)
            dqn_agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
            ppo_agent = PPOAgent(state_dim=state_dim, action_dim=action_dim)
            rl_trainer = RLTrainer(
                clean_csv_path = CLEAN_CSV,
                rl_csv_path    = RL_CSV,
                strategy_manager=None,
                dqn_agent_cls  = DQNAgent,
                ppo_agent_cls  = PPOAgent,
                dqn_kwargs     = {},
                ppo_kwargs     = {},
                buffer_size    = 10000,
                batch_size     = 64,
                train_interval = 50,
                gamma          = 0.99,
                save_dir       = MODELS_DIR
            )
            rl_trainer.pretrain_offline(epochs=5)
            print("✔️ Preentrenamiento RL offline completado.")

            # 6) Construir StrategyManagerDL con hypernet y hp del rl_trainer
            self.strategy_manager = StrategyManagerDL(
                lstm_path             = LSTM_MODEL,
                rl_agent_dqn          = dqn_agent,
                rl_agent_ppo          = ppo_agent,
                rl_trainer            = rl_trainer,
                hypernet              = rl_trainer.hypernet,
                hp                    = rl_trainer.hp,
                external_classifier   = None,
                window_lstm           = 50,
                window_rl             = 10,
                confidence_threshold  = 0.1,
                bet_scale_factor      = 1.0,
                wager_value           = self.wager_value,
            )
            # Extraemos la hypernet para usos posteriores
            self.hypernet = self.strategy_manager.hypernet
            print("✅ StrategyManagerDL inicializado correctamente.")

        # Configuración de detección paralela de regiones
        self._det_lock      = threading.Lock()
        self._det_condition = threading.Condition(self._det_lock)
        self._latest_det    = {'regions': [], 'timestamp': time.time()}
        self._stop_detector = threading.Event()

        threading.Thread(
            target=self._detection_loop,
            name="DetectorThread",
            daemon=True
        ).start()


    def _build_state_vector(
            self,
            registro: dict,
            saldo_history: List[float],
            vel_history: List[float],
            color_history: List[str],
            win_times: List[bool]
        ) -> np.ndarray:
            """
            Wrapper para reutilizar el _build_state_vector de StrategyManagerDL.
            """
            return self.strategy_manager._build_state_vector(
                registro, saldo_history, vel_history, color_history, win_times
            )

    def _detection_loop(self):
        """
        Hilo de detección paralelo:
        - Llama continuamente a region_finder.find_all_regions()
        - Captura timestamp justo tras la llamada
        - Notifica al hilo principal vía self._det_condition
        - Mide y registra el tiempo invertido en la detección
        - Se detiene limpiamente si self._stop_detector se setea
        """
        try:
            while not self._stop_detector.is_set():
                # 1) Medir tiempo de find_all_regions()
                t0_find = time.perf_counter()
                regions = self.region_finder.find_all_regions()
                dt_find = time.perf_counter() - t0_find
             #   logging.debug(f"[TIMINGS] find_all_regions() tomó {dt_find:.4f}s")

                # 2) Timestamp real de la detección
                ts = time.time()

                # 3) Bajo lock, guardar resultado y notificar a run()
                with self._det_condition:
                    self._latest_det['regions']   = regions
                    self._latest_det['timestamp'] = ts
                    self._det_condition.notify_all()

                # 4) Pequeña pausa para evitar busy‑loop
                time.sleep(0.01)

        except Exception as e:
            # Si ocurre un error inesperado, registrarlo y detener el hilo
            print(f"[ERROR] en _detection_loop: {e!r}")
            self._stop_detector.set()


    def monitor(self):
        if self.offline_mode:
            return self.backtest()

        # Loop real-time...
        # Mostrar métricas en tiempo real
        self.report_metrics()
        # Resto de monitor()...
    def backtest(self):
        records = self.db_manager.load_all()
        balances = [r['saldo'] for r in records]
        returns = np.diff(balances) / balances[:-1]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        max_dd = max((max(balances[:i]) - balances[i]) / max(balances[:i]) for i in range(len(balances)))
        win_rate = sum(r['ganancia']>0 for r in records)/len(records)
        print(f"Backtest → Sharpe: {sharpe:.2f}, MaxDD: {max_dd:.2%}, Win-rate: {win_rate:.2%}")
        return {'sharpe':sharpe, 'max_dd':max_dd, 'win_rate':win_rate}
    def report_metrics(self):
        # Llamar vía python_user_visible si queremos gráficas
        print(f"ε={self.strategy_manager.dqn_agent.epsilon:.3f} | Q_max={self.strategy_manager.last_q_max:.2f} | V_max={self.strategy_manager.last_v_max:.2f}")

    def _reset_daily(self):
        self.balance_start_day = self.balance_current
        self.peak_balance      = self.balance_current

    def _update_balance(self, gain: float):
        self.balance_current += gain
        self.peak_balance = max(self.peak_balance, self.balance_current)
        # si ganamos y estamos fuera de riesgo, resetear flag
        if gain > 0 and getattr(self, "_risk_skip_once", False):
            self._risk_skip_once = False

    def _check_risk(self) -> bool:
        """
        Comprueba el drawdown y aplica:
        1) Reducción de fichas si supera limit_drawdown_threshold (pero < max_drawdown)
        2) Forzado de SKIP si supera max_drawdown
        3) Reset de peak_balance tras recuperar gain_reset_threshold
        4) Lógica anti‐lock: tras max_consecutive_skips skips consecutivos, reinicia TODO y permite apuesta
        """
        # --- Anti‐lock guard: si acabamos de forzar una apuesta, limpiamos estado y salimos limpios ---
        if getattr(self, "_just_forced_reset", False):
            self._just_forced_reset = False
            # Reiniciamos contadores y límites
            self.skip_consecutive = 0
            self.current_max_fichas = None
            # Volvemos a tomar el pico de balance actual como referencia
            self.peak_balance = self.balance_current
            return False

        # Inicializaciones
        self.skip_consecutive = getattr(self, "skip_consecutive", 0)
        self.max_consecutive_skips = getattr(self, "max_consecutive_skips", 5)
        self.limit_drawdown_threshold = getattr(self, "limit_drawdown_threshold", 0.80)
        self.max_fichas_under_drawdown = getattr(self, "max_fichas_under_drawdown", 1)
        gain_reset_thresh = getattr(self, "gain_reset_threshold", 0.20)

        # 1) Cálculo de drawdown
        if self.peak_balance > 0:
            drawdown = max(0.0, (self.peak_balance - self.balance_current) / self.peak_balance)
        else:
            drawdown = 0.0
        logging.debug(f"[RISK] drawdown={drawdown*100:.1f}%, "
                      f"limit_thresh={self.limit_drawdown_threshold*100:.1f}%, "
                      f"max_drawdown={self.max_drawdown*100:.1f}%")

        # 2) Resetear peak_balance si hubo recuperación suficiente
        if self.balance_current - self.peak_balance >= self.peak_balance * gain_reset_thresh:
            logging.info(f"[RISK] Recuperación ≥{gain_reset_thresh*100:.0f}% del pico → reset peak_balance")
            self.peak_balance = self.balance_current
            drawdown = 0.0

        # 3) Reducción de fichas intermedia
        if self.limit_drawdown_threshold <= drawdown < self.max_drawdown:
            logging.warning(
                f"[RISK] drawdown={drawdown*100:.1f}% ≥ "
                f"{self.limit_drawdown_threshold*100:.1f}% → limitando fichas a "
                f"{self.max_fichas_under_drawdown}"
            )
            self.current_max_fichas = self.max_fichas_under_drawdown
        else:
            self.current_max_fichas = None

        # 4) Skip forzado si supera el umbral máximo
        if drawdown >= self.max_drawdown:
            self.skip_consecutive += 1
            logging.warning(
                f"⚠ Drawdown {drawdown*100:.1f}% ≥ {self.max_drawdown*100:.1f}% "
                f"(skip #{self.skip_consecutive}/{self.max_consecutive_skips}) → Forzando SKIP"
            )

            # Anti‐lock: tras X skips consecutivos, reiniciamos TODO y permitimos apuesta
            if self.skip_consecutive >= self.max_consecutive_skips:
                logging.info(
                    f"[RISK] {self.skip_consecutive} skips consecutivos → "
                    "reiniciando estado de riesgo y permitiendo apuesta"
                )
                # Marcar que acabamos de resetear y debemos salir limpios en la próxima llamada
                self._just_forced_reset = True
                # Reiniciar aquí también para este mismo turno
                self.skip_consecutive = 0
                self.current_max_fichas = None
                self.peak_balance = self.balance_current
                return False  # permitimos UNA apuesta antes de volver a chequear riesgo

            return True  # seguimos en skip obligatorio

        # 5) Si todo ok, reset contador de skips
        self.skip_consecutive = 0
        return False



    def _ajustar_umbrales(self):
        """
        Ajusta dinámicamente los parámetros de riesgo y skip según las últimas N rondas.
        """
        import json, logging

        N = 20
        raw = self.db_manager.load_all()[-N:]
        regs = []
        for r in raw:
            if isinstance(r, dict):
                regs.append(r)
            else:
                try:
                    regs.append(json.loads(r))
                except:
                    continue
        if not regs:
            return

        ganancias = [r.get("ganancia", 0.0) for r in regs]
        rewards   = [r.get("reward", 0.0)  for r in regs]
        winrate   = sum(g > 0 for g in ganancias) / len(ganancias)
        avg_gain  = sum(ganancias) / len(ganancias)
        avg_reward= sum(rewards)  / len(rewards)

        # Ajuste de max_drawdown
        if winrate > 0.6:
            self.max_drawdown = min(0.9, self.max_drawdown + 0.05)
        elif winrate < 0.4:
            self.max_drawdown = max(0.3, self.max_drawdown - 0.05)

        # Ajuste de skip_reward_scale
        if avg_reward > self.wager_value * 0.5:
            self.skip_reward_scale = min(2.0, self.skip_reward_scale + 0.1)
        elif avg_reward < -self.wager_value * 0.5:
            self.skip_reward_scale = max(0.5, self.skip_reward_scale - 0.1)

        # Ajuste de reactivate_threshold
        base = self.wager_value
        if avg_gain > base:
            # si venimos ganando, endurecemos umbral para skips
            self.reactivate_threshold = min(self.reactivate_threshold * 1.1, 3 * base)
        else:
            # si venimos perdiendo, bajamos umbral para reactivar apuesta
            self.reactivate_threshold = max(base * 0.5, self.reactivate_threshold * 0.9)

        logging.info(f"[AJUSTE] winrate={winrate:.2%}, avg_gain={avg_gain:.2f}, "
                     f"avg_reward={avg_reward:.2f} → "
                     f"max_dd={self.max_drawdown:.2f}, skip_scale={self.skip_reward_scale:.2f}, "
                     f"react_th={self.reactivate_threshold:.2f}")



    def relogin(self):
        """
        Tras 4 min sin detección de número:
        1) Recarga la página y maximiza la ventana.
        2) Si tras X intentos seguimos sin “ruleta”, entonces:
           a) cerramos pop-ups,
           b) reabrimos Chrome y relogueamos,
           c) seleccionamos el juego de nuevo.
        """
        from wplay.auth.login import paste_text

        def wait_for_region(name: str, timeout: int = 10) -> bool:
            start = time.time()
            while time.time() - start < timeout:
                if name in self.region_finder.find_all_regions():
                    return True
                time.sleep(0.5)
            return False

        print("[ENGINE][WARN] 4 min sin detección → intentando limpieza de sesión…")

        # 1) Intentar recargar en la misma ventana
        try:
            import pyautogui
            print("  → Recargando página (F5)…")
            pyautogui.hotkey("f5")
            time.sleep(3)
            print("  → Maximizar ventana…")
            wins = pyautogui.getWindowsWithTitle("Chrome")
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                    time.sleep(0.5)
                win.moveTo(0, 0)
                time.sleep(0.2)
                win.maximize()
                time.sleep(0.5)
        except Exception as e:
            print(f"  [WARN] Error recargando/maximizando: {e!r}")

        # 2) Verifico si ya veo la ruleta
        if wait_for_region("ruleta", timeout=15):
            print("[ENGINE] Ruleta visible tras recarga. Continuamos.")
        else:
            # Antes de abrir Chrome de cero, cerramos cualquier pop-up residual
            print("[ENGINE][WARN] No apareció 'ruleta'. Cerrando pop-ups antes de relogin…")
            for i in range(5):
                regs = self.region_finder.find_all_regions()
                if "cerrar" in regs:
                    print(f"  → Pop-up: click 'cerrar' (intento {i+1})")
                    self.region_finder.click_region("cerrar")
                    time.sleep(0.5)
                else:
                    break
            
            print("[ENGINE][WARN] Reabrimos Chrome…")
            url = self.login_url or getattr(self.login_handler, "login_url", None) or "https://wplay.co"
            try:
                self.login_handler.open_chrome(url)
                time.sleep(5)
                success = self.login_handler.login_or_continue(timeout=60)
                if not success:
                    print("[ENGINE][ERROR] login_or_continue falló en relogin().")
                    return False
            except Exception as e:
                print(f"[ENGINE][ERROR] No pudo reabrir Chrome: {e!r}")
                return False

            # tras login completo, seleccionar juego
            for attempt in range(3):
                regs = self.region_finder.find_all_regions()
                choices = [r for r in regs if r.startswith("clic")]
                if choices:
                    print(f"  → click '{choices[0]}' para seleccionar juego")
                    self.region_finder.click_region(choices[0])
                    break
                time.sleep(1)

        # 3) Resetear buffers
        print("[ENGINE] Reset buffers de ruleta y datos de spin.")
        self.data_collector.reset_spin_buffer()
        self.spin_nums.clear()
        print("[ENGINE] Relogin completado.")
        return True
    
    def run(self):
        import time
        import datetime
        import pyautogui
        import numpy as np
        import logging
        from logging import StreamHandler, DEBUG
        from wplay.strategy.betting_engine import JugadoresDetector

        # ─── Configuración robusta del logger ─────────────────────────────────
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
        handler = StreamHandler()
        handler.setLevel(DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        root.addHandler(handler)
        root.setLevel(DEBUG)

        logging.info("🎲 Iniciando BettingEngine…")

        # --- Inicialización de balances y variables ---
        self.saldo = 10000.0
        self._update_wager_value()
        self.balance_current   = self.saldo
        self.balance_start_day = self.saldo
        self.peak_balance      = self.saldo

        last_bet_time      = time.time() - self.cooldown
        last_apostar_time  = time.time()
        self.apuesta_en_curso = False

        relogin_fail_count = 0
        RELOGIN_MAX_FAILS  = 3
        RELOGIN_PAUSE_SEC  = 10 * 60

        prev_has_apostar    = False
        self._prev_has_giro = False

        muestreo_giro      = False
        muestreo_start     = None
        muestreo_duracion  = 15.0  # segundos

        self._fallback_done   = True
        self._fallback_coords = None

        detector = JugadoresDetector()

        try:
            while True:
                cycle_start = time.perf_counter()
                now = time.time()

                if (not self._fallback_done) and (now - last_apostar_time) >= muestreo_duracion:
                    if self._fallback_coords:
                        self.data_collector.accumulate_spin(self._fallback_coords)
                        vel_fb, dir_fb = self.data_collector.get_spin_stats()
                        jug_fb = detector.detectar_jugadores() or 0
                        self.giro_data.update({
                            "velocity":  vel_fb,
                            "direction": dir_fb,
                            "jugadores": jug_fb
                        })
                        logging.debug(f"[GIRO·FB] Fallback tras {muestreo_duracion:.0f}s → "
                                      f"vel={vel_fb:.2f}, dir={dir_fb}, jugadores={jug_fb}")
                    self._fallback_done = True

                with self._det_condition:
                    regions = list(self._latest_det['regions'])
                    det_ts  = self._latest_det['timestamp']

                if "giro" in regions:
                    prev_has_apostar = False

                if "clic" in regions:
                    self.region_finder.click_region("clic")
                    time.sleep(0.2)
                    continue

                has_giro = "giro" in regions

                if has_giro and not self._prev_has_giro and not muestreo_giro:
                    muestreo_start = now
                    logging.debug(f"[DEBUG-GIRO] 'giro' detectada en t={muestreo_start:.3f}")
                    muestreo_giro  = True
                    self._fallback_done = True

                    self.data_collector.reset_spin_buffer()
                    coords = self.data_collector.get_ruleta_roi()
                    jugadores_inicio = detector.detectar_jugadores() or 0
                    logging.debug(f"[GIRO] jugadores_inicio={jugadores_inicio}, duracion={muestreo_duracion}s")

                if muestreo_giro and muestreo_start and (now - muestreo_start) < muestreo_duracion:
                    if "apostar" in regions:
                        logging.debug("[GIRO] Abortado por 'apostar'")
                        muestreo_giro  = False
                        muestreo_start = None
                    else:
                        self.data_collector.accumulate_spin(coords)
                        time.sleep(1.0 / self.data_collector.ruleta_detector.capture_fps)
                        self._prev_has_giro = has_giro
                        continue

                if muestreo_giro and muestreo_start and (now - muestreo_start) >= muestreo_duracion:
                    vel, direc = self.data_collector.get_spin_stats()
                    jug_final = detector.detectar_jugadores() or jugadores_inicio
                    self.giro_data.update({
                        "velocity":  vel,
                        "direction": direc,
                        "jugadores": jug_final
                    })

                    # ─────────────── Nuevo bloque de refresco ───────────────
                    vel_actual = self.giro_data["velocity"]
                    if vel_actual < 40.0 or vel_actual > 70.0:
                        self._bad_speed_count += 1
                        logging.warning(f"[REFRESH] Velocidad fuera de rango ({vel_actual:.2f}) → intento {self._bad_speed_count}/3")
                        if self._bad_speed_count < 3:
                            # si tu region_finder soporta simplemente pulsar F5:
                            try:
                                import pyautogui
                                pyautogui.press("f5")
                                self._bad_speed_count = 0
                            except Exception as e:
                                logging.error(f"[REFRESH] Falló pulsar F5: {e}")
                        
                    else:
                        self._bad_speed_count = 0
                        # ───────────────────────────────────────────────────────────

                    logging.debug(f"[GIRO] Fin muestreo → vel={vel:.2f}, dir={direc}, jugadores={jug_final}")
                    muestreo_giro  = False
                    muestreo_start = None

                self._prev_has_giro = has_giro

                if now - last_bet_time < self.cooldown:
                    time.sleep(0.2)
                    continue

                if now - last_apostar_time > 5 * 60:
                    logging.warning("[ENGINE] 5 min sin 'apostar' → relogin")
                    if not self.relogin():
                        relogin_fail_count += 1
                        logging.warning(f"[ENGINE] relogin fallido ({relogin_fail_count}/{RELOGIN_MAX_FAILS})")
                        if relogin_fail_count >= RELOGIN_MAX_FAILS:
                            logging.warning(f"[ENGINE] {RELOGIN_MAX_FAILS} relogins fallidos → pausa {RELOGIN_PAUSE_SEC/60:.0f}min")
                            time.sleep(RELOGIN_PAUSE_SEC)
                            relogin_fail_count = 0
                    else:
                        relogin_fail_count = 0
                    self.data_collector.reset_spin_buffer()
                    last_apostar_time = now
                    last_bet_time = 0.0
                    time.sleep(1)
                    continue

                with self._det_condition:
                    self._det_condition.wait_for(lambda: "apostar" in self._latest_det['regions'], timeout=2.0)
                    regions = list(self._latest_det['regions'])
                    det_ts  = self._latest_det['timestamp']
                has_apostar = "apostar" in regions

                if has_apostar and not prev_has_apostar:
                    last_apostar_time    = det_ts
                    self._fallback_done   = False
                    self._fallback_coords = self.data_collector.get_ruleta_roi()

                    numero, jugadores = self.data_collector.read_result(regions)
                    logging.info(f"[APOSTAR] ts={det_ts:.3f}, número raw='{numero}'")

                    if numero is None:
                        self.data_collector.reset_spin_buffer()
                        prev_has_apostar = True
                        time.sleep(self.cooldown)
                        continue

                    # ✅ FIX: Agregar número al historial
                    self.spin_nums.append(numero)

                    registro = self._procesar_logica_y_apostar(regions, numero, jugadores, det_ts)

                    self.data_collector.reset_spin_buffer()
                    last_bet_time    = time.time()
                    prev_has_apostar = True

                    total = len(self.db_manager.load_all())
                    if total and total % 100 == 0:
                        self.train_skip_classifier()
                    if total and total % 1000 == 0 and hasattr(self.strategy_manager, "retrain_offline"):
                        self.strategy_manager.retrain_offline()
                    if hasattr(self, "train_agents"):
                        self.train_agents()

                    continue

                prev_has_apostar = has_apostar

                time.sleep(0.05)

        except KeyboardInterrupt:
            self._stop_detector.set()
            logging.info("[INFO] BettingEngine detenido por usuario.")



    def train_skip_classifier(self):
        import time, logging
        import numpy as np
        import pandas as pd
        from wplay.utils.chaos import compute_hurst, compute_lyapunov, shannon_entropy

        t0 = time.perf_counter()
        logging.info("[SKIP] Entrenando skip-classifier…")

        # 1) Cargo todos los registros y paso a DataFrame
        registros = self.db_manager.load_all()
        df = pd.DataFrame(registros)

        # 1.1) Si no hay registros, abortar
        if df.empty:
            logging.warning("[SKIP] No hay registros para entrenar.")
            return

        # 2) Defino las features base
        feats = [
            "delta_time_norm", "hour_sin", "hour_cos",
            "dow_sin", "dow_cos", "accel_mean", "accel_std",
            "players_mean", "players_std",
            "hurst", "lyapunov", "entropy"
        ]

        # 3) Aseguro que existan esas columnas
        for f in feats:
            if f not in df.columns:
                df[f] = 0.0

        # 4) Calculo chaos indicators sobre reward_history actual
        rewards_hist = np.array(self.strategy_manager.meta.reward_history) \
                       if self.strategy_manager.meta.reward_history else np.array([0.0])
        df["hurst"]    = compute_hurst(rewards_hist)
        df["lyapunov"] = compute_lyapunov(rewards_hist)
        df["entropy"]  = shannon_entropy(rewards_hist)

        # 5) Construyo X e y
        X = df[feats].fillna(0.0).values
        y = (df.get("strategy", "") == "skip").astype(int).values

        # 6) Entreno el clasificador
        try:
            self.skip_clf.fit(X, y)
            logging.info(f"[SKIP] Clasificador entrenado en {time.perf_counter()-t0:.2f}s")
        except Exception as e:
            logging.error(f"[SKIP] Error entrenando skip-classifier: {e!r}")

    def _procesar_logica_y_apostar(self, regions, numero, _ignored, det_ts):
        import datetime, time, logging, numpy as np, json

        t0 = time.perf_counter()
        logging.info("[PHASE] Inicio apuesta+registro")

        # — 0) Resultado apuesta anterior —
        if self.apuesta_en_curso and self.last_cat is not None:
            stake = self.last_amt * self.wager_value
            try:
                win, gain = self.data_collector.compute_gain(
                    numero, self.last_cat, self.last_amt, self.wager_value
                )
                if not win:
                    gain = -stake
            except Exception as e:
                logging.warning(f"[PHASE 0] compute_gain falló: {e}")
                win, gain = False, 0.0
        else:
            win, gain = False, 0.0
        logging.debug(f"[PHASE 0] win={win}, gain={gain:.2f}")

        # — 1) Features online —
        try:
            feats = self.data_collector.compute_online_features(det_ts)
        except Exception as e:
            logging.error(f"[PHASE 1] compute_online_features error: {e}")
            feats = {}
        logging.debug(f"[PHASE 1] feats extraídos: {feats.keys()}")

        # — 1.1) Historial para drawdown/racha —
        raw = self.db_manager.load_all()[-self.strategy_manager.window_rl:]
        registros_pasados = []
        for r in raw:
            if isinstance(r, dict):
                registros_pasados.append(r)
            else:
                try:
                    registros_pasados.append(json.loads(r))
                except:
                    continue

        if registros_pasados:
            outcomes    = [r.get("ganancia", 0.0) for r in registros_pasados]
            losses      = [g <= 0 for g in outcomes]
            loss_streak = 0
            for bad in reversed(losses):
                if bad:
                    loss_streak += 1
                else:
                    break
            winrate = sum(not l for l in losses) / len(losses)
            balances = [r.get("saldo", self.balance_current) for r in registros_pasados]
        else:
            loss_streak, winrate = 0, 0.0
            balances = [self.balance_current]

        peak     = max(balances)
        drawdown = max(0.0, (peak - self.balance_current) / (peak or 1))
        logging.debug(f"[PHASE 1.1] loss_streak={loss_streak}, winrate={winrate:.2%}, drawdown={drawdown:.2%}")

        # Ajuste dinámico de ε
        if loss_streak >= 3:
            old_eps = self.strategy_manager.epsilon
            self.strategy_manager.epsilon = min(1.0, old_eps + 0.1)
            logging.info(f"[EPSILON↑] ε {old_eps:.2f} → {self.strategy_manager.epsilon:.2f}")
        elif loss_streak == 0 and drawdown < 0.2 * self.max_drawdown:
            old_eps = self.strategy_manager.epsilon
            self.strategy_manager.epsilon = max(0.01, old_eps * 0.9)
            logging.info(f"[EPSILON↓] ε {old_eps:.2f} → {self.strategy_manager.epsilon:.2f}")

        # — 2) Registro base —
        registro = {
            "fecha_hora": datetime.datetime.fromtimestamp(det_ts).strftime("%Y-%m-%d %H:%M:%S"),
            "numero": numero,
            "jugadores_presentes": self.giro_data["jugadores"],
            "velocity": self.giro_data["velocity"],
            "direction": self.giro_data["direction"],
            "numero_hist": self.spin_nums[-self.strategy_manager.window_rl:],
            "drawdown": drawdown,
            "loss_streak": loss_streak,
            "recent_winrate": winrate,
            **feats
        }
        logging.debug(f"[PHASE 2] registro base: {registro}")

        # — 2.1) Balance si hubo apuesta —
        if self.apuesta_en_curso:
            stake = self.last_amt * self.wager_value
            net_gain = gain if gain <= 0 else gain - stake
            old_bal = self.balance_current
            self._update_balance(net_gain)
            registro.update({
                "ganancia": net_gain,
                "saldo_anterior": old_bal,
                "saldo": self.balance_current,
                "strategy": self.last_strat,
                "opcion_apuesta": self.last_cat,
                "fichas": self.last_amt,
                "monto": stake
            })
            logging.debug(f"[BALANCE] Antes={old_bal:.2f}, Stake={stake:.2f}, NetGain={net_gain:.2f}, Después={self.balance_current:.2f}")
        else:
            registro.update({
                "ganancia": 0.0,
                "saldo_anterior": self.balance_current,
                "saldo": self.balance_current,
                "strategy": "skip",
                "opcion_apuesta": None,
                "fichas": 0,
                "monto": 0
            })

        # — 3) Reward shaping —
        if not self.apuesta_en_curso:
            if drawdown <= self.max_drawdown * 0.5 and loss_streak == 0:
                reward = 0.5
            elif feats.get("entropy", 0.0) > 0.95 and loss_streak >= 3:
                reward = 0.1
            elif drawdown >= self.max_drawdown * 0.8:
                reward = 0.2
            else:
                reward = 0.0
        else:
            reward = gain if (gain > 0 or loss_streak < 4) else -1.0
        registro["reward"] = reward
        logging.debug(f"[PHASE 3] reward={reward:.4f}")

        # — 4) Guardar registro y ajustar meta —
        self.strategy_manager.add_record(registro)
        try:
            self.db_manager.guardar_registro(registro)
            logging.debug("[DB] Registro guardado correctamente")
            self._ajustar_umbrales()
        except Exception as e:
            logging.error(f"[PHASE 4] Error guardando en BD: {e}")

      # ── PHASE 5: preparar estado y llamar a select() ──
        self.strategy_manager.current_number = numero

        # 5.1) Generar state_full y recortar para DQN
        state_full = self.strategy_manager._build_state_vector(
            registro,
            balances,
            [r.get("velocity", 0.0) for r in registros_pasados],
            [r.get("strategy", "")  for r in registros_pasados],
            [r.get("ganancia", 0.0) > 0 for r in registros_pasados]
        )
        dqn_idxs  = self.strategy_manager.get_dqn_feature_indices()
        state_dqn = state_full[dqn_idxs].astype(np.float32).reshape(1, -1)

        # 5.2) Llamada a select() con return_soft=True
        try:
            cat_pred, fichas_count, alg, p_soft = self.strategy_manager.select(
                state=state_dqn,
                return_soft=True
            )
        except Exception as e:
            logging.error(f"[PHASE 5] select(return_soft) falló: {e}")
            import traceback; traceback.print_exc()
            # fallback uniforme
            p_soft = np.ones(3, dtype=np.float32) / 3
            cat_pred, fichas_count, alg = "skip", 0, "skip"

        logging.debug(f"[PHASE 5] Próxima estrategia: {alg}, cat={cat_pred}, fichas={fichas_count}")
        # — 5.5) Cap dinámico de fichas —
        max_f = getattr(self, "current_max_fichas", None)
        if max_f is not None and fichas_count > max_f:
            logging.warning(f"[RISK] cap fichas {fichas_count}>{max_f} → {max_f}")
            fichas_count = max_f

        # — 5.6) Ganancia hipotética —
        ganancia_hip = 0.0
        if not self.apuesta_en_curso and alg != "skip" and not self._check_risk():
            try:
                _, ganancia_hip = self.data_collector.compute_gain(
                    numero, cat_pred, fichas_count, self.wager_value
                )
                logging.info(f"[SKIP‑HINT] Ganancia hipotética: {ganancia_hip:.2f}")
            except Exception as e:
                logging.warning(f"[SKIP‑HINT] simulación falló: {e}")

        # — Reactivación si skip con señal fuerte —
        if not self.apuesta_en_curso and cat_pred == "skip" and ganancia_hip >= self.reactivate_threshold:
            logging.info(f"⚡ Reactivando: hipotética {ganancia_hip:.2f} ≥ {self.reactivate_threshold}")
            cat_pred = self.last_cat
            fichas_count = max(1, fichas_count)

        # — 5.7) SKIP inteligente —
        if not self.apuesta_en_curso:
            is_risk = drawdown >= self.max_drawdown
            feats_vec = [
                feats["delta_time_norm"], feats["hour_sin"], feats["hour_cos"],
                feats["dow_sin"], feats["dow_cos"], feats["accel_mean"],
                feats["accel_std"], feats["accel_skew"],
                feats["players_mean"], feats["players_std"], feats["players_skew"],
                feats["hurst"], feats["lyapunov"], feats["entropy"], feats["dir_bin"]
            ]
            try:
                p_skip_model = self.skip_clf.predict_proba([feats_vec])[0, 1]
            except Exception:
                p_skip_model = p_soft[2]
            combined_skip_prob = 0.5 * p_skip_model + 0.5 * p_soft[2]
            if combined_skip_prob > 0.7 or is_risk:
                logging.warning(f"⚠ SKIP inteligente (P_skip={combined_skip_prob:.2f})")
                registro.update({"strategy": "skip", "fichas": 0, "monto": 0})
                self.db_manager.guardar_registro(registro)
                return registro

        # — 6) Ejecutar apuesta —
        amount = fichas_count * self.wager_value
        self.last_cat         = cat_pred
        self.last_amt         = fichas_count
        self.last_strat       = alg
        self.apuesta_en_curso = True

        sim = "[SIM]" if getattr(self.region_finder, "simulate", False) else "[REAL]"
        logging.info(f"{sim} Apostando {amount:.2f} ({fichas_count}) a '{cat_pred}'")
        if sim == "[REAL]" and fichas_count > 0:
            if self._check_risk():
                self.apuesta_en_curso = False
                self._skip_counter   += 1
                return registro
            try:
                self.region_finder.click_region(f"{self.wager_value}_1")
                time.sleep(0.1)
                self.place_bet(cat_pred, amount)
            except Exception as e:
                logging.error(f"[PHASE 7] place_bet error: {e}")
        else:
            logging.debug("[SIM] place_bet omitido.")

        # — 7) Final —
        self._update_wager_value()
        self._check_risk()
        self._skip_counter = 0
        logging.info(f"[PHASE] Fin apuesta+registro en {time.perf_counter() - t0:.3f}s")
        logging.info(f"[RECORD] {registro}")
        return registro




    def _log_cycle_time(self, cycle_start: float, cycle_end: float):
        """
        Helper opcional para registrar la latencia end‑to‑end de cada ciclo.
        - cycle_start: timestamp (time.perf_counter()) al inicio del ciclo.
        - cycle_end:   timestamp (time.perf_counter()) al final del ciclo.
        """
        duration = cycle_end - cycle_start
        print(f"[TIMINGS] Ciclo completo: {duration:.3f}s")

    def _update_wager_value(self):
            """
            Ajusta self.wager_value a 500 si balance_current < 50_000,
            o a 5 000 si balance_current ≥ 50_000, sin diferenciar entre real/sim.
            """
            THRESHOLD = 50_000
            LOW_STAKE = 500
            HIGH_STAKE = 5_000

            if self.balance_current >= THRESHOLD:
                self.wager_value = HIGH_STAKE
            else:
                self.wager_value = LOW_STAKE