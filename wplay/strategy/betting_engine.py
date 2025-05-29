# Archivo: wplay/strategy/betting_engine.py

import os
import time
import pyautogui
import numpy as np
import pandas as pd
import webbrowser  
from wplay.capture.data_collector import DataCollector
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager
from wplay.data.db_reader import DBReader
from wplay.data.feature_engineer_deep import FeatureEngineerDeep
from wplay.data.model_trainer import ModelTrainer
from wplay.data.transformer_trainer import TransformerTrainer
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent

class BettingEngine:
    def __init__(
        self,
        region_finder,
        data_collector: DataCollector,
        stats_helper: StatsHelper,
        db_manager: DBManager,
        place_bet_fn,
        strategy_manager,
        login_handler=None,
        login_url: str = None, 
        cooldown: float = 12.0,
        wager_value: int = 500,
    ):
        self.region_finder    = region_finder
        self.collector        = data_collector
        self.stats_helper     = stats_helper
        self.db_manager       = db_manager
        self.place_bet        = place_bet_fn
        self.strategy_manager = strategy_manager
        self.login_handler    = login_handler
        self.cooldown         = cooldown
        self.wager_value      = wager_value
        self.saldo            = 0.0
        self.spin_nums        = []
        self.login_url        = login_url  

        print("[INIT] Reentrenando modelos…")
        # — mismo pipeline de entrenamiento offline que ya tenías —
        reader = DBReader()
        df = reader.load_rounds()

        data_dir  = os.path.join("wplay", "data")
        clean_csv = os.path.join(data_dir, "clean_records.csv")
        lstm_csv  = os.path.join(data_dir, "lstm_input.csv")
        rl_csv    = os.path.join(data_dir, "rl_input.csv")

        fe = FeatureEngineerDeep(
            clean_csv=clean_csv,
            lstm_csv=lstm_csv,
            rl_csv=rl_csv,
            window_lstm=self.strategy_manager.window_lstm,
            window_rl=self.strategy_manager.window_rl
        )
        fe.transform()

        lstm_model_path = os.path.join("wplay", "models", "lstm.h5")
        if os.path.exists(lstm_model_path): os.remove(lstm_model_path)
        ModelTrainer(feat_csv=lstm_csv, model_path=lstm_model_path, epochs=20).train()

        try:
            transformer = TransformerTrainer(
                feat_csv=lstm_csv,
                model_path=os.path.join("wplay","models","transformer.h5"),
                epochs=10,
                batch_size=64
            )
            transformer.train()
        except Exception as e:
            print("[WARN] Entrenamiento Transformer falló:", e)

        try:
            df_rl = pd.read_csv(rl_csv)
            cats = self.strategy_manager.CATEGORIES
            def map_to_cat(num):
                if num in range(1,37):
                    half = '1-18' if num<=18 else '19-36'
                    par  = 'par' if num%2==0 else 'impar'
                    color = 'rojo' if num in self.stats_helper.rojos else 'negro'
                    for key in (color, par, half):
                        if key in cats:
                            return cats.index(key)
                return 0
            df_rl['action_cat'] = df_rl['action'].apply(map_to_cat)
            state_cols = [c for c in df_rl.columns if c.startswith('state_')]
            states  = df_rl[state_cols].values
            actions = df_rl['action_cat'].values
            rewards = df_rl['reward'].values

            # DQN
            DQNAgent(
                state_dim=self.strategy_manager.window_rl+3,
                action_dim=len(cats),
                model_path=os.path.join("wplay","models","dqn.h5")
            ).train(states, actions, rewards, epochs=50, batch_size=32)

            # PPO
            advantages = rewards.copy()
            returns    = rewards.copy()
            old_logp   = np.zeros_like(actions, dtype=float)
            PPOAgent(
                state_dim=self.strategy_manager.window_rl+3,
                action_dim=len(cats),
                model_path=os.path.join("wplay","models","ppo.h5")
            ).train(states, actions, advantages, returns, old_logp, epochs=50, batch_size=32)
        except Exception as e:
            print("[WARN] Entrenamiento RL falló:", e)


    def relogin(self):
        """
        Tras 3 min sin detección, cierra ventanas, espera 10 min,
        abre navegador + login + selección de juego.
        """
        print("[ENGINE][WARN] 3 min sin detección de número; reiniciando sesión…")

        # 1) Cerrar todas las ventanas ‘cerrar’
        for intento in range(10):
            det = self.region_finder.find_all_regions()
            if "cerrar" in det:
                print(f"[ENGINE] Clic en 'cerrar' (intento {intento+1})")
                self.region_finder.click_region("cerrar")
                time.sleep(2)
            else:
                break

        # 2) Esperar 10 min antes de reloguear
        print("[ENGINE] Esperando 10 min antes de reloguear…")
        time.sleep(10 * 60)

        # 3) Abrir URL en navegador
        url = getattr(self.login_handler, "login_url", None) or "https://wplay.co"
        print(f"[ENGINE] Abriendo navegador en {url}")
        webbrowser.open_new_tab(url)
        time.sleep(8)

        # 4) Ejecutar login automático
        if self.login_handler:
            print("[ENGINE] Ejecutando login automático…")
            self.login_handler.perform_login()
            time.sleep(5)

        # 5) Seleccionar el juego de nuevo
        print("[ENGINE] Seleccionando juego de nuevo…")
        for nombre in ("buscar juego", "speed auto roulette"):
            det = self.region_finder.find_all_regions()
            if nombre in det:
                print(f"[ENGINE] Clic en '{nombre}'")
                self.region_finder.click_region(nombre)
                time.sleep(3)

        # 6) Limpiar buffers
        self.collector.reset_spin_buffer()
        self.spin_nums.clear()
        print("[ENGINE] Login y selección completados.")

    def run(self):
        print("🎲 Iniciando BettingEngine…")
        last_bet_time = 0.0
        last_num_time = time.time()
        apuesta_en_curso = False
        last_cat, last_strat, last_amt = None, None, 0

        while True:
            det = self.region_finder.find_all_regions()

            # — Inactividad prolongada —
            if time.time() - last_num_time > 3 * 60:
                self.relogin()
                # reset
                self.collector.reset_spin_buffer()
                self.spin_nums.clear()
                last_num_time = time.time()
                last_bet_time = 0.0
                continue

            # Clics
            if "clic" in det:
                self.region_finder.click_region("clic")
                time.sleep(0.2)
                continue

            # Giro
            if "giro" in det:
                rois = self.collector.regions.get("ruleta", [])
                if rois:
                    x, y, w, h = rois[0].values()
                    self.collector.accumulate_spin({"ruleta": (x, y, w, h)})
                else:
                    print("[ENGINE][WARN] No hay ROI 'ruleta'.")

            # Cooldown
            now = time.time()
            if now - last_bet_time < self.cooldown:
                time.sleep(0.2)
                continue

            # Esperar 'apostar'
            if "apostar" not in det:
                time.sleep(0.2)
                continue

            # Leer resultado
            numero, jugadores = self.collector.read_result(det)
            if numero is None:
                time.sleep(0.2)
                continue
            last_num_time = now

            # Ganancia previa
            gain = 0.0
            if apuesta_en_curso:
                win, gain = self.collector.compute_gain(
                    numero, last_cat, last_amt, self.wager_value
                )
                print(f"[DEBUG] Resultado previo: win={win}, gain={gain}")

            # Estadísticas
            avg_vel, direction = self.collector.get_spin_stats()
            print(f"[DEBUG] Velocidad: {avg_vel:.2f}, dirección: {direction}")

            # Registro
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
            # Historial
            self.spin_nums.append(numero)
            if len(self.spin_nums) > self.strategy_manager.window_rl:
                self.spin_nums.pop(0)
            registro["numero_hist"] = list(self.spin_nums)

            # Guardar
            self.db_manager.guardar_registro(registro)
            print(">> Registro guardado:", registro)
            self.strategy_manager.add_record(registro)

            # Siguiente apuesta
            cat_pred, amt, strat = self.strategy_manager.choose()
            print(f"[ENGINE] Próxima: categoría={cat_pred}, fichas={amt}")
            label = "[SIM]" if getattr(self.region_finder, "simulate", True) else "[REAL]"
            print(f"{label} Apostando {amt} fichas a '{cat_pred}'")
            self.place_bet(cat_pred, amt)

            # Actualizar estado
            self.saldo = registro["saldo"]
            apuesta_en_curso = True
            last_cat, last_amt, last_strat = cat_pred, amt, strat
            last_bet_time = now

            # Reset buffer de giro
            self.collector.reset_spin_buffer()
            time.sleep(0.2)
