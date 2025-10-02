# wplay/data/feature_engineer_deep.py

import os
import pandas as pd
import numpy as np
from datetime import datetime
from wplay.utils.chaos import compute_hurst, compute_lyapunov, shannon_entropy
from wplay.utils.constants import MAX_INTERVAL, CHAOS_WINDOW_SIZE, MIN_CHAOS_POINTS
from wplay.utils.time_features import get_time_sin_cos

# Constantes para normalización de features físicas y temporales
MAX_JUGADORES = 20     # Máximo estimado de jugadores presentes
MAX_VELOCITY   = 100.0 # Velocidad máxima estimada de la bola
MAX_INTERVAL   = 60.0  # Máximo intervalo (s) entre giros considerado válido

class FeatureEngineerDeep:
    """
    Ingeniería de características avanzada para:
      • Modelos secuenciales (LSTM, Transformer)
      • Aprendizaje por refuerzo (DQN, PPO)

    A partir de clean_csv genera:
      - lstm_csv: secuencias de longitud `window` con features + etiqueta categórica
      - rl_csv: transiciones (state → next_state) con acción y reward
    """

    # Categorías de apuesta utilizadas tanto en LSTM como en RL
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(
        self,
        clean_csv: str,
        lstm_csv: str,
        rl_csv: str,
        window: int = 50,
        window_rl: int = 10,
        done_threshold: float = MAX_INTERVAL  # ⬆️ mod.: umbral configurable (en segundos)
    ):
        """
        :param clean_csv: Ruta al CSV limpio generado por DataCleaner
        :param lstm_csv:  Ruta de salida para los datos de LSTM/Transformer
        :param rl_csv:    Ruta de salida para las transiciones RL
        :param window:    Longitud de la secuencia para LSTM/Transformer
        :param window_rl: Tamaño de la ventana histórica para construir estados RL
        :param done_threshold: Tiempo máximo entre transiciones para considerar episodio activo
        """
        self.clean_csv      = clean_csv
        self.lstm_csv       = lstm_csv
        self.rl_csv         = rl_csv
        self.window         = window
        self.window_rl      = window_rl
        self.done_threshold = done_threshold  # ⬆️ mod.


    def _num_to_cat(self, n: int) -> str:
        """
        Convierte un número de ruleta a categoría de color/paridad:
          - 0  → "0"
          - rojo/ne­gro
          - par/impar
        """
        if n == 0:
            return "0"
        if n in {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}:
            return "rojo"
        if n % 2 == 0:
            return "par"
        return "impar"

    def transform(self) -> None:
        """
        Lee clean_csv, genera dos CSVs:
        1) lstm_csv: secuencias deslizantes + etiqueta numérica ("numero") y categórica ("target_cat")
        2) rl_csv: transiciones state→action→next_state + reward
        """
        df = pd.read_csv(self.clean_csv, parse_dates=["fecha_hora"])
        # — normalizaciones básicas —
        df['saldo']    = pd.to_numeric(df.get('saldo', 0),    errors='coerce').fillna(0.0)
        df['ganancia'] = pd.to_numeric(df.get('ganancia',0),  errors='coerce').fillna(0.0)
        df['strategy_prev'] = df.get('strategy', '').shift(1).fillna('none')
        valid_strats = set(self.CATEGORIES + ['none'])
        df['strategy_prev'] = (df['strategy_prev']
            .astype(str)
            .apply(lambda s: s if s in valid_strats else 'other'))
        strat_vals = sorted(valid_strats | {'other'})
        saldos, ganancias = df['saldo'].tolist(), df['ganancia'].tolist()

        # — señales caóticas usando constantes y mínimo de puntos —
        df['hurst'] = (
            df['ganancia']
            .rolling(self.window, min_periods=MIN_CHAOS_POINTS)
            .apply(lambda x: compute_hurst(x.to_numpy()), raw=False)
            .fillna(0.5)
        )
        df['lyapunov'] = (
            df['numero']
            .rolling(self.window, min_periods=MIN_CHAOS_POINTS)
            .apply(lambda x: compute_lyapunov(x.to_numpy()), raw=False)
            .fillna(0.0)
        )
        df['entropy'] = (
            df['numero']
            .rolling(self.window, min_periods=MIN_CHAOS_POINTS)
            .apply(lambda x: shannon_entropy(x.to_numpy()), raw=False)
            .fillna(0.0)
        )

        # — Parte A: LSTM/Transformer —
        rows_lstm, reds = [], {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        for idx in range(self.window, len(df)):
            row, dt = df.iloc[idx], df.iloc[idx]['fecha_hora']
            prev_dt = df.iloc[idx-1]['fecha_hora']
            delta = min((dt - prev_dt).total_seconds(), MAX_INTERVAL)
            time_between = delta / MAX_INTERVAL
            hour_sin, hour_cos, dow_sin, dow_cos = get_time_sin_cos(dt.timestamp())

            # minutos como ciclo simple
            min_sin = np.sin(2*np.pi * dt.minute / 60)
            min_cos = np.cos(2*np.pi * dt.minute / 60)

            # ventana de velocidad y jugadores
            win_vel = df['velocity'].iloc[idx-self.window:idx].fillna(0.0)
            vel_mean, vel_std = win_vel.mean()/MAX_VELOCITY, win_vel.std()/MAX_VELOCITY
            win_jug = df['jugadores_presentes'].iloc[idx-self.window:idx].fillna(0)
            jug_mean, jug_std = win_jug.mean()/MAX_JUGADORES, win_jug.std()/MAX_JUGADORES

            # aceleraciones y skew
            accel = win_vel.diff().fillna(0).to_numpy()
            accel2 = np.diff(accel, prepend=0)
            accel_mean, accel2_mean = accel.mean(), accel2.mean()
            players_skew = win_jug.skew()

            # conteos y drawdown
            hist = df['numero'].iloc[idx-self.window:idx].astype(int)
            count_red = (hist.isin(reds).sum())/self.window
            count_par = ((hist % 2 == 0) & (hist != 0)).sum()/self.window
            slice_sal = saldos[idx-self.window:idx]
            peak, curr = max(slice_sal + [1e-6]), saldos[idx]
            drawdown = min(max((peak-curr)/peak,0.0),1.0)

            # tiempo desde última ganancia
            t_win = next(((dt - df.iloc[j]['fecha_hora']).total_seconds() for j in range(idx-1, idx-self.window-1, -1)
                          if ganancias[j]>0), 300.0)
            time_since_win = min(t_win, 300.0)/300.0

            # one‐hot previa y streaks
            sp = row['strategy_prev']
            strat_ohe = {f"strat_{s}": int(sp==s) for s in strat_vals}
            streak_red = row.get('streak_rojo',0)/self.window
            streak_win = row.get('streak_win',0)/self.window

            # ensamblaje
            rows_lstm.append({
                **strat_ohe,
                "velocity": row['velocity']/MAX_VELOCITY,
                "direction_bin": int(row['direction']=="horario"),
                "jugadores": min(row['jugadores_presentes']/MAX_JUGADORES,1.0),
                "time_between": time_between,
                "hour_sin": hour_sin, "hour_cos": hour_cos,
                "min_sin": min_sin,   "min_cos": min_cos,
                "dow_sin": dow_sin,   "dow_cos": dow_cos,
                "vel_mean": vel_mean, "vel_std": vel_std,
                "accel_mean": accel_mean, "accel2_mean": accel2_mean,
                "accel_skew": float(pd.Series(accel).skew()),
                "jug_mean": jug_mean, "jug_std": jug_std,
                "players_skew": players_skew,
                "count_red": count_red, "count_black": 1-count_red,
                "count_par": count_par, "count_impar": 1-count_par,
                "drawdown": drawdown,
                "time_since_win": time_since_win,
                "streak_red": streak_red, "streak_win": streak_win,
                # nuevas chaos‐features
                "hurst":    float(df.at[idx,'hurst']),
                "lyapunov": float(df.at[idx,'lyapunov']),
                "entropy":  float(df.at[idx,'entropy']),
                # etiquetas
                "numero":     int(row['numero']),
                "target_cat": self._num_to_cat(int(row['numero']))
            })

        out_df_lstm = pd.DataFrame(rows_lstm)
        os.makedirs(os.path.dirname(self.lstm_csv) or ".", exist_ok=True)
        out_df_lstm.to_csv(self.lstm_csv, index=False)
        print(f"[✓] LSTM sequences ({len(out_df_lstm)}) guardadas en '{self.lstm_csv}'")
         # ─────────── Parte B: Generar CSV de transiciones para RL ─────────── #
        registros = []
        hist_nums = []
        for idx in range(len(df) - 1):
            actual    = df.iloc[idx]
            siguiente = df.iloc[idx+1]
            hist_nums.append(int(actual['numero']))

            if len(hist_nums) < self.window_rl:
                continue

            # Construir estado actual
            window_hist = hist_nums[-self.window_rl:]
            state = {
                **{f"pos_{i}": n/36.0 for i,n in enumerate(window_hist)},
                "count_red": sum(n in reds for n in window_hist)/self.window_rl,
                "count_par": sum((n%2==0 and n!=0) for n in window_hist)/self.window_rl,
                "velocidad": actual['velocity']/MAX_VELOCITY,
                "jugadores": actual['jugadores_presentes']/MAX_JUGADORES,
                "time_between": min((actual['fecha_hora'] - (df.iloc[idx-1]['fecha_hora'] if idx>0 else actual['fecha_hora'])).total_seconds(), self.done_threshold) / self.done_threshold,
                "hour_sin": np.sin(2*np.pi * (actual['fecha_hora'].hour*3600 + actual['fecha_hora'].minute*60 + actual['fecha_hora'].second) / 86400),
                "hour_cos": np.cos(2*np.pi * (actual['fecha_hora'].hour*3600 + actual['fecha_hora'].minute*60 + actual['fecha_hora'].second) / 86400),
                "drawdown": min(max((max(saldos[idx-self.window_rl+1:idx+1] + [1e-6]) - saldos[idx])/max(saldos[idx-self.window_rl+1:idx+1] + [1e-6]), 0),1),
                "time_since_win": (lambda dt, wins, times: min(((dt - times[j]).total_seconds() for j in range(len(wins)-1, -1, -1) if wins[j]), default=300.0)/300.0)(
                    actual['fecha_hora'],
                    ganancias[idx-self.window_rl+1:idx+1],
                    df['fecha_hora'].iloc[idx-self.window_rl+1:idx+1].tolist()
                )
            }

            # Construir transición
            reward = 1.0 if self._num_to_cat(int(actual['numero'])) == self._num_to_cat(int(siguiente['numero'])) else -1.0
            done   = (siguiente['fecha_hora'] - actual['fecha_hora']).total_seconds() > self.done_threshold

            registros.append({
                **state,
                "action": (
                    self.CATEGORIES.index(self._num_to_cat(int(actual['numero'])))
                    if actual['numero'] != 0 else -1
                ),
                "reward": reward,
                "done": done
            })

        # — Filtrar sólo las 19 features que usaremos en producción —
        rl_features = [
            *[f"pos_{i}" for i in range(self.window_rl)],  # pos_0 … pos_9
            "count_red", "count_par",
            "velocidad", "jugadores",
            "time_between", "hour_sin", "hour_cos",
            "drawdown", "time_since_win"
        ]

        df_rl = pd.DataFrame(registros)
        df_rl = df_rl[rl_features + ["action", "reward", "done"]]

        os.makedirs(os.path.dirname(self.rl_csv) or ".", exist_ok=True)
        df_rl.to_csv(self.rl_csv, index=False)
        print(f"[✓] RL transitions ({len(df_rl)}) guardadas en '{self.rl_csv}'")