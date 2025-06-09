# wplay/data/feature_engineer_deep.py

import os
import pandas as pd
from datetime import datetime

# Ajuste del número máximo de jugadores observado (para normalización)
MAX_JUGADORES = 20

class FeatureEngineerDeep:
    """
    Genera dos datasets a partir de un CSV limpio (que ya contiene columnas 'aus_<cat>'):
      1) CSV para LSTM (columnas: aus_<cat>, velocity, dir_bin, jugadores, hora_norm, target_cat)
      2) CSV para RL (columnas: state_pos_*, state_aus_<cat>*, state_velocidad, state_dir_bin, state_jugadores,
                         acción, recompensa,
                         next_state_pos_*, next_state_aus_<cat>*, next_state_velocidad, next_state_dir_bin, next_state_jugadores)
    """

    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(
        self,
        clean_csv: str,
        lstm_csv: str,
        rl_csv: str,
        window: int = 50,
        window_rl: int = 10,
    ):
        """
        :param clean_csv: ruta al CSV limpio (output de DataCleaner)
        :param lstm_csv: ruta donde se guardará el CSV para entrenamiento LSTM
        :param rl_csv: ruta donde se guardará el CSV de transiciones para RL
        :param window: tamaño de ventana para LSTM
        :param window_rl: tamaño de ventana para RL
        """
        self.clean_csv = clean_csv
        self.lstm_csv = lstm_csv
        self.rl_csv = rl_csv
        self.window = window
        self.window_rl = window_rl

    def _num_to_cat(self, n: int) -> str:
        """
        Convierte un número (0..36) a categoría (rojo/negro/par/impar/1-18/19-36).
        Asigna la etiqueta “color” con prioridad (rojo o negro).
        """
        if n == 0:
            return "0"
        cat = "par" if n % 2 == 0 else "impar"
        _range = "1-18" if 1 <= n <= 18 else "19-36"
        rojo_set = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        color_cat = "rojo" if n in rojo_set else "negro"
        return color_cat

    def transform(self):
        """
        1) Genera CSV para LSTM (ausencias + variables físicas + target_cat)
        2) Genera CSV de transiciones RL (estado, acción_idx, recompensa, next_estado)
           - Estado incluye tanto “posiciones” como “ausencias” y variables físicas.
        """
        df = pd.read_csv(self.clean_csv)

        # --- PARTE A: CSV para LSTM ---
        rows_lstm = []
        for idx in range(self.window, len(df)):
            row = df.iloc[idx]

            aus_cols = [c for c in df.columns if c.startswith("aus_")]
            absences = {c: row[c] for c in aus_cols}

            try:
                dt = datetime.fromisoformat(row["fecha_hora"])
                hour_norm = dt.hour / 23.0
            except:
                hour_norm = 0.0

            feat_lstm = {
                **absences,
                "velocidad": row.get("velocity", 0.0),
                "dir_bin": 1 if row.get("direction", "") == "horario" else 0,
                "jugadores": min(row.get("jugadores_presentes", 0) / MAX_JUGADORES, 1.0),
                "hora_norm": hour_norm,
                "target_cat": self._num_to_cat(int(row["numero"]))
            }
            rows_lstm.append(feat_lstm)

        df_lstm = pd.DataFrame(rows_lstm)
        os.makedirs(os.path.dirname(self.lstm_csv) or ".", exist_ok=True)
        df_lstm.to_csv(self.lstm_csv, index=False)
        print(f"✔️ FeatureEngineerDeep: {len(df_lstm)} filas guardadas en '{self.lstm_csv}'")

        # --- PARTE B: CSV de transiciones para RL ---
        registros = []
        hist_numeros = []

        for idx in range(len(df) - 1):
            actual = df.iloc[idx]
            siguiente = df.iloc[idx + 1]

            hist_numeros.append(int(actual["numero"]))
            if len(hist_numeros) < self.window_rl:
                continue

            window_hist = hist_numeros[-self.window_rl:]
            next_hist = hist_numeros[-(self.window_rl - 1):] + [int(siguiente["numero"])]

            # Estado actual: posiciones + ausencias + físicas
            state_dict = {}
            for i, num in enumerate(window_hist):
                state_dict[f"state_pos_{i}"] = num / 36.0
            # ausencias en el estado actual
            for cat in FeatureEngineerDeep.CATEGORIES:
                state_dict[f"state_aus_{cat}"] = actual.get(f"aus_{cat}", 0)

            state_dict["state_velocidad"] = actual["velocity"] / 100.0
            state_dict["state_dir_bin"] = 1 if actual["direction"] == "horario" else 0
            state_dict["state_jugadores"] = actual["jugadores_presentes"] / MAX_JUGADORES

            # Próximo estado (same features con “siguiente” en lugar de “actual”)
            next_state_dict = {}
            for i, num in enumerate(next_hist):
                next_state_dict[f"next_state_pos_{i}"] = num / 36.0
            for cat in FeatureEngineerDeep.CATEGORIES:
                next_state_dict[f"next_state_aus_{cat}"] = siguiente.get(f"aus_{cat}", 0)

            next_state_dict["next_state_velocidad"] = siguiente["velocity"] / 100.0
            next_state_dict["next_state_dir_bin"] = 1 if siguiente["direction"] == "horario" else 0
            next_state_dict["next_state_jugadores"] = siguiente["jugadores_presentes"] / MAX_JUGADORES

            # Acción: índice de color (solo color). Recompensa: +1 si coincide, -1 si no
            accion_idx = self._numero_a_categoria_idx(int(actual["numero"]))
            recompensa = self._calcular_recompensa(accion_idx, int(siguiente["numero"]))

            registro = {}
            registro.update(state_dict)
            # Nota: aquí guardamos “numero” real en columna aparte para luego mapear offline a “action_idx”
            registro["numero"] = int(actual["numero"])
            registro["recompensa"] = recompensa
            registro.update(next_state_dict)

            registros.append(registro)

        df_rl = pd.DataFrame(registros)
        os.makedirs(os.path.dirname(self.rl_csv) or ".", exist_ok=True)
        df_rl.to_csv(self.rl_csv, index=False)
        print(f"✅ FeatureEngineerDeep (RL): {len(df_rl)} muestras guardadas en '{self.rl_csv}'")

    def _numero_a_categoria_idx(self, n: int) -> int:
        """
        Convierte un número (0–36) a índice 0..5 de CATEGORIES (color con prioridad).
        “0” → -1, en cuyo caso se descarta.
        """
        if n == 0:
            return -1
        rojo_set = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        color = "rojo" if n in rojo_set else "negro"
        return FeatureEngineerDeep.CATEGORIES.index(color)

    def _calcular_recompensa(self, accion_idx: int, real_num: int) -> float:
        """
        Si la acción (color) coincide con el número real, +1; sino, -1.
        """
        if accion_idx < 0:
            return -1.0
        cat_real = self._numero_a_categoria_idx(real_num)
        return 1.0 if accion_idx == cat_real else -1.0
