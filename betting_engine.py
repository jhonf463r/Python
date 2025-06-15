# wplay/strategy/betting_engine.py

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
from wplay.data.feature_engineer_deep import generate_unified_features

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
        """
        Si strategy_manager se pasa como argumento, se asume que ya se ejecutó
        el pipeline offline (obtener_datos_actualizados) y no se vuelve a correr.
        Si viene strategy_manager=None, se hace todo el flujo offline aquí dentro.
        """
        self.region_finder    = region_finder
        self.data_collector   = data_collector
        self.stats_helper     = stats_helper
        self.db_manager       = db_manager
        self.place_bet        = place_bet_fn
        self.login_handler    = login_handler
        self.cooldown         = cooldown
        self.wager_value      = wager_value
        self.saldo            = 0.0
        self.spin_nums        = []
        self.login_url        = login_url

        # Si ya tengo un strategy_manager entrenado, lo uso tal cual
        if strategy_manager is not None:
            self.strategy_manager = strategy_manager
            print("[INIT] Se recibió un StrategyManager preentrenado → omitiendo offline retraining.")
            return

        # En cambio, si strategy_manager == None, hago todo el flujo offline aquí:
        print("[INIT] Reentrenando modelos (pipeline offline)...")

        # --- Definir rutas relativas al root del proyecto ---
        ROOT_DIR   = os.path.dirname(os.path.dirname(__file__))  # .../wplay/strategy → subo dos niveles
        DATA_DIR   = os.path.join(ROOT_DIR, "wplay", "data")
        CLEAN_CSV  = os.path.join(DATA_DIR, "clean_records.csv")
        LSTM_CSV   = os.path.join(DATA_DIR, "lstm_input.csv")
        RL_CSV     = os.path.join(DATA_DIR, "rl_input.csv")

        MODELS_DIR = os.path.join(ROOT_DIR, "wplay", "models")
        LSTM_MODEL = os.path.join(MODELS_DIR, "lstm.h5")
        DQN_MODEL  = os.path.join(MODELS_DIR, "dqn.h5")
        PPO_MODEL  = os.path.join(MODELS_DIR, "ppo.h5")

        # Asegurar carpetas existentes
        for fpath in (CLEAN_CSV, LSTM_CSV, RL_CSV):
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
        for fpath in (LSTM_MODEL, DQN_MODEL, PPO_MODEL):
            os.makedirs(os.path.dirname(fpath), exist_ok=True)

        # 1) Ejecutar DataCleaner local (igual que en helpers)
        print("🔄 DataCleaner: limpiando registros…")
        reader = DBReader()  # reader carga desde la base de datos RAW
        df_raw = reader.load_rounds()
        os.makedirs(os.path.dirname(CLEAN_CSV), exist_ok=True)
        df_raw.to_csv(CLEAN_CSV, index=False)
        print(f"✔️ DataCleaner: CSV limpio guardado en '{CLEAN_CSV}'")

        # 2) Generar características avanzadas con módulo separado
        print("🔄 Generando características avanzadas…")

        generate_unified_features(
            clean_csv_path=CLEAN_CSV,
            lstm_csv_path=LSTM_CSV,
            rl_csv_path=RL_CSV,
            window_lstm=50,
            window_rl=10
        )
        print(f"✔️ Características generadas en '{LSTM_CSV}' y '{RL_CSV}'")

        # 3) Entrenar LSTM offline
        print("🔄 ModelTrainer: entrenando LSTM…")
        if os.path.exists(LSTM_MODEL):
            os.remove(LSTM_MODEL)

        # ---- CORRECCIÓN: instanciamos sin model_path ----
        trainer = ModelTrainer(
            feat_csv       = LSTM_CSV,      # CSV con features para LSTM
            model_type     = 'lstm',        # tipo de modelo
            window         = 50,            # debe coincidir con Window en FeatureEngineerDeep
            test_size      = 0.2,
            learning_rate  = 1e-3,
            epochs         = 20,
            dropout_rate   = 0.2
        )
        trainer.train_model(output_model_path = LSTM_MODEL)
        print(f"✔️ ModelTrainer: LSTM guardado en '{LSTM_MODEL}'")
        # ---- FIN CORRECCIÓN ----

        # 4) Entrenar Transformer (opcional)
        try:
            print("🔄 TransformerTrainer: entrenando Transformer…")
            # ---- CORRECCIÓN: llamamos sin model_path en el constructor ----
            transformer = TransformerTrainer(
                feat_csv      = LSTM_CSV,
                model_type    = 'transformer',
                window        = 11,
                test_size     = 0.2,
                learning_rate = 1e-4,
                epochs        = 10,
                dropout_rate  = 0.2
            )
            transformer.train_model(output_model_path = os.path.join(MODELS_DIR, "transformer.h5"))
            print("✔️ TransformerTrainer: Transformer guardado.")
        except Exception as e:
            print("[WARN] Entrenamiento Transformer falló:", e)

        # 5) Generar transiciones RL y preentrenar DQN/PPO si hay suficientes datos
        print("🔄 FeatureEngineerDeep (RL): generando transiciones para RL…")
        df_rl = pd.read_csv(RL_CSV)
        if len(df_rl) >= 100:
            cats = StrategyManagerDL.CATEGORIES

            def map_to_cat(num):
                if num in range(1, 37):
                    half = "1-18" if num <= 18 else "19-36"
                    par  = "par"   if num % 2 == 0 else "impar"
                    rojo_set = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
                    color = "rojo" if num in rojo_set else "negro"
                    for key in (color, par, half):
                        if key in cats:
                            return cats.index(key)
                return 0

            print("🔄 Preentrenando agentes DQN/PPO offline…")
            df_rl["action_cat"] = df_rl["numero"].apply(map_to_cat)
            df_rl["action_idx"] = df_rl["action_cat"] * MONTO_MAX + 0

            state_cols  = [c for c in df_rl.columns if c.startswith("state_")]
            next_cols   = [c for c in df_rl.columns if c.startswith("next_state_")]
            states      = df_rl[state_cols].values.astype(np.float32)
            actions     = df_rl["action_idx"].values.astype(np.int32)
            rewards     = df_rl["recompensa"].values.astype(np.float32)
            next_states = df_rl[next_cols].values.astype(np.float32)
            dones       = np.array([False]*(len(states)-1) + [True], dtype=np.bool_)

            # 5.1) DQN offline
            dqn = DQNAgent(
                state_dim=states.shape[1],
                action_dim=len(cats) * MONTO_MAX,
                model_path=DQN_MODEL
            )
            try:
                dqn.load(DQN_MODEL)
            except:
                pass

            dqn.train(
                batch_size  = 32,
                states      = states,
                actions     = actions,
                rewards     = rewards,
                next_states = next_states,
                dones       = dones,
                epochs      = 50
            )
            dqn.save(DQN_MODEL)

            print(f"✔️ DQNAgent preentrenado y guardado en '{DQN_MODEL}'")

            # 5.2) PPO offline
            ppo = PPOAgent(
                state_dim  = states.shape[1],
                action_dim = len(cats) * MONTO_MAX
            )
            try:
                ppo.load(PPO_MODEL.replace(".h5", "_actor.h5"),
                        PPO_MODEL.replace(".h5", "_critic.h5"))
            except:
                pass

            values = ppo.critic.predict(states, verbose=0).flatten()
            returns = []
            discounted_sum = 0
            for r, is_done in zip(reversed(rewards), reversed(dones)):
                if is_done:
                    discounted_sum = 0
                discounted_sum = r + ppo.gamma * discounted_sum
                returns.insert(0, discounted_sum)
            returns = np.array(returns, dtype=np.float32)

            advantages = returns - values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

            probs = ppo.actor.predict(states, verbose=0)
            old_logp = np.log(np.choose(actions, probs.T) + 1e-8)

            ppo.train_offline(
                states       = states,
                actions      = actions,
                returns      = returns,
                advantages   = advantages,
                old_logprobs = old_logp,
                epochs       = 50,
                batch_size   = 32
            )
            ppo.save(
                PPO_MODEL.replace(".h5", "_actor.h5"),
                PPO_MODEL.replace(".h5", "_critic.h5")
            )
            print(f"✔️ PPOAgent preentrenado y guardado en '{PPO_MODEL}'")
            # 6) Construir StrategyManagerDL con ambos agentes
            self.strategy_manager = StrategyManagerDL(
                lstm_path     = LSTM_MODEL,
                rl_agent_dqn  = dqn,
                rl_agent_ppo  = ppo,
                window_lstm   = 50,
                window_rl     = 10
            )
            print("✅ StrategyManagerDL configurado con DQN y PPO preentrenados.")
        else:
            # No hay suficientes muestras RL → cargo modelos existentes (si los hay)
            print("⚠ No hay suficientes muestras RL. Cargando DQN/PPO existentes (si los hay)...")
            cats = StrategyManagerDL.CATEGORIES

            dqn = DQNAgent(
                state_dim  = 1,
                action_dim = len(cats) * MONTO_MAX,
                model_path = DQN_MODEL
            )
            try:
                dqn.load()
            except:
                pass

            ppo = PPOAgent(
                state_dim  = 1,
                action_dim = len(cats) * MONTO_MAX,
                model_path = PPO_MODEL
            )
            try:
                ppo.load()
            except:
                pass

            self.strategy_manager = StrategyManagerDL(
                lstm_path     = LSTM_MODEL,
                rl_agent_dqn  = dqn,
                rl_agent_ppo  = ppo,
                window_lstm   = 50,
                window_rl     = 10
            )
            print("✅ StrategyManagerDL configurado (modelos existentes).")

    def relogin(self):
        """
        Tras 3 min sin detección de número:
        1) Cierra pop-ups.
        2) Recarga la página y maximiza la ventana.
        3) Si tras X intentos seguimos sin “ruleta”, entonces reabre Chrome.
        """
        from wplay.auth.login import paste_text  # para login_or_continue

        def wait_for_region(name: str, timeout: int = 10) -> bool:
            start = time.time()
            while time.time() - start < timeout:
                if name in self.region_finder.find_all_regions():
                    return True
                time.sleep(0.5)
            return False

        print("[ENGINE][WARN] 3 min sin detección → intentando limpieza de sesión…")

        # 1) Cerrar pop-ups
        for i in range(5):
            regs = self.region_finder.find_all_regions()
            if "cerrar" in regs:
                print(f"  → Pop-up: click 'cerrar' (intento {i+1})")
                self.region_finder.click_region("cerrar")
                time.sleep(0.5)
            else:
                break

        # 2) Intentar recargar en la misma ventana
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

        # 3) Verifico si ya veo la ruleta
        if wait_for_region("ruleta", timeout=15):
            print("[ENGINE] Ruleta visible tras recarga. Continuamos.")
        else:
            print("[ENGINE][WARN] No apareció 'ruleta'. Reabrimos Chrome…")
            # 4) Abrir de nuevo Chrome (fallback)
            url = self.login_url or getattr(self.login_handler, "login_url", None) or "https://wplay.co"
            try:
                self.login_handler.open_chrome(url)
                time.sleep(5)
                # repetir login completo
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

        # 5) Resetear buffers
        print("[ENGINE] Reset buffers de ruleta y datos de spin.")
        self.data_collector.reset_spin_buffer()
        self.spin_nums.clear()
        print("[ENGINE] Relogin completado.")
        return True

    def run(self):
        print("🎲 Iniciando BettingEngine…")
        last_bet_time   = 0.0
        last_num_time   = time.time()
        apuesta_en_curso = False
        last_cat, last_strat, last_amt = None, None, 0

        while True:
            det = self.region_finder.find_all_regions()

            # — Inactividad prolongada →
            if time.time() - last_num_time > 3 * 60:
                self.relogin()
                self.data_collector.reset_spin_buffer()
                self.spin_nums.clear()
                last_num_time = time.time()
                last_bet_time = 0.0
                continue

            # Si aparece “clic”…
            if "clic" in det:
                self.region_finder.click_region("clic")
                time.sleep(0.2)
                continue

            # Si la ruleta gira, acumulamos estadísticas
            if "giro" in det:
                    # Asegurarnos de usar la clave exacta 'ruleta'
                    coords = det.get("ruleta")
                    print("[DEBUG] regiones detectadas para ruleta:", det.keys())
                    if coords:
                        # pasar un dict con la misma forma que espera DataCollector
                        self.data_collector.accumulate_spin({"ruleta": coords})
                    else:
                        print("[ENGINE][WARN] Región 'ruleta' no detectada en det pese a que existe plantilla 'giro'.")


            # Cooldown entre apuestas
            now = time.time()
            if now - last_bet_time < self.cooldown:
                time.sleep(0.2)
                continue

            # Esperar botón “apostar”
            if "apostar" not in det:
                time.sleep(0.2)
                continue

            # Leer resultado (número + jugadores)
            numero, jugadores = self.data_collector.read_result(det)
            if numero is None:
                time.sleep(0.2)
                continue
            last_num_time = now

            # Calcular ganancia de la apuesta previa
            gain = 0.0
            if apuesta_en_curso:
                win, gain = self.data_collector.compute_gain(
                    numero, last_cat, last_amt, self.wager_value
                )
                print(f"[DEBUG] Resultado previo: win={win}, gain={gain}")

            # Obtener estadísticas del giro actual
            avg_vel, direction = self.data_collector.get_spin_stats()
            print(f"[DEBUG] Velocidad: {avg_vel:.2f}, dirección: {direction}")

            # Construir registro
            registro = {
                "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "numero": numero,
                "jugadores_presentes": jugadores,
                "ganancia": gain,
                "saldo_anterior": self.saldo,
                "velocity": avg_vel,
                "direction": direction,
                "strategy": last_strat,
                "fichas": last_amt,
                "saldo": self.saldo + gain,
                "opcion_apuesta": last_cat
            }

            # Guardar buffer de últimos spins (solo números)
            self.spin_nums.append(numero)
            if len(self.spin_nums) > self.strategy_manager.window_rl:
                self.spin_nums.pop(0)
            registro["numero_hist"] = list(self.spin_nums)

            # Guardar en BD
            self.db_manager.guardar_registro(registro)
            print(">> Registro guardado:", registro)

            # Avisar al strategy_manager de este registro
            self.strategy_manager.add_record(registro)

            # Decidir siguiente apuesta (híbrido DQN/PPO interno)
            cat_pred, amt, strat = self.strategy_manager.choose()
            print(f"[ENGINE] Próxima: categoría={cat_pred}, fichas={amt}")
            label = "[SIM]" if getattr(self.region_finder, "simulate", True) else "[REAL]"
            print(f"{label} Apostando {amt} fichas a '{cat_pred}'")
            self.place_bet(cat_pred, amt)

            # Actualizar bankroll
            self.saldo = registro["saldo"]
            apuesta_en_curso = True
            last_cat, last_amt, last_strat = cat_pred, amt, strat
            last_bet_time = now

            # Resetear buffer ruleta
            self.data_collector.reset_spin_buffer()
            time.sleep(0.2)
