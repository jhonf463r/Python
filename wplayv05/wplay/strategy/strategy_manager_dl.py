# wplay/strategy/strategy_manager_dl.py

import time
import logging
import numpy as np
import math
import tensorflow as tf
from tensorflow.keras.models import load_model
from collections import deque

from wplay.data.feature_engineer_deep import MAX_JUGADORES
from wplay.strategy.constants import MONTO_MAX, MAX_VELOCITY
from wplay.strategy.meta_strategy_selector import MetaStrategySelector

class StrategyManagerDL:
    """
    Estrategia híbrida DQN + PPO con estado enriquecido:
      - DQN y PPO aprenden en paralelo.
      - Meta‐selector combina sus señales.
      - Control de drawdown y ajuste de apuestas.
    """

    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(
        self,
        lstm_path: str,
        rl_agent_dqn,
        rl_agent_ppo,
        window_lstm: int = 50,
        window_rl: int = 10,
        confidence_threshold: float = 0.5,
        bet_scale_factor: float = 1.0,
        wager_value: int = 500,
    ):
        
        # en __init__ de StrategyManagerDL, tras inicializar last_algo, etc.:
        self.ucb_counts  = {'dqn': 0, 'ppo': 0}
        self.ucb_rewards = {'dqn': 0.0, 'ppo': 0.0}
        self.ucb_c       = 1.0   # coeficiente de exploración, ajústalo a tu gusto
        # Parámetros internos para normalizar Q/V
        self.v_min = float("inf")
        self.v_max = float("-inf")
        self.q_min = float("inf")
        self.q_max = float("-inf")

        # Estado (dim desconocida aún) y meta‐selector
        self.state_dim = 0
        self.window_lstm = window_lstm
        self.window_rl   = window_rl
        self.meta = MetaStrategySelector(
            state_dim=self.state_dim,
            strategy_list=['dqn', 'ppo'],
            window=self.window_rl
        )

        # Cargar LSTM si se va a usar para features secuenciales
        self.lstm = load_model(lstm_path) if lstm_path else None

        # Agentes RL
        self.rl_agent_dqn = rl_agent_dqn
        self.rl_agent_ppo = rl_agent_ppo

        # Parámetros de apuesta
        self.confidence_threshold = confidence_threshold
        self.bet_scale_factor     = bet_scale_factor
        self.wager_value          = wager_value

        # Mapear acción → (categoría, fichas)
        self.action_map = [
            (cat, fichas)
            for cat in StrategyManagerDL.CATEGORIES
            for fichas in range(1, MONTO_MAX + 1)
        ]
        self.action_dim = len(self.action_map)
        # Ajustar dims y rebuild en los agentes
        self.rl_agent_dqn.action_dim  = self.action_dim
        self.rl_agent_ppo.action_dim  = self.action_dim

        # Historial de registros y estados
        self.registros = deque(maxlen=self.window_lstm)
        self.last_state      = None
        self.last_state_dqn  = None
        self.last_chosen_idx = None
        self.last_algo       = None
        self.last_ppo_logprob= 0.0
        self.current_balance = 0.0

        # Configuración de logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

    def _rebuild_meta(self):
        """Reconstruye meta‐selector tras definir state_dim."""
        self.meta = MetaStrategySelector(
            state_dim=self.state_dim,
            strategy_list=['dqn', 'ppo'],
            window=self.window_rl
        )
        logging.info(f"[META] Reconstruido con state_dim={self.state_dim}")

    def _clip_state_dqn(self, state: np.ndarray) -> np.ndarray:
        """Recorta el vector de estado a las primeras 23 dims para DQN."""
        return state[:23]

    def add_record(self, registro: dict):
        """
        Añade un registro nuevo:
        1) Actualiza buffer de registros.
        2) Construye el estado actual completo.
        3) Si es el primer registro, inicializa state_dim y rebuild de agentes/meta.
        4) Si hay estado previo, calcula reward y entrena DQN, PPO y meta‐selector.
        5) Actualiza los contadores UCB de DQN/PPO.
        6) Actualiza wager_value según el nuevo balance.
        """
        # 1) Añadir a historial limitado
        self.registros.append(registro)

        # 2) Asegurar campos obligatorios en registro
        for fld in [
            "delta_time_norm", "hour_sin", "hour_cos",
            "dow_sin", "dow_cos", "accel_mean", "accel_std",
            "players_mean", "players_std"
        ]:
            registro.setdefault(fld, 0.0)

        # 3) Construir estado completo
        saldo_hist = [r.get("saldo", 0.0) for r in list(self.registros)[-self.window_rl:]]
        vel_hist   = [r.get("velocity", 0.0) for r in list(self.registros)[-self.window_rl:]]
        color_hist = [r.get("color", "") for r in list(self.registros)[-self.window_rl:]]
        win_times  = [r.get("ganancia", 0.0) > 0 for r in list(self.registros)[-self.window_rl:]]
        current_state = self._build_state_vector(registro, saldo_hist, vel_hist, color_hist, win_times)

        # 4) Inicializar dimensión del estado si es el primero
        if self.state_dim == 0:
            self.state_dim             = current_state.shape[-1]
            self.rl_agent_dqn.state_dim = self.state_dim
            self.rl_agent_ppo.state_dim = self.state_dim
            self.rl_agent_dqn.rebuild_network(self.state_dim)
            self.rl_agent_ppo.rebuild_network(self.state_dim)
            self._rebuild_meta()

        # 5) Si existe estado previo, entrenar online
        if self.last_state is not None and self.last_chosen_idx is not None:
            prev_state = self.last_state
            prev_saldo = float(self.registros[-2].get("saldo", 0.0))
            new_saldo  = float(self.registros[-1].get("saldo", 0.0))
            stake      = ((self.last_chosen_idx % MONTO_MAX) + 1) * self.wager_value
            raw_reward = np.clip((new_saldo - prev_saldo) / stake, -1.0, 1.0)
            peak = max(saldo_hist + [1e-6])
            dd   = min((peak - saldo_hist[-1]) / peak if peak > 0 else 0.0, 1.0)

            # — ACTUALIZACIÓN UCB1 antes del entrenamiento —
            # (garantiza que la elección del último algoritmo acumule su recompensa)
            if self.last_algo in ('dqn', 'ppo'):
                self.ucb_counts[self.last_algo]  += 1
                self.ucb_rewards[self.last_algo] += raw_reward

            # — DQN training —
            s_prev_dqn = self._clip_state_dqn(prev_state).astype(np.float32)
            s_curr_dqn = self._clip_state_dqn(current_state).astype(np.float32)
            self.rl_agent_dqn.store_transition(
                state=s_prev_dqn,
                action=self.last_chosen_idx,
                raw_reward=raw_reward,
                next_state=s_curr_dqn,
                done=False
            )
            if self.rl_agent_dqn.memory.size() >= 32:
                loss = self.rl_agent_dqn.train_online(batch_size=32)
                logging.info(f"[DQN TRAIN] loss={loss:.4f}")

            # — PPO training —
            self.rl_agent_ppo.store_transition(
                state=prev_state.astype(np.float32),
                action=self.last_chosen_idx,
                log_prob=self.last_ppo_logprob,
                reward=raw_reward,
                done=False,
                drawdown=dd
            )
            if len(self.rl_agent_ppo.buffer_states) >= 16:
                result = self.rl_agent_ppo.update()
                if result:
                    pl, vl, ent = result
                    logging.info(
                        f"[PPO TRAIN] policy_loss={pl:.4f}, value_loss={vl:.4f}, entropy={ent:.4f}"
                    )

            # — Meta‐selector update —
            shaped = raw_reward - 0.5 * dd
            self.meta.update(self.last_algo, np.clip(shaped, -1.0, 1.0))

        # 6) Guardar estado y actualizar wager_value
        self.last_state      = current_state
        self.last_state_dqn  = self._clip_state_dqn(current_state)
        self.current_balance = float(registro.get("saldo", 0.0))
        self._update_wager_value()



    def _build_state_vector(
        self,
        registro: dict,
        saldo_history: list,
        vel_history: list,
        color_history: list,
        win_times: list
    ) -> np.ndarray:
        """
        Construye un vector de estado concatenando:
         A) número normalizado y jugadores
         B) features temporales (hora, día)
         C) estadísticas de velocidad
         D) proporciones color/paridad
         E) estadísticas de aceleración/jugadores
         F) one-hot de estrategia previa
         G) drawdown
         H) tiempo desde última ganancia
        """
        vec = []
        # A) número y jugadores
        vec.append(registro.get("numero", 0)/36.0)
        jug = min(registro.get("jugadores_presentes", 0), MAX_JUGADORES)
        vec.append(jug / MAX_JUGADORES)

        # B) temporales
        for fld in ("delta_time_norm","hour_sin","hour_cos","dow_sin","dow_cos"):
            vec.append(registro.get(fld, 0.0))

        # C) velocidad media y desvío
        arr_v = np.array(vel_history[-self.window_rl:], dtype=float)
        if arr_v.size < self.window_rl:
            arr_v = np.pad(arr_v, (self.window_rl - arr_v.size, 0), 'constant')
        vec.append(arr_v.mean() / MAX_VELOCITY)
        vec.append(arr_v.std()  / MAX_VELOCITY)

        # D) proporciones color/paridad
        red_prop = color_history.count("rojo") / self.window_rl
        vec.append(red_prop)
        vec.append(1.0 - red_prop)
        nums = registro.get("numero_hist", [])[-self.window_rl:]
        nums += [0]*(self.window_rl - len(nums))
        par_prop = sum(n%2==0 for n in nums)/self.window_rl
        vec.append(par_prop)
        vec.append(1.0 - par_prop)

        # E) aceleración y jugadores (rolling stats)
        for fld in ("accel_mean","accel_std","players_mean","players_std"):
            vec.append(registro.get(fld, 0.0))

        # F) estrategia previa one-hot
        prev = registro.get("strategy_prev", "none")
        for s in ['none','dqn','ppo','martingala','fibonacci','dalembert','other']:
            vec.append(1.0 if prev==s else 0.0)

        # G) drawdown
        peak = max(saldo_history + [1e-6])
        curr = saldo_history[-1] if saldo_history else 0.0
        dd = min((peak-curr)/peak if peak>0 else 0.0,1.0)
        vec.append(dd)

        # H) tiempo desde última ganancia (normalizado a 300s)
        t_win = 300.0
        for r in reversed(self.registros):
            if r.get("ganancia",0)>0 and "fecha_hora" in r:
                t0 = time.mktime(time.strptime(r["fecha_hora"], "%Y-%m-%d %H:%M:%S"))
                t_win = min(time.time()-t0, 300.0)
                break
        vec.append(t_win/300.0)

        return np.array(vec, dtype=np.float32)

    def select(self) -> tuple:
        """
        Elige acción combinando:
        1) DQN sobre estado recortado a 23 dims.
        2) PPO sobre estado completo.
        3) Meta‐selector decide cuál usar, aplicado umbral de confianza o UCB1.
        4) Control de riesgo (drawdown alto reduce fichas).
        Devuelve:
        - cat (str)
        - fichas_count (int)
        - algo (str)
        """
        if self.last_state is None:
            logging.warning("No hay estado para seleccionar acción.")
            return StrategyManagerDL.CATEGORIES[0], 0, "none"

        # 1) DQN
        s_dqn   = self.last_state_dqn
        idx_dqn = self.rl_agent_dqn.select_action(s_dqn)
        q_vals  = self.rl_agent_dqn.q_network.predict(s_dqn[None], verbose=0)[0]
        q_max   = q_vals[idx_dqn]
        self.q_min = min(self.q_min, float(q_vals.min()))
        self.q_max = max(self.q_max, float(q_vals.max()))
        q_norm  = (q_max - self.q_min) / max(self.q_max - self.q_min, 1e-8)

        # 2) PPO
        s_ppo      = self.last_state
        idx_ppo, logp, v = self.rl_agent_ppo.select_action(s_ppo)
        self.last_ppo_logprob = logp
        self.v_min = min(self.v_min, float(v))
        self.v_max = max(self.v_max, float(v))
        v_norm  = (v - self.v_min) / max(self.v_max - self.v_min, 1e-8)

        # 3) Competición DQN vs PPO vía UCB1
        total_counts = self.ucb_counts['dqn'] + self.ucb_counts['ppo']
        ucb_scores = {}
        for algo in ('dqn', 'ppo'):
            count = self.ucb_counts[algo]
            reward = self.ucb_rewards[algo]
            if count == 0:
                # explorar primero cada uno
                ucb_scores[algo] = float('inf')
            else:
                mean_r = reward / count
                ucb_scores[algo] = mean_r + self.ucb_c * math.sqrt(math.log(total_counts) / count)
        # elegir el agente con mayor UCB
        algo = max(ucb_scores, key=ucb_scores.get)

        chosen_idx = idx_ppo if algo == 'ppo' else idx_dqn

        # 4) Control de riesgo (drawdown)
        balances = [r.get("saldo", 0.0) for r in list(self.registros)[-self.window_rl:]]
        peak     = max(balances + [1e-6])
        last_bal = balances[-1] if balances else peak
        drawdown = min((peak - last_bal) / peak if peak > 0 else 0.0, 1.0)

        # 5) Número de fichas (conteo)
        cat, fichas_count = self.action_map[chosen_idx]
        if drawdown > 0.8:
            fichas_count = min(fichas_count, 3)

        # Guardar elección y métricas
        self.last_chosen_idx = chosen_idx
        self.last_algo       = algo
        logging.info(
            f"[CHOICE] {algo.upper()} idx={chosen_idx}, cat={cat}, "
            f"fichas_count={fichas_count}, wager_value={self.wager_value}, "
            f"Q_norm={q_norm:.2f}, V_norm={v_norm:.2f}, DD={drawdown:.2%}"
        )

        return cat, fichas_count, algo

    def bet_amount(self) -> int:
        """
        Ajusta el monto de apuesta según la diferencia entre Q y V normalizadas.
        """
        conf = abs(self.last_q_max - self.last_v_max)
        return int(self.wager_value * (1 + conf * self.bet_scale_factor))

    def _update_wager_value(self):
        """
        Ajusta wager_value a 5_000 si balance ≥ 50_000, sino 500.
        """
        if self.current_balance >= 100_000:
            self.wager_value = 5_000
        else:
            self.wager_value = 500
