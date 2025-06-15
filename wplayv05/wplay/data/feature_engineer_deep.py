# wplay/data/feature_engineer_deep.py

import os
import pandas as pd
import numpy as np
from datetime import datetime

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
        window_rl: int = 10
    ):
        """
        :param clean_csv: Ruta al CSV limpio generado por DataCleaner
        :param lstm_csv:  Ruta de salida para los datos de LSTM/Transformer
        :param rl_csv:    Ruta de salida para las transiciones RL
        :param window:    Longitud de la secuencia para LSTM/Transformer
        :param window_rl: Tamaño de la ventana histórica para construir estados RL
        """
        self.clean_csv  = clean_csv
        self.lstm_csv   = lstm_csv
        self.rl_csv     = rl_csv
        self.window     = window
        self.window_rl  = window_rl

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
        # —————— Carga y preparación inicial —————— #
        df = pd.read_csv(self.clean_csv, parse_dates=["fecha_hora"])
        # Asegurar que saldo y ganancia sean numéricos
        df['saldo']    = pd.to_numeric(df.get('saldo', 0),    errors='coerce').fillna(0.0)
        df['ganancia'] = pd.to_numeric(df.get('ganancia',0),  errors='coerce').fillna(0.0)

        # Construir la estrategia previa (shift + filler)
        df['strategy_prev'] = df.get('strategy', '').shift(1).fillna('none')
        valid_strats = set(self.CATEGORIES + ['none'])
        df['strategy_prev'] = df['strategy_prev'].astype(str).apply(
            lambda s: s if s in valid_strats else 'other'
        )
        strat_vals = sorted(valid_strats | {'other'})

        # Listas auxiliares de saldo y ganancia para cálculos posteriores
        saldos    = df['saldo'].tolist()
        ganancias = df['ganancia'].tolist()

        # —————— Parte A: Generar CSV para LSTM/Transformer —————— #
        rows_lstm = []
        reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

        for idx in range(self.window, len(df)):
            row     = df.iloc[idx]
            dt      = row['fecha_hora']
            prev_dt = df.iloc[idx-1]['fecha_hora']

            # 1) Intervalo normalizado entre giros
            delta         = min((dt - prev_dt).total_seconds(), MAX_INTERVAL)
            time_between  = delta / MAX_INTERVAL

            # 2) Codificación cíclica de hora del día
            sec_day       = dt.hour * 3600 + dt.minute * 60 + dt.second
            theta         = 2 * np.pi * sec_day / 86400
            hour_sin, hour_cos = np.sin(theta), np.cos(theta)
            # 2b) Delta_time normalizado
            delta_norm = time_between  # ya calculado
            # 2c) Minuto cíclico
            min_sin = np.sin(2*np.pi * dt.minute / 60)
            min_cos = np.cos(2*np.pi * dt.minute / 60)

            # 3) Estadísticas de ventana de velocidad y jugadores
            win_vel = df['velocity'].iloc[idx-self.window:idx].fillna(0.0)
            vel_mean = win_vel.mean() / MAX_VELOCITY
            vel_std  = win_vel.std()  / MAX_VELOCITY

            win_jug  = df['jugadores_presentes'].iloc[idx-self.window:idx].fillna(0)
            jug_mean = win_jug.mean()   / MAX_JUGADORES
            jug_std  = win_jug.std()    / MAX_JUGADORES
            
            # 3b) Aceleración y aceleración2
            accel    = df['velocity'].iloc[idx-self.window:idx].diff().fillna(0).values
            accel2   = np.diff(accel, prepend=0)
            accel_mean = np.mean(accel)
            accel2_mean= np.mean(accel2)

            # 3c) Players stats skew
            players = df['jugadores_presentes'].iloc[idx-self.window:idx].values
            players_skew = pd.Series(players).skew()


            # 4) Proporciones de color/paridad en la ventana
            hist = df['numero'].iloc[idx-self.window:idx].astype(int)
            count_red   = sum(n in reds for n in hist) / self.window
            count_black = 1.0 - count_red
            count_par   = sum((n % 2 == 0 and n != 0) for n in hist) / self.window
            count_imp   = 1.0 - count_par

            # 5) Drawdown sobre saldo en la ventana
            slice_sal = saldos[idx-self.window:idx]
            peak      = max(slice_sal + [1e-6])
            curr      = saldos[idx]
            drawdown  = min(max((peak - curr) / peak, 0.0), 1.0)

            # 6) Tiempo desde última ganancia (limitado a 300s)
            t_win = 300.0
            for j in range(idx-1, idx-self.window-1, -1):
                if ganancias[j] > 0:
                    t_win = min((dt - df.iloc[j]['fecha_hora']).total_seconds(), 300.0)
                    break
            time_since_win = t_win / 300.0

            # 7) One-hot de estrategia previa
            sp = row['strategy_prev']
            strat_ohe = {f"strat_{s}": int(sp == s) for s in strat_vals}
            
            # 7b) Streaks
            # calculo de streak_rojo y streak_win previamente en DataCleaner y presentes en df
            streak_red = row.get('streak_rojo', 0) / self.window
            streak_win = row.get('streak_win', 0)  / self.window


            # 8) Ensamblar dict de features + etiqueta numérica y categórica
          
            rows_lstm.append({
                **strat_ohe,
                "velocity":       row['velocity']/MAX_VELOCITY,
                "direction_bin":  int(row['direction']=="horario"),
                "jugadores":      min(row['jugadores_presentes']/MAX_JUGADORES,1.0),
                "time_between":   time_between,
                "delta_time":     delta_norm,
                "hour_sin":       hour_sin,
                "hour_cos":       hour_cos,
                "min_sin":        min_sin,
                "min_cos":        min_cos,
                "dow_sin":        df.at[idx,'dow_sin'],
                "dow_cos":        df.at[idx,'dow_cos'],
                "vel_mean":       vel_mean,
                "vel_std":        vel_std,
                "accel_mean":     accel_mean,
                "accel2_mean":    accel2_mean,
                "accel_skew":     float(pd.Series(accel).skew()),
                "jug_mean":       jug_mean,
                "jug_std":        jug_std,
                "players_skew":   players_skew,
                "count_red":      count_red,
                "count_black":    count_black,
                "count_par":      count_par,
                "count_impar":    count_imp,
                "drawdown":       drawdown,
                "time_since_win": time_since_win,
                "streak_red":     streak_red,
                "streak_win":     streak_win,
                "numero":         int(row['numero']),
                "target_cat":     self._num_to_cat(int(row['numero']))
            })
        # Guardar CSV de LSTM/Transformer
        os.makedirs(os.path.dirname(self.lstm_csv) or ".", exist_ok=True)
        pd.DataFrame(rows_lstm).to_csv(self.lstm_csv, index=False)
        print(f"[✓] LSTM input ({len(rows_lstm)} filas) guardado en '{self.lstm_csv}'")

        # —————— Parte B: Generar CSV de transiciones para RL —————— #
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
                "count_red":   sum(n in reds for n in window_hist)/self.window_rl,
                "count_black": 1.0 - sum(n in reds for n in window_hist)/self.window_rl,
                "count_par":   sum((n%2==0 and n!=0) for n in window_hist)/self.window_rl,
                "count_imp":   1.0 - sum((n%2==0 and n!=0) for n in window_hist)/self.window_rl,
                "velocidad":   actual['velocity']/MAX_VELOCITY,
                "dir_bin":     int(actual['direction']=="horario"),
                "jugadores":   actual['jugadores_presentes']/MAX_JUGADORES,
            }

            # Tiempo e hora en estado
            dt_act = actual['fecha_hora']
            prev   = df.iloc[idx-1]['fecha_hora'] if idx>0 else dt_act
            iv     = min((dt_act - prev).total_seconds(), MAX_INTERVAL)/MAX_INTERVAL
            sec    = dt_act.hour*3600 + dt_act.minute*60 + dt_act.second
            th     = 2*np.pi * sec / 86400
            state.update({
                "time_between": iv,
                "hour_sin":     np.sin(th),
                "hour_cos":     np.cos(th),
            })

            # Drawdown y time_since_win en state
            sl2 = saldos[idx-self.window_rl+1:idx+1]
            pk2 = max(sl2+[1e-6]); cs2 = saldos[idx]
            state["drawdown"]        = min(max((pk2-cs2)/pk2, 0),1)
            tw2 = 300.0
            for j in range(idx, idx-self.window_rl, -1):
                if ganancias[j] > 0:
                    tw2 = min((dt_act - df.iloc[j]['fecha_hora']).total_seconds(),300.0)
                    break
            state["time_since_win"] = tw2/300.0

            # Estrategia previa one-hot en state
            sp0 = actual['strategy_prev']
            for s in strat_vals:
                state[f"strat_{s}"] = int(sp0 == s)

            # Construir next_state
            next_hist = window_hist[1:] + [int(siguiente['numero'])]
            next_state = {
                **{f"next_pos_{i}": n/36.0 for i,n in enumerate(next_hist)},
                "next_velocidad": siguiente['velocity']/MAX_VELOCITY,
                "next_dir_bin":   int(siguiente['direction']=="horario"),
                "next_jugadores": siguiente['jugadores_presentes']/MAX_JUGADORES,
            }

            # Drawdown y time_since_win en next_state
            sl3  = saldos[idx-self.window_rl+2:idx+2]
            pk3  = max(sl3+[1e-6]); cs3 = saldos[idx+1]
            next_state["next_drawdown"]        = min(max((pk3-cs3)/pk3,0),1)
            dt_n = siguiente['fecha_hora']
            tw3  = 300.0
            for j in range(idx+1, idx+1-self.window_rl, -1):
                if ganancias[j] > 0:
                    tw3 = min((dt_n - df.iloc[j]['fecha_hora']).total_seconds(),300.0)
                    break
            next_state["next_time_since_win"] = tw3/300.0

            # Strat one-hot en next_state
            for s in strat_vals:
                next_state[f"next_strat_{s}"] = int(sp0 == s)

            # Acción y recompensa
            action_idx = (
                self.CATEGORIES.index(self._num_to_cat(int(actual['numero'])))
                if actual['numero'] != 0 else -1
            )
            reward = 1.0 if action_idx == (
                self.CATEGORIES.index(self._num_to_cat(int(siguiente['numero'])))
                if siguiente['numero'] != 0 else -1
            ) else -1.0

            registros.append({
                **state,
                "action": action_idx,
                "reward": reward,
                **next_state
            })

        # Guardar CSV de transiciones RL
        os.makedirs(os.path.dirname(self.rl_csv) or ".", exist_ok=True)
        pd.DataFrame(registros).to_csv(self.rl_csv, index=False)
        print(f"[✓] RL transitions ({len(registros)}) guardadas en '{self.rl_csv}'")
