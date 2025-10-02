# wplay/features_online.py

import numpy as np
from datetime import datetime, timedelta
from wplay.utils.time_features import get_time_sin_cos, get_time_sin_cos_dow
from wplay.data.feature_engineer_deep import MAX_JUGADORES, MAX_VELOCITY

class OnlineFeatureEngineer:
    """
    Genera *en vivo* el mismo set de columnas que RL transitions offline.
    """

    def __init__(self, window_rl:int, done_threshold:float, strat_vals:list):
        self.window_rl      = window_rl
        self.done_threshold = done_threshold
        self.strat_vals     = strat_vals

    def build(self,
              registro: dict,
              saldo_hist:   list[float],
              win_hist:     list[bool],
              num_hist:     list[int],
              time_hist:    list[datetime]):
        """
        :param registro:   los campos básicos sacados en BettingEngine (incluye 'fecha_hora', 'numero', 'velocity', 'direction', 'jugadores_presentes', 'strategy_prev')
        :param saldo_hist: lista de saldos previos (len ≥ window_rl)
        :param win_hist:   lista booleana si cada spin fue win (len ≥ window_rl)
        :param num_hist:   lista de últimos números (len ≥ window_rl)
        :param time_hist:  lista de timestamps (len ≥ window_rl) 
        :returns dict con todas las keys pos_0…done
        """
        N = self.window_rl
        # 1) State
        window_nums = num_hist[-N:]
        state = {
            **{f"pos_{i}": n/36.0 for i,n in enumerate(window_nums)},
            "count_red":   sum(n in wplay.data.feature_engineer_deep.FeatureEngineerDeep.CATEGORIES and n%2 for n in window_nums)/N,  # o tu lista de rojos
            "count_black": 1.0,
            "count_par":   sum((n%2==0 and n!=0) for n in window_nums)/N,
            "count_imp":   1.0,
            "velocidad":   registro['velocity']/MAX_VELOCITY,
            "dir_bin":     int(registro['direction']=="horario"),
            "jugadores":   registro['jugadores_presentes']/MAX_JUGADORES,
        }
        state["count_black"] = 1 - state["count_red"]
        state["count_imp"]   = 1 - state["count_par"]

        # 2) Time & calendar
        now   = registro['fecha_hora']
        prev  = time_hist[-1] if time_hist else now
        delta = (now - prev).total_seconds()
        iv    = min(delta, self.done_threshold)/self.done_threshold
        hs, hc = get_time_sin_cos(now)
        ds, dc = get_time_sin_cos_dow(now)
        state.update({
            "time_between": iv,
            "hour_sin":     hs,
            "hour_cos":     hc,
            "dow_sin":      ds,
            "dow_cos":      dc,
        })

        # 3) Drawdown & time_since_win
        sl = saldo_hist[-N:]
        pk = max(sl+[1e-6]); cs = saldo_hist[-1]
        state["drawdown"] = min(max((pk-cs)/pk,0),1)
        # última vez que win_hist==True
        tw = 300.0
        for i in range(N-1, -1, -1):
            if win_hist[i]:
                tw = min((now - time_hist[i]).total_seconds(),300.0)
                break
        state["time_since_win"] = tw/300.0

        # 4) strat one-hot
        sp = registro['strategy_prev']
        for s in self.strat_vals:
            state[f"strat_{s}"] = int(sp==s)

        # 5) next_state y done
        # (asumiendo que en línea no necesitas next_…, o igual lo calculas con buffer “siguiente”)

        # 6) “action”, “reward” y “done” los añade BettingEngine antes de pasar a add_record()
        return state
