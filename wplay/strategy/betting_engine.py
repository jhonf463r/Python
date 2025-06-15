import os
import time
import numpy as np
import pandas as pd
import pyautogui
import threading
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
class BettingEngine:
    def __init__(
        self,
        region_finder,
        data_collector: DataCollector,
        stats_helper: StatsHelper,
        db_manager: DBManager,
        place_bet_fn,
        strategy_manager: Optional[StrategyManagerDL] = None,
        login_handler=None,
        login_url: str = None,
        cooldown: float = 12.0,
        wager_value: int = 500,
    ):
        # ——————————————————————————————————————————————————————————————————————————
        # 1) PARTE ORIGINAL DE INICIALIZACIÓN
        #    – Asignación de dependencias y parámetros
        #    – Estado interno (balances, riesgos)
        #    – Pipeline offline (solo si no hay strategy_manager preentrenado)
        # ——————————————————————————————————————————————————————————————————————————
        self.region_finder   = region_finder
        self.data_collector  = data_collector
        self.stats_helper    = stats_helper
        self.db_manager      = db_manager
        self.place_bet       = place_bet_fn
        self.login_handler   = login_handler
        self.login_url       = login_url
        self.cooldown        = cooldown
        self.wager_value     = wager_value

        # Estado de balances y control de riesgo
        self.saldo             = 0.0
        self.spin_nums         = []
        self.max_drawdown      = 0.7
        self.stop_loss_daily   = 10000.0
        self.balance_start_day = 0.0
        self.balance_current   = 0.0
        self.peak_balance      = 0.0
        self.paused            = False
        self._reset_daily()  # Inicializa balances diarios

        if strategy_manager is not None:
            # Si me pasan un manager ya entrenado, lo uso y no vuelvo a entrenar
            self.strategy_manager = strategy_manager
            print("[INIT] StrategyManager preentrenado recibido → omitiendo pipeline offline.")
        else:
            # Ejecuto pipeline offline completo: limpieza, features, entrenamiento y pretrain RL
            print("[INIT] Reentrenando modelos (pipeline offline)...")
            ROOT_DIR    = os.path.dirname(os.path.dirname(__file__))
            DATA_DIR    = os.path.join(ROOT_DIR, "wplay", "data")
            CLEAN_CSV   = os.path.join(DATA_DIR, "clean_records.csv")
            LSTM_CSV    = os.path.join(DATA_DIR, "lstm_input.csv")
            RL_CSV      = os.path.join(DATA_DIR, "rl_input.csv")
            MODELS_DIR  = os.path.join(ROOT_DIR, "wplay", "models")
            LSTM_MODEL  = os.path.join(MODELS_DIR, "lstm.h5")
            TRANS_MODEL = os.path.join(MODELS_DIR, "transformer.h5")
            DQN_MODEL   = os.path.join(MODELS_DIR, "dqn.h5")
            PPO_MODEL   = os.path.join(MODELS_DIR, "ppo.h5")

            # Asegurar que existan las carpetas necesarias
            for p in (CLEAN_CSV, LSTM_CSV, RL_CSV):
                os.makedirs(os.path.dirname(p), exist_ok=True)
            for p in (LSTM_MODEL, TRANS_MODEL, DQN_MODEL, PPO_MODEL):
                os.makedirs(os.path.dirname(p), exist_ok=True)

            # 1) Limpieza de datos
            print("🔄 DataCleaner: limpiando registros…")
            df_raw = DBReader().load_rounds()
            df_raw.to_csv(CLEAN_CSV, index=False)
            print(f"✔️ CSV limpio guardado en '{CLEAN_CSV}'")

            # 2) Ingeniería de features
            print("🔄 FeatureEngineerDeep: generando características…")
            fe = FeatureEngineerDeep(
                clean_csv = CLEAN_CSV,
                lstm_csv  = LSTM_CSV,
                rl_csv    = RL_CSV,
                window    = 50,
                window_rl = 10,
            )
            fe.transform()
            print(f"✔️ Características RL guardadas en '{RL_CSV}'")

            # 3) Entrenar LSTM
            print("🔄 Entrenando LSTM…")
            if os.path.exists(LSTM_MODEL):
                os.remove(LSTM_MODEL)
            ModelTrainer(
                feat_csv      = LSTM_CSV,
                model_type    = 'lstm',
                window        = 50,
                test_size     = 0.2,
                learning_rate = 1e-3,
                epochs        = 20,
                dropout_rate  = 0.2
            ).train_model(output_model_path=LSTM_MODEL)
            print(f"✔️ LSTM guardado en '{LSTM_MODEL}'")

            # 4) Entrenar Transformer (manejo de excepciones para no interrumpir)
            print("🔄 Entrenando Transformer…")
            try:
                TransformerTrainer(
                    feat_csv      = LSTM_CSV,
                    model_type    = 'transformer',
                    window        = 11,
                    test_size     = 0.2,
                    learning_rate = 1e-4,
                    epochs        = 10,
                    dropout_rate  = 0.2
                ).train_model(output_model_path=TRANS_MODEL)
                print(f"✔️ Transformer guardado en '{TRANS_MODEL}'")
            except Exception as e:
                print("[WARN] TransformerTrainer falló:", e)

            # 5) Pre-entrenamiento offline de agentes DQN y PPO
            print("🔄 Preentrenando agentes DQN/PPO offline…")
            cols = pd.read_csv(RL_CSV, nrows=1).columns
            state_cols = [c for c in cols if c not in ("action","reward","done") and not c.startswith("next_")]
            state_dim  = len(state_cols)
            action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX

            dqn_agent = DQNAgent(state_dim=state_dim, action_dim=action_dim, model_path=DQN_MODEL)
            ppo_agent = PPOAgent(state_dim=state_dim, action_dim=action_dim, model_path=PPO_MODEL)

            RLTrainer(
                rl_csv_path    = RL_CSV,
                strategy_manager=None,
                dqn_agent      = dqn_agent,
                ppo_agent      = ppo_agent,
                buffer_size    = 10000,
                batch_size     = 64,
                train_interval = 50,
                gamma          = 0.99,
                save_dir       = MODELS_DIR
            ).pretrain_offline(epochs=5)
            print("✔️ Preentrenamiento RL offline completado.")

            # 6) Crear el StrategyManagerDL para producción
            self.strategy_manager = StrategyManagerDL(
                lstm_path            = LSTM_MODEL,
                rl_agent_dqn         = dqn_agent,
                rl_agent_ppo         = ppo_agent,
                window_lstm          = 50,
                window_rl            = 10,
                confidence_threshold = 0.1,
                bet_scale_factor     = 1.0,
                wager_value          = self.wager_value
            )
            print("✅ StrategyManagerDL inicializado.")

        # ——————————————————————————————————————————————————————————————————————————
        # 2) CONFIGURACIÓN DE DETECCIÓN PARALELA (SIEMPRE, incluso si hay manager preentrenado)
        #    – Lock y Condition para sincronizar con run()
        #    – Hilo daemon para detectar plantillas sin bloquear
        # ——————————————————————————————————————————————————————————————————————————
        self._det_lock      = threading.Lock()
        self._det_condition = threading.Condition(self._det_lock)
        self._latest_det    = {'regions': [], 'timestamp': time.time()}
        self._stop_detector = threading.Event()

        threading.Thread(
            target=self._detection_loop,
            name="DetectorThread",
            daemon=True
        ).start()

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
                # 1) Medir inicio de detección
                t0 = time.perf_counter()

                # 2) Ejecutar detección real con el objeto region_finder
                regions = self.region_finder.find_all_regions()

                # 3) Timestamp real de la detección
                ts = time.time()

                # 4) Bajo lock, guardar resultado y notificar a run()
                with self._det_condition:
                    self._latest_det['regions']   = regions
                    self._latest_det['timestamp'] = ts
                    self._det_condition.notify_all()

                # 5) Medir fin de detección y loguear duración
              #  t1 = time.perf_counter()
               # print(f"[TIMINGS] Detección: {t1 - t0:.3f}s")

                # 6) Pequeña pausa para evitar busy‑loop
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
        # Aquí se actualiza el pico si y solo si hay un nuevo máximo real
        self.peak_balance = max(self.peak_balance, self.balance_current)

    def _check_risk(self):
        """
        Comprueba el drawdown y muestra logs, pero ya no pausa el engine.
        """
        # Solo evaluamos drawdown si hay un peak_balance positivo
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.balance_current) / self.peak_balance
            print(f"[DEBUG][RISK] drawdown={drawdown*100:.1f}%, max_drawdown={self.max_drawdown*100:.1f}%")

            # Antes: si el drawdown superaba max_drawdown, se pausaba
            # if drawdown >= self.max_drawdown:
            #     print(f"⚠ Drawdown máximo alcanzado: {drawdown * 100:.1f}% → PAUSANDO")
            #     self.paused = True

            # Antes: reactivación cuando bajaba por debajo del 50% del umbral
            # elif self.paused and drawdown < (self.max_drawdown * 0.5):
            #     print("✅ Riesgo controlado — Reanudando apuestas")
            #     self.paused = False


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
        """
        Bucle principal del BettingEngine:
        - Detecta regiones en paralelo ('apostar', 'giro', etc.).
        - Aplica lógica de apuesta solo al detectar aparición nueva de 'apostar'.
        - Evita clics repetidos innecesarios.
        - Aplica control de relogin tras varios intentos fallidos.
        """
        import time, datetime

        print("🎲 Iniciando BettingEngine…")

        # — Inicialización de estado —
        self.saldo             = 10000.0
        self._update_wager_value()
        self.balance_current   = self.saldo
        self.balance_start_day = self.saldo
        self.peak_balance      = self.saldo

        last_bet_time         = 0.0
        last_apostar_time     = time.time()
        apuesta_en_curso      = False
        registered            = False
        self.last_recorded_num = None
        last_cat = last_strat = None
        last_amt = 0

        low_vel_count        = 0
        LOW_VEL_THRESHOLD    = 40.0
        LOW_VEL_MAX_COUNT    = 3

        relogin_fail_count   = 0
        RELOGIN_MAX_FAILS    = 3
        relogin_pause_until  = 0.0
        RELOGIN_PAUSE_SEC    = 10 * 60  # 10 minutos

        # Control de flanco de aparición de 'apostar'
        awaiting_apostar_click = False
        prev_has_apostar       = False

        try:
            while True:
                cycle_start = time.perf_counter()

                # 1) Obtener regiones detectadas más recientes
                with self._det_condition:
                    regions = list(self._latest_det['regions'])
                    det_ts  = self._latest_det['timestamp']

                # 2) Click en plantilla 'clic' si aparece
                if "clic" in regions:
                    self.region_finder.click_region("clic")
                    time.sleep(0.2)
                    continue

                # 3) Acumular info de giro (muestreo incremental)
                has_giro = "giro" in regions
                if has_giro and not getattr(self, "_prev_has_giro", False):
                    print("[DEBUG] Giro iniciado → muestreo incremental de velocidad.")
                self._prev_has_giro = has_giro

                if has_giro:
                    ruleta_list = self.data_collector.regions.get("ruleta", [])
                    if ruleta_list:
                        reg = ruleta_list[0]
                        coords = (reg["x"], reg["y"], reg["w"], reg["h"])
                        self.data_collector.incremental_spin(coords)
                    time.sleep(0.1)
                else:
                    # Al salir del giro, opcionalmente mostrar stats:
                    if hasattr(self.data_collector, "_last_ang"):
                        vel_med, dir_med = self.data_collector.get_spin_stats()
                        print(f"[DEBUG] Giro finalizado → velocidad mediana={vel_med:.1f}, dirección={dir_med}")
                        # limpiar estado temporal
                        del self.data_collector._last_ang
                        del self.data_collector._last_t


                # 4) Cooldown entre apuestas
                now = time.time()
                if now - last_bet_time < self.cooldown:
                    time.sleep(0.2)
                    continue

                # 5) Relogin tras 2 minutos sin ver 'apostar'
                if now - last_apostar_time > 2 * 60:
                    if now < relogin_pause_until:
                        wait = int(relogin_pause_until - now)
                        print(f"[ENGINE][INFO] Pausado relogin por {wait}s más")
                    else:
                        print("[ENGINE][WARN] 2 min sin 'apostar' → relogin")
                        success = self.relogin()
                        relogin_fail_count += 1
                        if success:
                            relogin_fail_count = 0
                        elif relogin_fail_count >= RELOGIN_MAX_FAILS:
                            relogin_pause_until = now + RELOGIN_PAUSE_SEC
                            relogin_fail_count = 0
                            print(f"[ENGINE][WARN] 3 relogin fallidos → pausando por 10 min")
                        self.data_collector.reset_spin_buffer()
                        self.spin_nums.clear()
                        last_apostar_time = time.time()
                        last_bet_time     = 0.0
                    time.sleep(1)
                    continue

                # 6) Esperar aparición de 'apostar'
                with self._det_condition:
                    self._det_condition.wait_for(
                        lambda: "apostar" in self._latest_det['regions'],
                        timeout=self.cooldown + 1
                    )
                    regions = list(self._latest_det['regions'])
                    det_ts  = self._latest_det['timestamp']
                has_apostar = "apostar" in regions

                # Detectar flanco de subida
                if has_apostar and not prev_has_apostar:
                    awaiting_apostar_click = True
                prev_has_apostar = has_apostar

                # Si no hay 'apostar', seguimos
                if not has_apostar:
                    time.sleep(0.2)
                    continue

                last_apostar_time = det_ts
                print(f"[INFO] 'apostar' detectado (ts={det_ts:.3f})")

                # 7) Obtener resultado OCR
                numero, jugadores = self.data_collector.read_result(regions)
                if numero is None:
                    print("[WARN] OCR no encontró número — ciclo skip.")
                    time.sleep(0.05)
                    continue

                # 8) Verificar velocidad del giro
                avg_vel, direction = self.data_collector.get_spin_stats()
                if avg_vel < LOW_VEL_THRESHOLD:
                    low_vel_count += 1
                    print(f"[WARN] Velocidad baja ({avg_vel:.1f}) [{low_vel_count}/{LOW_VEL_MAX_COUNT}]")
                    if low_vel_count >= LOW_VEL_MAX_COUNT:
                        print("[WARN] 3 velocidades bajas → relogin")
                        self.relogin()
                        self.data_collector.reset_spin_buffer()
                        self.spin_nums.clear()
                        low_vel_count = 0
                        continue
                else:
                    low_vel_count = 0

                # 9) Calcular ganancia previa
                gain = 0.0
                if apuesta_en_curso:
                    win, gain = self.data_collector.compute_gain(
                        numero, last_cat, last_amt, self.wager_value
                    )
                    print(f"[DEBUG] Resultado previo: win={win}, gain={gain}")

                # 10) Registro
                if not registered:
                    registro = {
                        "fecha_hora": datetime.datetime.fromtimestamp(det_ts)
                            .strftime("%Y-%m-%d %H:%M:%S"),
                        "numero": numero,
                        "jugadores_presentes": jugadores,
                        "velocity": avg_vel,
                        "direction": direction,
                        "numero_hist": list(self.spin_nums[-self.strategy_manager.window_rl:]),
                    }
                    if apuesta_en_curso and gain != 0:
                        stake = last_amt * self.wager_value
                        net = gain - stake if gain > 0 else gain
                        registro.update({
                            "ganancia": net,
                            "saldo_anterior": self.balance_current,
                            "strategy": last_strat,
                            "fichas": last_amt,
                            "saldo": self.balance_current + net,
                            "opcion_apuesta": last_cat
                        })
                    self.db_manager.guardar_registro(registro)
                    self.strategy_manager.add_record(registro)
                    print(">> Registro guardado:", registro)

                    if gain != 0:
                        self._update_balance(registro["ganancia"])
                        self._check_risk()
                    apuesta_en_curso = False
                    registered = True

                # 11) Verificar si se puede apostar
                if self.strategy_manager.last_state is None or self.paused:
                    if self.paused:
                        print("⚠ En pausa — recolectando datos sin apostar.")
                    time.sleep(0.2)
                    continue

                # 12) Elegir estrategia y ejecutar apuesta
                self._update_wager_value()
                cat_pred, fichas_count, used = self.strategy_manager.select()
                amount = fichas_count * self.wager_value
                label = "[REAL]" if not getattr(self.region_finder, "simulate", True) else "[SIM]"

                if label == "[REAL]" and awaiting_apostar_click:
                    key1 = f"{self.wager_value}_1"
                    key2 = str(self.wager_value)
                    region_key = key1 if key1 in regions else (key2 if key2 in regions else None)

                    if region_key:
                        self.region_finder.click_region(region_key)
                        time.sleep(0.2)
                        print(f"{label} Apostando {amount} ({fichas_count} ficha(s)) a '{cat_pred}' usando plantilla '{region_key}'")
                        self.place_bet(cat_pred, amount)
                    else:
                        print(f"[WARN] No detecté ni '{key1}' ni '{key2}' → salto click")

                    awaiting_apostar_click = False

                elif label == "[SIM]":
                    print(f"{label} Apostando {amount} ({fichas_count} ficha(s)) a '{cat_pred}'")

                # 13) Preparar siguiente ciclo
                apuesta_en_curso = True
                last_cat, last_amt, last_strat = cat_pred, fichas_count, used
                last_bet_time = time.time()
                registered = False

                self.data_collector.reset_spin_buffer()
                time.sleep(0.05)

                # 14) Latencia
                cycle_end = time.perf_counter()
                self._log_cycle_time(cycle_start, cycle_end)

        except KeyboardInterrupt:
            self._stop_detector.set()
            print("[INFO] BettingEngine detenido por usuario.")



    def _procesar_logica_y_apostar(self, regions, numero, jugadores, det_ts):
        """
        Ejecuta OCR/estrategia/apuesta/registro como bloque atómico:
        1) Usa los datos extraídos (numero, jugadores) por run().
        2) Selecciona acción con self.strategy_manager.select().
        3) En modo REAL, hace click en la ficha correspondiente.
        4) Llama a self.place_bet() con la categoría y monto calculado.
        5) Construye el registro, lo guarda en la BD y en el strategy_manager.
        6) Resetea el buffer y actualiza balance y riesgo.
        7) Mide y loggea el tiempo total de esta fase.
        """
        import datetime
        import time

        # 1) Inicio de medición interna de esta fase
        t0 = time.perf_counter()

        # 2) Selección de categoría, conteo de fichas y algoritmo usado
        cat_pred, fichas_count, alg = self.strategy_manager.select()
        amount = fichas_count * self.wager_value

        # 3) En modo REAL, hacer click en la ficha en pantalla
        if not getattr(self.region_finder, "simulate", False):
            ficha_region = f"{self.wager_value}_1"
            print(f"[REAL] Seleccionando ficha '{ficha_region}' antes de apostar")
            self.region_finder.click_region(ficha_region)
            time.sleep(0.1)

        # 4) Ejecutar la apuesta
        label = "[SIM]" if getattr(self.region_finder, "simulate", False) else "[REAL]"
        print(f"{label} Apostando {amount} ({fichas_count} ficha(s)) a '{cat_pred}'")
        self.place_bet(cat_pred, amount)

        # 5) Construir registro usando timestamp de detección real (det_ts)
        registro = {
            "fecha_hora":          datetime.datetime.fromtimestamp(det_ts)
                                    .strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "numero":              numero,
            "jugadores_presentes": jugadores,
            "opcion_apuesta":      cat_pred,
            "fichas":              fichas_count,
            "monto":               amount,
            # "ganancia" y "saldo" se añadirán tras compute_gain en run()
        }

        # Guardar en BD y en strategy_manager
        self.db_manager.guardar_registro(registro)
        print(">> Registro guardado:", registro)
        self.strategy_manager.add_record(registro)

        # 6) Reset de buffer de OCR/spin
        self.data_collector.reset_spin_buffer()

        # 7) Actualizar balance y riesgo (solo si se añadió 'ganancia' en run())
        if "ganancia" in registro:
            self._update_balance(registro["ganancia"])
            self._check_risk()

        # 8) Fin de medición y log de duración
        # t1 = time.perf_counter()
        #print(f"[TIMINGS] Apuesta+registro: {t1 - t0:.3f}s")

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