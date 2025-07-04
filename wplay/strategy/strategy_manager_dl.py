# wplay/strategy/strategy_manager_dl.py

import os
import time
import logging
from typing import Optional
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from keras.models import load_model

from wplay.data.utils import safe_load_model
from wplay.strategy.constants import MONTO_MAX, MAX_VELOCITY
from wplay.strategy.meta_strategy_selector import MetaStrategySelector
from wplay.features import FeaturePipeline
from wplay.training.rl_trainer import RLTrainer  # <-- Add this import, adjust path if needed

class StrategyManagerDL:
    """
    Estrategia híbrida DQN + PPO con estado enriquecido:
      - DQN y PPO aprenden en paralelo.
      - Meta‐selector combina sus señales.
      - Control de drawdown y ajuste de apuestas.
    """
    _executor = ThreadPoolExecutor(max_workers=2)
    CATEGORIES = ["rojo","negro","par","impar","1-18","19-36","skip"]

    def __init__(
        self,
        lstm_path: str,
        rl_agent_dqn,
        rl_agent_ppo,
        rl_trainer,
        external_classifier=None,
        hypernet=None,                # 👈 Recibimos aquí
        hp=None,                      # 👈 (opcional)
        # — parámetros de ventana —
        window_lstm: int = 50,
        window_rl:   int = 10,
        # — parámetros de apuesta / mezcla —
        confidence_threshold: float = 0.5,
        bet_scale_factor:     float = 1.0,
        wager_value:          int   = 500,
        # — hiperparámetros de skip inteligente —
        max_loss_streak:         int   = 3,
        skip_momentum_window:    int   = 10,
        skip_momentum_threshold: float = -0.1,
        skip_entropy_threshold:  float = 1.0,
        reactivation_threshold:  float = None,
        # — ε-greedy interno —
        tau:            float = 0.5,
        epsilon:        float = 0.1,
        min_epsilon:    float = 0.01,
        max_epsilon:    float = 0.5,
        alpha:          float = 0.0005,
        mix_ext_weight: float = 0.3,
        # — resto de argumentos originales —
        model_dir:    str  = None,
        state_dim_dqn: int = None,
        meta_ucb_c:   float  = 1.0,
        meta_use_ts:  bool  = True,
    ):
        # Guardar rl_trainer, hp y hypernet para luego
        self.rl_trainer  = rl_trainer
        self.hp          = hp or getattr(rl_trainer, 'hp', None)
        self.hypernet    = hypernet or getattr(rl_trainer, 'hypernet', None)

        # Umbrales para MetaStrategySelector
        self.L_thresh    = getattr(self.hp, 'L_thresh', 0.3)
        self.H_thresh    = getattr(self.hp, 'H_thresh', 0.7)
        self.ENT_thresh  = getattr(self.hp, 'ENT_thresh', 1.5)

        # — resto de tu __init__ sin cambios, empieza aquí —
        # 0) Clasificador externo o dummy uniforme de 3 clases
        from sklearn.dummy import DummyClassifier
        import numpy as np
        if external_classifier is None:
            from sklearn.multiclass import OneVsRestClassifier
            from sklearn.linear_model import LogisticRegression
            base = LogisticRegression(
                multi_class='multinomial',
                solver='lbfgs',
                max_iter=1000
            )
            dummy3 = OneVsRestClassifier(base)
            X = [[0]] * 3
            y = [0, 1, 2]
            dummy3.fit(X, y)
            self.external_classifier = dummy3
        else:
            self.external_classifier = external_classifier
            try:
                _ = self.external_classifier.predict_proba(
                    np.zeros((1, state_dim_dqn or 1))
                )
            except Exception:
                logging.warning(
                    "[StrategyManagerDL] external_classifier inválido, usando uniforme."
                )
                dummy = DummyClassifier(strategy="uniform")
                dummy.fit([[0]], [0])
                self.external_classifier = dummy

        # 1) Directorio de modelos
        self.model_dir = model_dir or os.path.dirname(os.path.abspath(lstm_path))
        logging.info(f"[StrategyManagerDL] model_dir = '{self.model_dir}'")
        self.current_number = None

        # 2) Ventanas
        self.window_lstm = window_lstm
        self.window_rl   = window_rl
        self._hips       = []

        # 3) Mapa de acciones
        self.CATEGORIES = ["rojo","negro","par","impar","1-18","19-36","skip"]
        self.action_map = [
            (cat, f)
            for cat in self.CATEGORIES
            for f in range(1, MONTO_MAX + 1)
        ] + [("skip", 0)]
        self.action_dim = len(self.action_map)


        # ------------------------------------------------------------------
        # 4) EXTRACCIÓN Y FILTRADO DE COLUMNAS ANTES DE FITEAR PIPELINE ----
        # ------------------------------------------------------------------

        data_dir = os.path.abspath(os.path.join(self.model_dir, os.pardir, "data"))
        csv_path = os.path.join(data_dir, "rl_input.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No encontré rl_input.csv en {csv_path}")
        df_offline = pd.read_csv(csv_path)

        if "reward" not in df_offline.columns:
            raise KeyError("El CSV debe contener columna 'reward'")

        raw_feats = [
            c for c in df_offline.columns
            if c not in ("action", "reward", "done") and not c.startswith("next_")
        ]

        drop_low_var = [
            'dir_bin',
            'strat_1-18','strat_19-36','strat_impar','strat_negro',
            'strat_none','strat_other','strat_par','strat_rojo'
        ]
        drop_corr    = ['count_black','count_imp']
        filtered_feats = [
            c for c in raw_feats
            if c not in drop_low_var + drop_corr
        ]
        numeric_feats = filtered_feats
        categ_feats   = []

        logging.info(
            f"[StrategyManagerDL] Usando features filtrados "
            f"({len(numeric_feats)}): {numeric_feats}"
        )

        # 4.3) Pipeline de features
        self.feature_pipe = FeaturePipeline(numeric_feats, categ_feats)
        self.feature_pipe.fit_offline(
            df_offline[numeric_feats + ["reward", "action", "done"]]
        )

        # 4.4) Features finales e índices
        self.final_feats = self.feature_pipe.final_feats
        self.final_idx   = self.feature_pipe.get_final_indices()

        # 4.5) Dimensión total
        self.state_dim_total = len(self.final_feats)

        # 4.6) Dimensión para DQN
        self.state_dim_dqn = (
            self.state_dim_total if state_dim_dqn is None else state_dim_dqn
        )
        if self.state_dim_dqn > self.state_dim_total:
            raise ValueError(
                f"state_dim_dqn ({self.state_dim_dqn}) no puede exceder "
                f"state_dim_total ({self.state_dim_total})"
            )

        # DQN debe usar exactamente las primeras state_dim_dqn columnas
        self.dqn_idx = list(range(self.state_dim_dqn))
        # ------------------------------------------------------------------
        # 5) Inicializar agentes con dimensiones correctas ----------------
        # ------------------------------------------------------------------

        self.rl_agent_dqn = rl_agent_dqn
        self.rl_agent_ppo = rl_agent_ppo
        for ag in (self.rl_agent_dqn, self.rl_agent_ppo):
            ag.action_dim = self.action_dim

        # DQN: solo ve las primeras dimensiones
        self.rl_agent_dqn.state_dim = self.state_dim_dqn
        self.rl_agent_dqn.rebuild_network(self.state_dim_dqn)

        # PPO: ve el estado completo
        self.rl_agent_ppo.state_dim = self.state_dim_total
        self.rl_agent_ppo.rebuild_network(self.state_dim_total)
        self.rl_agent_ppo.actor.build(input_shape=(None, self.state_dim_total))
        self.rl_agent_ppo.critic.build(input_shape=(None, self.state_dim_total))

        # ------------------------------------------------------------------
        # 6) Meta‐selector, LSTM y resto de la lógica ----------------------
        # ------------------------------------------------------------------

        self.meta        = None
        self.meta_ucb_c  = meta_ucb_c
        self.meta_use_ts = meta_use_ts

        if lstm_path:
            self.lstm = (
                safe_load_model(lstm_path) if lstm_path.endswith(".h5")
                else load_model(lstm_path)
            )
        else:
            self.lstm = None

        self.confidence_threshold = confidence_threshold
        self.bet_scale_factor     = bet_scale_factor
        self.wager_value          = wager_value

        # Estado interno
        self.registros       = deque(maxlen=self.window_lstm)
        self.last_state      = None
        self.last_state_dqn  = None
        self.last_state_ppo  = None
        self.last_chosen_idx = None
        self.last_algo       = None
        self.last_ppo_logprob= 0.0
        self.current_balance = 0.0
        self.skip_count      = 0
        self.total_records   = 0

        # Skip inteligente & ε‑greedy
        self.max_loss_streak         = max_loss_streak
        self.skip_momentum_window    = skip_momentum_window
        self.skip_momentum_threshold = skip_momentum_threshold
        self.skip_entropy_threshold  = skip_entropy_threshold
        self.reactivation_threshold  = reactivation_threshold or wager_value

        self.tau            = tau
        self.epsilon        = epsilon
        self.min_epsilon    = min_epsilon
        self.max_epsilon    = max_epsilon
        self.alpha          = alpha
        self.mix_ext_weight = mix_ext_weight

        # Buffers y skip_clf
        self._rewards = {k: deque(maxlen=self.window_rl) for k in ("dqn","ppo","skip")}
        for q in self._rewards.values():
            q.append(0.0)
        self.skip_clf = RandomForestClassifier()

      
        self.logger = logging.getLogger(self.__class__.__name__)
        self.restart_every = 10               # reinicio suave cada 10 llamadas a select()
        self.steps_since_restart = 0


    def _rebuild_meta(self):
        """
        Reconstruye el meta-selector con state_dim_total y action_dim,
        usando hypernet y hp, preservando estadísticas.
        """
        # Guardar estado previo
        if self.meta:
            old = {
                'counts': self.meta.counts.copy(),
                'values': self.meta.values.copy(),
                'total_counts': self.meta.total_counts,
                'successes': self.meta.successes.copy(),
                'failures': self.meta.failures.copy(),
                'reward_history': deque(self.meta.reward_history, maxlen=self.meta.window),
                'off_states': deque(self.meta._offline_states, maxlen=self.meta.window),
                'off_idxs': deque(self.meta._offline_idxs, maxlen=self.meta.window),
            }
        else:
            old = None

        # Instanciar MetaStrategySelector con todos los parámetros necesarios
        self.meta = MetaStrategySelector(
            state_dim=self.state_dim_total,
            action_dim=self.action_dim,
            hypernet=self.hypernet,
            hp=self.hp,
            strategy_list=["dqn", "ppo", "skip"],
            model_path=os.path.join(self.model_dir, "meta_strategy_selector.keras"),
            window=self.window_rl,
            ucb_c=self.meta_ucb_c,
            use_ts=self.meta_use_ts,
            L_thresh=self.L_thresh,
            H_thresh=self.H_thresh,
            ENT_thresh=self.ENT_thresh
        )
        self.selector = self.meta
        # Asignar agentes
        self.meta.dqn_agent = self.rl_agent_dqn
        self.meta.ppo_agent = self.rl_agent_ppo

        # Restaurar estadísticas
        if old:
            self.meta.counts          = old['counts']
            self.meta.values          = old['values']
            self.meta.total_counts    = old['total_counts']
            self.meta.successes       = old['successes']
            self.meta.failures        = old['failures']
            self.meta.reward_history  = old['reward_history']
            self.meta._offline_states = old['off_states']
            self.meta._offline_idxs   = old['off_idxs']

        logging.info(
            f"[META] Reconstruido con state_dim_total={self.state_dim_total} "
            f"action_dim={self.action_dim}"
        )


    def _clip_state_dqn(self, state: np.ndarray) -> np.ndarray:
            """
            Recorta el estado completo a las primeras state_dim_dqn dimensiones para DQN.
            """
            if state.shape[-1] != self.state_dim_total:
                raise ValueError(
                    f"State total de dimensión {state.shape[-1]} != esperado {self.state_dim_total}"
                )
            clipped = state[:self.state_dim_dqn]
            if clipped.shape[-1] != self.state_dim_dqn:
                raise ValueError(
                    f"State DQN de dimensión {clipped.shape[-1]} != esperado {self.state_dim_dqn}"
                )
            return clipped.astype(np.float32)
    def _clip_state_ppo(self, state: np.ndarray) -> np.ndarray:
            """
            Recorta el estado completo a las últimas (state_dim_total - state_dim_dqn) dimensiones para PPO.
            """
            start = self.state_dim_dqn
            clipped = state[start:]
            if clipped.shape[-1] + self.state_dim_dqn != self.state_dim_total:
                raise ValueError(
                    f"DQN+PPO dims suman {self.state_dim_dqn + clipped.shape[-1]} != {self.state_dim_total}"
                )
            return clipped.astype(np.float32)

    def add_record(self, registro: dict):
        import numpy as np
        from wplay.utils.chaos import compute_hurst, compute_lyapunov, shannon_entropy
        import time, logging
        from collections import deque

        t0 = time.perf_counter()
       

        # 0) Históricos para features
        recientes   = list(self.registros)[-self.window_rl:]
        saldo_hist  = [r.get("saldo", 0.0)    for r in recientes]
        vel_hist    = [r.get("velocity", 0.0) for r in recientes]
        color_hist  = [r.get("strategy", "")  for r in recientes]
        win_times   = [r.get("ganancia", 0.0) > 0 for r in recientes]

        # Campos mínimos
        for fld in ("delta_time_norm","hour_sin","hour_cos",
                    "dow_sin","dow_cos","accel_mean","accel_std",
                    "players_mean","players_std"):
            registro.setdefault(fld, 0.0)

        # Caos
        registro.setdefault("hurst",   compute_hurst(vel_hist))
        registro.setdefault("lyapunov",compute_lyapunov(vel_hist))
        registro.setdefault("entropy", shannon_entropy(vel_hist))

        # 1) Construir vector vivo
        current_state = self._build_state_vector(
            registro, saldo_hist, vel_hist, color_hist, win_times
        )
         
        # 1.5) Guardar estado para entrenamiento del skip_clf
        registro['state'] = current_state.copy()

        # 2) Padding / truncate
        live_dim = current_state.shape[-1]
        if live_dim < self.state_dim_total:
            pad = np.zeros(self.state_dim_total - live_dim, dtype=np.float32)
            current_state = np.concatenate([current_state, pad], axis=0)
        elif live_dim > self.state_dim_total:
            current_state = current_state[:self.state_dim_total]

        # 3) Registrar en memoria
        self.registros.append(registro)
        self.current_number    = registro["numero"]
        self.last_state        = current_state
        self.last_state_dqn    = self._clip_state_dqn(current_state)
        self.last_state_ppo    = current_state
        self.current_balance   = float(registro.get("saldo", 0.0))
        self._update_wager_value()
        self.total_records    += 1

        # 4) Acumular reward y actualizar racha
        strat = registro.get("strategy")
        rew   = registro.get("reward", 0.0)
        if rew > 0:
            self.loss_streak = 0
        else:
            self.loss_streak = getattr(self, 'loss_streak', 0) + 1


        if strat == "skip":
            self.skip_count += 1
            self._rewards.setdefault('skip', deque(maxlen=self.window_rl)).append(rew)
            # +1 streak si gana, reset al perder
            self.current_streak = (getattr(self, 'current_streak', 0) + 1) if rew > 0 else 0

        elif strat in ("dqn", "ppo"):
            self._rewards[strat].append(rew)
            self.current_streak = (getattr(self, 'current_streak', 0) + 1) if rew > 0 else 0

        else:
            self.current_streak = 0

        logging.debug(
            f"[ADD_RECORD] Procesado en {time.perf_counter()-t0:.3f}s — "
            f"estrat={strat} rew={rew:.3f} streak={self.current_streak}"
        )
        # NO hay retorno ni guardado en BD aquí; el flujo principal lo hace una vez.


    def _simulate_gain(self, numero, cat, fichas, wager_value):
        try:
            _, gain = self.data_collector.compute_gain(numero, cat, 1, wager_value)
            return max(0.0, gain)
        except:
            return 0.0

    def get_dqn_feature_indices(self) -> np.ndarray:
        """
        Devuelve la lista de índices (en el vector full) que corresponden
        a las features que DQN debe usar.
        """
        return np.array(self.final_idx, dtype=int)

    def _build_state_vector(
        self,
        registro: dict,
        saldo_history: list,
        vel_history: list,
        color_history: list,
        win_times: list
    ) -> np.ndarray:
        """
        Construye el vector de estado EXACTAMENTE igual que rl_input.csv,
        rellenando con 0.0 o "" cualquier columna que falte, y luego
        llama a self.feature_pipe.transform().
        """
        import pandas as pd
        import numpy as np
        from datetime import datetime
        from wplay.utils.time_features import get_time_sin_cos
        from wplay.utils.constants import MAX_INTERVAL              # seguirá viniendo de aquí
        from wplay.data.feature_engineer_deep import MAX_JUGADORES, MAX_VELOCITY  # ← FIX

        N = self.window_rl

        # 1) Extraer histórico de los últimos N registros
        hist = list(self.registros)[-N:]
        nums = [int(r.get("numero", 0)) for r in hist]
        times = []
        for r in hist:
            t = r.get("fecha_hora")
            if isinstance(t, str):
                t = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            times.append(t or datetime.now())

        # 2) Generar dict con todas las columnas “state”
        feat = {}
        for i in range(N):
            v = nums[i] if i < len(nums) else 0
            feat[f"pos_{i}"] = v / 36.0

        count_red = sum(1 for v in nums if 1 <= v <= 36 and v % 2 == 1) / max(len(nums), 1)
        count_par = sum(1 for v in nums if 1 <= v <= 36 and v % 2 == 0) / max(len(nums), 1)
        feat["count_red"]   = count_red
        feat["count_black"] = 1.0 - count_red
        feat["count_par"]   = count_par
        feat["count_imp"]   = 1.0 - count_par

        feat["velocidad"] = registro.get("velocity", 0.0) / MAX_VELOCITY
        feat["dir_bin"]   = int(registro.get("direction", "") == "horario")
        feat["jugadores"] = registro.get("jugadores_presentes", 0) / MAX_JUGADORES

        now = registro.get("fecha_hora")
        if isinstance(now, str):
            now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        prev = times[-1] if times else now
        delta = (now - prev).total_seconds() if prev else 0.0
        feat["time_between"] = min(delta, MAX_INTERVAL) / MAX_INTERVAL

        hs, hc, ds, dc = get_time_sin_cos(now.timestamp())
        feat["hour_sin"] = hs
        feat["hour_cos"] = hc
        feat["dow_sin"]  = ds
        feat["dow_cos"]  = dc

        sl   = saldo_history[-N:]
        peak = max(sl) if sl else 1.0
        curr = saldo_history[-1] if saldo_history else peak
        feat["drawdown"] = min(max((peak - curr) / max(peak, 1e-6), 0.0), 1.0)

        last_win = 300.0
        for i in range(len(win_times) - 1, -1, -1):
            if win_times[i]:
                dt = (now - times[i]).total_seconds()
                last_win = min(dt, 300.0)
                break
        feat["time_since_win"] = last_win / 300.0

        prev_strat = registro.get("strategy", "")
        for s in self.CATEGORIES:
            feat[f"strat_{s}"] = int(prev_strat == s)

        for k, v in registro.items():
            if k.startswith("next_") or k in ("action", "reward", "done"):
                feat[k] = v

        for col in self.feature_pipe.numeric_feats:
            feat.setdefault(col, 0.0)
        for col in self.feature_pipe.categ_feats:
            feat.setdefault(col, "")

       

        df1 = pd.DataFrame([feat])
        state_arr = self.feature_pipe.transform(df1)
        if state_arr.ndim != 2 or state_arr.shape[1] != self.state_dim_total:
            raise AssertionError(
                f"[_build_state_vector] Esperaba (1,{self.state_dim_total}), "
                f"pero pipeline devolvió {state_arr.shape}"
            )

        full_state = state_arr.flatten().astype(np.float32)
        if self.total_records and self.total_records % 1000 == 0:
            mu, sd = full_state.mean(), full_state.std()
            logging.debug(f"[State Drift] paso={self.total_records}, mean={mu:.4f}, std={sd:.4f}")
        return full_state



    def get_dqn_feature_indices(self) -> list[int]:
        """
        Devuelve la lista de índices dentro del vector de estado completo
        que corresponden a las features que utiliza DQN en el preentrenamiento offline.
        """
        # Si estás usando un FeaturePipeline:
        if hasattr(self, "feature_pipe") and hasattr(self.feature_pipe, "get_final_indices"):
            # El pipeline ya contiene la lógica de varianza/correlación
            return self.feature_pipe.get_final_indices()
        # Si en tu init guardaste las columnas offline en self.feature_cols:
        if hasattr(self, "feature_cols"):
            # Construye el vector completo de nombres de feature en el mismo orden
            all_feats = self._all_state_feature_names  # DEBES tener esta lista con los 55 nombres en orden
            return [all_feats.index(c) for c in self.feature_cols]

        # Fallback: asume que usa todas las features en orden
        raise RuntimeError("No puedo determinar los índices DQN: ni feature_pipe ni feature_cols presentes")
    def select(
        self,
        state: Optional[np.ndarray] = None,
        return_soft: bool = False
    ) -> tuple:
        """
        Selección híbrida DQN + PPO + skip, con protección robusta y debug detallado.
        """
        import numpy as np
        import logging

        print("=== ENTERED select() ===")
        log = logging.getLogger(self.__class__.__name__)

        strategies = ['dqn', 'ppo', 'skip']
        n_strat    = len(strategies)

        # 1) Obtener state_vec
        if state is None:
            if self.last_state is None:
                uniform3 = np.ones(n_strat, dtype=np.float32) / n_strat
                return ("skip", 0, "skip", uniform3) if return_soft else ("skip", 0, "skip")
            state_vec = self.last_state
        else:
            arr = np.array(state, dtype=np.float32)
            state_vec = arr.flatten() if (arr.ndim == 2 and arr.shape[0] == 1) else arr

        L = state_vec.shape[-1]
        log.debug(f"[SELECT] state_vec.len={L}")

        # 2) Construir state_dqn / state_full
        if L == self.state_dim_total:
            state_full = state_vec
            state_dqn  = state_full[self.dqn_idx]
        elif L == self.state_dim_dqn:
            state_dqn  = state_vec
            pad        = np.zeros(self.state_dim_total - self.state_dim_dqn, dtype=np.float32)
            state_full = np.concatenate([state_dqn, pad], axis=0)
        else:
            raise ValueError(f"[SELECT] dimensión inválida: {L}")

        # 3) Propuestas de DQN y PPO
        idx_dqn = self.rl_agent_dqn.select_action(state_dqn)
        out_ppo = self.rl_agent_ppo.select_action(state_full)
        idx_ppo = int(out_ppo[0]) if isinstance(out_ppo, tuple) else int(out_ppo)

        # 4) Simular ganancias
        hip_dqn  = self._simulate_gain(self.current_number, *self.action_map[idx_dqn], self.wager_value)
        hip_ppo  = self._simulate_gain(self.current_number, *self.action_map[idx_ppo], self.wager_value)
        avg_skip = float(np.nanmean(self._rewards.get('skip', [0.0])))

        self._rewards['dqn'].append(hip_dqn)
        self._rewards['ppo'].append(hip_ppo)
        self._rewards['skip'].append(avg_skip)

        # 5) p_soft
        temps = np.array([
            np.nanmean(self._rewards['dqn']) + hip_dqn * self.alpha,
            np.nanmean(self._rewards['ppo']) + hip_ppo * self.alpha,
            avg_skip
        ], dtype=np.float32) / self.tau
        exp_t  = np.exp(temps - temps.max())
        p_soft = exp_t / (exp_t.sum() + 1e-8)

        # 6) p_ext
        try:
            p_ext = self.external_classifier.predict_proba(state_dqn.reshape(1, -1))[0]
            if p_ext.size != n_strat:
                raise ValueError("ext size")
        except Exception:
            p_ext = np.ones(n_strat, dtype=np.float32) / n_strat

        # 7) p_int
        try:
            p_bin = self.skip_clf.predict_proba(state_full.reshape(1, -1))[0]
            p_int = np.array([p_bin[0]/2, p_bin[0]/2, p_bin[1]], dtype=np.float32)
        except Exception:
            p_int = np.ones(n_strat, dtype=np.float32) / n_strat

        # 8) p_mix
        mix_w = self.mix_ext_weight
        p_mix = ((1 - mix_w) * p_soft + mix_w * p_ext + mix_w * p_int) / 2.0

        # 9) p_final (ε‑greedy)
        p_final = (1 - self.epsilon) * p_mix + self.epsilon * (1.0 / n_strat)

        # ——— VALIDACIÓN DE p_final ———
        if len(p_final) != n_strat or np.isnan(p_final).any():
            log.error(f"[SELECT] p_final inválido: size={len(p_final)}, nan={np.isnan(p_final).any()}")
            p_final = np.ones(n_strat, dtype=np.float32) / n_strat

        # Re-normaliza por seguridad
        p_final /= (p_final.sum() + 1e-8)

        # 10) Muestreo robusto
        try:
            choice = np.random.choice(strategies, p=p_final)
        except Exception as e:
            log.error(f"[SELECT] muestreo falló: {e}")
            choice = 'skip'

        # 11) Mapear a acción real
        idx_map    = {'dqn': idx_dqn, 'ppo': idx_ppo, 'skip': self.action_dim - 1}
        chosen_idx = idx_map.get(choice, self.action_dim - 1)
        cat, fichas = self.action_map[chosen_idx]
        self.last_chosen_idx = chosen_idx
        self.last_algo       = choice

        # Depuración final
        print(f">>> DEBUG Muestreado choice='{choice}', chosen_idx={chosen_idx}, cat='{cat}', fichas={fichas}'")

        if return_soft:
            return (cat, fichas, choice, p_soft)
        return (cat, fichas, choice)

    def train_skip_classifier(self):
        """
        Entrena en línea un RandomForest para predecir skip vs apostar.
        Usa los últimos registros en self.registros.
        """
        import numpy as np

        # Necesitamos distinguir skip (1) vs apostar (0)
        X = []
        y = []
        for r in list(self.registros):
            # El feature vector que usas en select() es last_state completo
            if 'state' not in r:
                continue
            X.append(r['state'])
            y.append(1 if r.get('strategy')=='skip' else 0)
        if len(X) < 10:
            # Poca muestra, saltamos
            return
        X = np.stack(X, axis=0)
        y = np.array(y)
        self.skip_clf.fit(X, y)

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
    