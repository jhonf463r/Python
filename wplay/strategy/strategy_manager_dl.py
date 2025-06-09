import time
import collections
import numpy as np
import collections

import tensorflow as tf
from tensorflow.keras.models import load_model
from wplay.data.feature_engineer_deep import MAX_JUGADORES
from wplay.strategy.constants import MONTO_MAX
from collections import deque

class StrategyManagerDL:
    """
    Estrategia híbrida DQN + PPO. Contiene:
      - Un DQNAgent (self.rl_agent_dqn)
      - Un PPOAgent (self.rl_agent_ppo)

    Ambos aprenden en paralelo (DQN con replay buffer + PPO con su propio buffer).
    Al elegir → comparamos Q(s, a)_DQN con V(s)_PPO (cada uno normalizado por su propio rango).

    Mejoras incorporadas:
      - Normalización de V usando buffer propio
      - Uso de action_map para mapear índice a (categoría, fichas)
      - Eliminación de lógica redundante de descomposición de índices
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
        self.current_balance = 0.0
        self.ppo_val_buffer = deque(maxlen=100)
        self.v_min = float('inf')
        self.v_max = float('-inf')
        self.wager_value           = wager_value 
        # 1) Cargar LSTM si corresponde
        self.lstm = load_model(lstm_path) if lstm_path else None

        # 2) Instancias de agentes
        self.rl_agent_dqn = rl_agent_dqn
        self.rl_agent_ppo = rl_agent_ppo

        # 3) Ventanas de historial
        self.window_lstm = window_lstm
        self.window_rl   = window_rl

        # 4) Parámetros de selección avanzada
        self.confidence_threshold = confidence_threshold
        self.bet_scale_factor = bet_scale_factor

        # 5) Construir action_map: lista de (categoría, fichas)
        self.action_map = [
            (cat, fichas)
            for cat in StrategyManagerDL.CATEGORIES
            for fichas in range(1, MONTO_MAX + 1)
        ]
        self.action_dim = len(self.action_map)

        # 6) Ajustar action_dim en agentes
        self.rl_agent_dqn.action_dim = self.action_dim
        self.rl_agent_ppo.action_dim = self.action_dim

        # 7) Historial y estado previo
        self.registros         = []
        self.last_state        = None
        self.last_chosen_idx   = None

        # buffer para normalizar V
        self.ppo_val_buffer = collections.deque(maxlen=100)

    def add_record(self, registro: dict):
        """
        1) Añade registro al historial.
        2) Si hubo apuesta previa, ajusta wager_value (500/5000), calcula reward neto
           (Δsaldo / stake) y drawdown, almacena transición en DQN y PPO, y entrena online.
        3) Siempre actualiza self.last_state y self.current_balance.
        """
        import numpy as np

        # ——— 1) Historial ———
        self.registros.append(registro)
        if len(self.registros) > self.window_lstm:
            self.registros.pop(0)

        # ——— 2) Estado actual ———
        saldo_hist = [r.get("saldo", 0.0) for r in self.registros[-self.window_rl:]]
        vel_hist   = [r.get("velocity", 0.0) for r in self.registros[-self.window_rl:]]
        win_times  = [r.get("ganancia", 0.0) > 0.0 for r in self.registros[-self.window_rl:]]
        current_state = self._build_state_vector(registro, saldo_hist, vel_hist, win_times)

        # ——— 3) Si existía acción previa ———
        if self.last_state is not None and self.last_chosen_idx is not None:
            # 3.1) Ajustamos el valor de ficha (500 ó 5000) según el saldo actual
            self._update_wager_value()

            # 3.2) Cuántas fichas apostó la vez anterior
            monto_fichas = (self.last_chosen_idx % MONTO_MAX) + 1
            # stake en valor monetario
            stake = monto_fichas * self.wager_value

            # 3.3) Ganancia neta = cambio real de saldo
            prev_saldo = float(registro.get("saldo_anterior", 0.0))
            new_saldo  = float(registro.get("saldo", 0.0))
            net_gain   = new_saldo - prev_saldo

            # 3.4) Recompensa normalizada en [-1,1]
            reward = np.clip(net_gain / stake, -1.0, 1.0)
            done   = False

            # 3.5) Drawdown para PPO shaping
            peak     = max(saldo_hist + [1e-6])
            drawdown = (peak - saldo_hist[-1]) / peak if peak > 0 else 0.0

            # — DQN: almacenar transición y entrenar
            self.rl_agent_dqn.store_transition(
                state      = np.array(self.last_state, dtype=np.float32),
                action     = int(self.last_chosen_idx),
                raw_reward = reward,
                next_state = np.array(current_state, dtype=np.float32),
                done       = done
            )
            if self.rl_agent_dqn.memory.size() >= 32:
                loss_dqn = self.rl_agent_dqn.train(batch_size=32)
                print(f"[DQN TRAIN] loss = {loss_dqn:.4f}")

            # — PPO: almacenar transición y entrenar
            self.rl_agent_ppo.store_transition(
                state     = np.array(self.last_state, dtype=np.float32),
                action    = int(self.last_chosen_idx),
                log_prob  = self.last_ppo_logprob,
                reward    = reward,
                done      = done,
                drawdown  = drawdown
            )
            if len(self.rl_agent_ppo.buffer_states) >= 16:
                pl, vl, ent = self.rl_agent_ppo.update()
                print(f"[PPO TRAIN] policy_loss={pl:.4f} | value_loss={vl:.4f} | entropy={ent:.4f}")

        # ——— 4) Actualizar estado previo y balance ———
        self.last_state      = current_state
        self.current_balance = float(registro.get("saldo", 0.0))

    def _build_state_vector(self, registro, saldo_history, vel_history, win_times):
        """
        Construye un vector de estado de tamaño fijo (19) para DQN/PPO:
        1 número actual normalizado
        1 jugadores normalizado
        5 velocidades (últimos 5)
        5 saldos (últimos 5, normalizados)
        1 drawdown actual
        1 tiempo desde última victoria (normalizado a max 5 min)
        2 dirección one-hot
        3 últimos números normalizados
        """
        vec = []

        # 1) Número actual normalizado (0–36)
        numero = registro.get("numero", 0)
        vec.append(numero / 36.0)

        # 2) Jugadores presentes (0–MAX_JUGADORES)
        jugadores = registro.get("jugadores_presentes", 0)
        vec.append(min(jugadores, MAX_JUGADORES) / MAX_JUGADORES)

        # 3) Velocidades (últimos 5)
        last_vels = vel_history[-5:]
        if len(last_vels) < 5:
            last_vels = [0.0] * (5 - len(last_vels)) + last_vels
        vec.extend(last_vels)

        # 4) Saldos históricos (últimos 5, normalizados)
        last_saldos = saldo_history[-5:]
        if len(last_saldos) < 5:
            last_saldos = [0.0] * (5 - len(last_saldos)) + last_saldos
        max_saldo = max(last_saldos + [1e-6])
        norm_saldos = [s / max_saldo for s in last_saldos]
        vec.extend(norm_saldos)

        # 5) Drawdown actual
        peak = max(saldo_history + [1e-6])
        dd = (peak - saldo_history[-1]) / peak if peak > 0 else 0.0
        vec.append(dd)

        # 6) Tiempo desde última victoria (último registro con ganancia>0)
        t_win = 300.0  # 5 minutos en segundos
        for r in reversed(self.registros):
            if r.get("ganancia", 0.0) > 0.0:
                # parsear fecha y calcular diferencia:
                fmt = "%Y-%m-%d %H:%M:%S"
                try:
                    t0 = time.mktime(time.strptime(r["fecha_hora"], fmt))
                    t_win = min(time.time() - t0, 300.0)
                except:
                    t_win = 300.0
                break
        vec.append(t_win / 300.0)  # normalizado a [0,1]

        # 7) Dirección one-hot: ""->[0,0], "horario"->[1,0], "antihorario"->[0,1]
        direction = registro.get("direction", "")
        if direction == "horario":
            vec.extend([1.0, 0.0])
        elif direction == "antihorario":
            vec.extend([0.0, 1.0])
        else:
            vec.extend([0.0, 0.0])

        # 8) Últimos 3 números históricos normalizados
        nums = registro.get("numero_hist", [])[-3:]
        if len(nums) < 3:
            nums = [0] * (3 - len(nums)) + nums
        vec.extend([n / 36.0 for n in nums])

        return np.array(vec, dtype=np.float32)


    def bet_amount(self, strategy, last_win):
        confidence = abs(self.last_q_max - self.last_v_max)
        base = self.base_bet
        return int(base * (1 + confidence * self.bet_scale))
    

    def choose(self) -> tuple:
        """
        1) DQN → idx + Q_norm(s,idx)
        2) PPO → idx + V_norm(s) con rango propio y protección NaN
        3) Confianza = |Q_norm - V_norm|
        4) Si confianza >= confidence_threshold → PPO, else DQN
        5) Bet-sizing proporcional a la confianza (número de fichas)
        6) Devolver (cat, monto, etiqueta)
        """
        import numpy as np

        if self.last_state is None:
            print("[ERROR] No hay estado válido para elegir acción.")
            return StrategyManagerDL.CATEGORIES[0], 1, "sin_estado"

        s = self.last_state

        # ——— DQN ———
        try:
            dqn_idx = self.rl_agent_dqn.select_action(s)
            q_vals  = self.rl_agent_dqn.q_network.predict(s[None], verbose=0)[0]
        except Exception as e:
            print(f"[ERROR][DQN] fallo al predecir Q: {e}")
            return StrategyManagerDL.CATEGORIES[0], 1, "error_dqn"

        q_min, q_max = np.min(q_vals), np.max(q_vals)
        ptp_q = max(q_max - q_min, 1e-8)
        q_norm = (q_vals[dqn_idx] - q_min) / ptp_q

        # ——— PPO ———
        try:
            ppo_idx, ppo_logp, ppo_val = self.rl_agent_ppo.select_action(s)
            v = float(ppo_val)
        except Exception as e:
            print(f"[ERROR][PPO] fallo al seleccionar acción: {e}")
            # Fallback inmediato a DQN
            fichas = max(1, min(int(q_norm * MONTO_MAX), MONTO_MAX))
            cat    = StrategyManagerDL.CATEGORIES[dqn_idx // MONTO_MAX]
            return cat, fichas, "dqn_fallback"

        # ——— Actualizar y normalizar V con su propio rango ———
        # Inicializar v_min/v_max si fuera la primera vez
        if not hasattr(self, "v_min"):
            self.v_min = v
            self.v_max = v

        self.v_min = min(self.v_min, v)
        self.v_max = max(self.v_max, v)

        # Proteger contra división por cero o v NaN
        if np.isnan(v) or self.v_max - self.v_min <= 0:
            v_norm = 0.0
        else:
            v_norm = (v - self.v_min) / (self.v_max - self.v_min)

        print(f"[DEBUG][V] v = {v:.4f}, v_min = {self.v_min:.4f}, v_max = {self.v_max:.4f}, v_norm = {v_norm:.4f}")

        # ——— Confianza y decisión ———
        confidence = abs(q_norm - v_norm)
        if not np.isfinite(confidence):
            confidence = 0.0

        if confidence >= self.confidence_threshold:
            chosen_idx, algo = ppo_idx, 'ppo'
        else:
            chosen_idx, algo = dqn_idx, 'dqn'

        # Validar índice
        if not (0 <= chosen_idx < self.action_dim):
            print(f"[ERROR] índice de acción fuera de rango: {chosen_idx}")
            chosen_idx = 0

        # ——— Bet-sizing proporcional a confianza ———
        # Calcula valor total de apuesta (en dinero) escalonado por confianza
        raw_value = confidence * MONTO_MAX * self.wager_value
        if not np.isfinite(raw_value):
            raw_value = self.wager_value  # apuesta mínima en dinero

        total_bet_value = max(self.wager_value,
                            min(int(raw_value),
                                MONTO_MAX * self.wager_value))
        # Convierte valor total en número de fichas
        monto = max(1, total_bet_value // self.wager_value)

        # ——— Mapear categoría ———
        cat = StrategyManagerDL.CATEGORIES[chosen_idx // MONTO_MAX]

        # ——— Guardar para add_record() ———
        self.last_chosen_idx  = chosen_idx
        self.last_algo        = algo
        self.last_ppo_logprob = ppo_logp
        self.last_ppo_value   = v
        self.last_q_max       = q_max
        self.last_v_max       = v

        print(f"[COMPARE] Q_norm={q_norm:.4f}, V_norm={v_norm:.4f}, conf={confidence:.4f}")
        print(f"[CHOICE] {algo.upper()} → idx={chosen_idx}, cat={cat}, monto={monto}")

        return cat, monto, f'dqn-ppo[{algo}]'

    def _update_wager_value(self):
        """
        Ajusta self.wager_value a 500 o 5000 según el current_balance y el umbral 50_000.
        """
        if hasattr(self, "current_balance") and self.current_balance >= 50_000:
            self.wager_value = 5_000
        else:
            self.wager_value = 500
