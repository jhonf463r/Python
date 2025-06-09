import os
import time
import numpy as np
import pandas as pd
import pyautogui
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

class BettingEngine:
    def __init__(
        self,
        region_finder,
        data_collector: DataCollector,
        stats_helper: StatsHelper,
        db_manager: DBManager,
        place_bet_fn,
        strategy_manager=None,
        login_handler=None,
        login_url: str = None,
        cooldown: float = 12.0,
        wager_value: int = 500,
    ):
        self.region_finder  = region_finder
        self.data_collector = data_collector
        self.stats_helper   = stats_helper
        self.db_manager     = db_manager
        self.place_bet      = place_bet_fn
        self.login_handler  = login_handler
        self.login_url      = login_url
        self.cooldown       = cooldown
        self.wager_value    = wager_value
        self.saldo          = 0.0
        self.spin_nums      = []
        self.max_drawdown = 0.7  # permítele caer hasta 70 % antes de pausar
        # Gestión de riesgo
        self.stop_loss_daily   = 10000.0
        self.balance_start_day = 0.0
        self.balance_current   = 0.0
        self.peak_balance      = 0.0
        self.paused            = False
        self._reset_daily()

        # Si me pasan un manager ya entrenado, lo uso directamente
        if strategy_manager is not None:
            self.strategy_manager = strategy_manager
            print("[INIT] StrategyManager preentrenado recibido → omitiendo pipeline offline.")
            return

        # Sino, corro todo el pipeline offline:
        print("[INIT] Reentrenando modelos (pipeline offline)...")
        ROOT_DIR   = os.path.dirname(os.path.dirname(__file__))
        DATA_DIR   = os.path.join(ROOT_DIR, "wplay", "data")
        CLEAN_CSV  = os.path.join(DATA_DIR, "clean_records.csv")
        LSTM_CSV   = os.path.join(DATA_DIR, "lstm_input.csv")
        RL_CSV     = os.path.join(DATA_DIR, "rl_input.csv")

        MODELS_DIR = os.path.join(ROOT_DIR, "wplay", "models")
        LSTM_MODEL = os.path.join(MODELS_DIR, "lstm.h5")
        DQN_MODEL  = os.path.join(MODELS_DIR, "dqn.h5")
        PPO_MODEL  = os.path.join(MODELS_DIR, "ppo.h5")

        # Asegurar carpetas
        for f in (CLEAN_CSV, LSTM_CSV, RL_CSV):
            os.makedirs(os.path.dirname(f), exist_ok=True)
        for m in (LSTM_MODEL, DQN_MODEL, PPO_MODEL):
            os.makedirs(os.path.dirname(m), exist_ok=True)

        # 1) DataCleaner
        print("🔄 DataCleaner: limpiando registros…")
        reader = DBReader()
        df_raw = reader.load_rounds()
        df_raw.to_csv(CLEAN_CSV, index=False)
        print(f"✔️ CSV limpio guardado en '{CLEAN_CSV}'")

        # 2) FeatureEngineerDeep
        print("🔄 FeatureEngineerDeep: generando características…")
        fe = FeatureEngineerDeep(
            clean_csv = CLEAN_CSV,
            lstm_csv  = LSTM_CSV,
            rl_csv    = RL_CSV,
            window    = 50,
            window_rl = 10
        )
        fe.transform()
        print(f"✔️ Características RL en '{RL_CSV}'")

        # 3) Entrenar LSTM
        print("🔄 Entrenando LSTM…")
        if os.path.exists(LSTM_MODEL): os.remove(LSTM_MODEL)
        trainer = ModelTrainer(
            feat_csv      = LSTM_CSV,
            model_type    = 'lstm',
            window        = 50,
            test_size     = 0.2,
            learning_rate = 1e-3,
            epochs        = 20,
            dropout_rate  = 0.2
        )
        trainer.train_model(output_model_path = LSTM_MODEL)
        print(f"✔️ LSTM guardado en '{LSTM_MODEL}'")

        # 4) Entrenar Transformer
        try:
            print("🔄 Entrenando Transformer…")
            transformer = TransformerTrainer(
                feat_csv      = LSTM_CSV,
                model_type    = 'transformer',
                window        = 11,
                test_size     = 0.2,
                learning_rate = 1e-4,
                epochs        = 10,
                dropout_rate  = 0.2
            )
            transformer.train_model(
                output_model_path = os.path.join(MODELS_DIR, "transformer.h5")
            )
            print("✔️ Transformer guardado.")
        except Exception as e:
            print("[WARN] TransformerTrainer falló:", e)

        # 5) Preparar datos RL y pre-entrenar agentes offline
        df_rl = pd.read_csv(RL_CSV)
        cats = StrategyManagerDL.CATEGORIES
        # Mapeo, entrenamiento offline DQN y PPO...
        # Instanciar StrategyManagerDL
        self.strategy_manager = StrategyManagerDL(
            lstm_path         = LSTM_MODEL,
            rl_agent_dqn      = dqn,
            rl_agent_ppo      = ppo,
            window_lstm       = 50,
            window_rl         = 10,
            confidence_threshold = 0.1,
            bet_scale_factor     = 1.0,
            wager_value          = self.wager_value,  # <- importante
        )

        print("✅ StrategyManagerDL inicializado.")
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
            self.strategy_manager.ppo_val_buffer.clear()
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
        print("🎲 Iniciando BettingEngine…")

        # 🔧 Inicializar balances
        self.balance_current   = self.saldo
        self.balance_start_day = self.saldo
        self.peak_balance      = self.saldo

        last_bet_time      = 0.0
        last_apostar_time  = time.time()
        apuesta_en_curso   = False
        last_cat = last_strat = None
        last_amt = 0
        registered = False

        # Para no duplicar el mismo número en spin_nums
        self.last_recorded_num = None

        while True:
            # 1) Detectar regiones
            det = self.region_finder.find_all_regions()

            # Reset de registro cuando desaparece "apostar"
            if "apostar" not in det:
                registered = False
                self.last_recorded_num = None

            # 2) Relogin si no vemos "apostar" hace 2 min
            if time.time() - last_apostar_time > 2 * 60:
                print("[ENGINE][WARN] 2 min sin 'apostar' → relogin")
                self.relogin()
                self.data_collector.reset_spin_buffer()
                self.spin_nums.clear()
                last_apostar_time = time.time()
                last_bet_time = 0.0
                continue

            # 3) Click en plantillas
            if "clic" in det:
                self.region_finder.click_region("clic")
                time.sleep(0.2)
                continue

            # 4) Acumular spin si detectamos "giro"
            if "giro" in det:
                rois = self.data_collector.regions.get("ruleta", [])
                if rois:
                    x, y, w, h = rois[0]['x'], rois[0]['y'], rois[0]['w'], rois[0]['h']
                    self.data_collector.accumulate_spin({"ruleta": (x, y, w, h)})
                else:
                    print("[ENGINE][WARN] No hay ROI 'ruleta' para acumular giro.")

            # 5) Cooldown entre apuestas
            now = time.time()
            if now - last_bet_time < self.cooldown:
                time.sleep(0.2)
                continue

            # 6) Si aparece "apostar", actualizo timestamp
            if "apostar" in det:
                last_apostar_time = now
            else:
                time.sleep(0.2)
                continue

            # 7) Leer resultado OCR
            numero, jugadores = self.data_collector.read_result(det)
            if numero is None:
                time.sleep(0.2)
                continue

            # Solo agregar a spin_nums cuando es un nuevo número
            if numero != self.last_recorded_num:
                self.last_recorded_num = numero
                self.spin_nums.append(numero)
                if len(self.spin_nums) > self.strategy_manager.window_rl:
                    self.spin_nums.pop(0)
                registered = False

            # 8) Calcular ganancia previa
            gain = 0.0
            if apuesta_en_curso:
                win, gain = self.data_collector.compute_gain(
                    numero, last_cat, last_amt, self.wager_value
                )
                print(f"[DEBUG] Resultado previo: win={win}, gain={gain}")

            # 9) Stats de giro
            avg_vel, direction = self.data_collector.get_spin_stats()

            # 10) Guardar registro (solo la parte de ruleta si estamos en pausa)
            if not registered:
                registro = {
                    "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "numero": numero,
                    "jugadores_presentes": jugadores,
                    "velocity": avg_vel,
                    "direction": direction,
                    "numero_hist": list(self.spin_nums)
                }

                if not self.paused:
                    # 🧮 Ajuste: registrar ganancia neta (descontando monto apostado)
                    monto_apostado = last_amt * self.wager_value
                    ganancia_neta = gain - monto_apostado if gain > 0 else gain

                    registro.update({
                        "ganancia": ganancia_neta,
                        "saldo_anterior": self.saldo,
                        "strategy": last_strat,
                        "fichas": last_amt,
                        "saldo": self.saldo + ganancia_neta,
                        "opcion_apuesta": last_cat
                    })

                self.db_manager.guardar_registro(registro)
                print(">> Registro guardado:", registro)

                # ——— AÑADIDO: inicializar last_state con cada nuevo registro ———  #<<<
                print(f"[DEBUG] Nuevo registro, llamando a add_record()")
                self.strategy_manager.add_record(registro)                  #<<<
                # Así, tras window_rl registros, last_state deja de ser None   #<<<

                registered = True

                if apuesta_en_curso and not self.paused:
                    apuesta_en_curso = False

                if not self.paused:
                    self._update_balance(registro.get("ganancia", 0.0))
                    self._check_risk()

            # 11) Saltar apuesta si no hay estado válido o estamos en pausa
               # ➤ DEBUG: cuántos spins tenemos y si last_state está listo
            print(f"[DEBUG][BUFFER] spin_nums={len(self.spin_nums)}/{self.strategy_manager.window_rl}, "
                  f"last_state={'SET' if self.strategy_manager.last_state is not None else 'None'}")

            if self.strategy_manager.last_state is None or self.paused:
                if self.paused:
                    print("⚠ En pausa — recolectando datos sin apostar.")
                time.sleep(0.2)
                continue

            # 12) Elegir acción y apostar
            cat_pred, amt, used = self.strategy_manager.choose()
            print(f"[CHOICE] {used} → categoría={cat_pred}, fichas={amt}")
            label = "[SIM]" if getattr(self.region_finder, "simulate", True) else "[REAL]"
            print(f"{label} Apostando {amt} ficha(s) a '{cat_pred}'")
            self.place_bet(cat_pred, amt)

            # 13) Marcar nueva apuesta
            self.saldo = registro.get("saldo", self.saldo)
            apuesta_en_curso = True
            last_cat, last_amt, last_strat = cat_pred, amt, used
            last_bet_time = now

            # 14) Reset buffer OCR
            self.data_collector.reset_spin_buffer()
            time.sleep(0.2)
