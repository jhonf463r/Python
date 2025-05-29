import pandas as pd
import os

MAX_JUGADORES = 20  # Ajusta según tu juego

class FeatureEngineerRL:
    """
    Genera un dataset de transiciones para entrenamiento de un agente RL,
    a partir de un CSV limpio con columnas: numero, velocity, direction, jugadores_presentes.

    Salida: CSV con columnas:
      state_pos_0,...,state_pos_{window-1}, state_velocidad, state_dir_bin, state_jugadores,
      accion (0-5), recompensa,
      next_state_pos_0,...,next_state_pos_{window-1}, next_state_velocidad, next_state_dir_bin, next_state_jugadores
    """
    # Definimos las categorías en el mismo orden que StrategyManagerDL.CATEGORIES
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(self, clean_csv: str, output_csv: str, window: int = 10):
        self.clean_csv = clean_csv
        self.output_csv = output_csv
        self.window = window

    def _numero_a_estado_vector(self, row: pd.Series, window_hist: list[int], prefix="state_") -> dict:
        estado = {}
        # posiciones normalizadas de la ruleta (0..36 → 0.0..1.0)
        for i, num in enumerate(window_hist):
            estado[f"{prefix}pos_{i}"] = num / 36.0
        # características de la ronda actual
        estado[f"{prefix}velocidad"] = row["velocity"] / 100.0
        estado[f"{prefix}dir_bin"]   = 1 if row["direction"] == "horario" else 0
        estado[f"{prefix}jugadores"] = row["jugadores_presentes"] / MAX_JUGADORES
        return estado

    def _calcular_recompensa(self, accion_idx: int, real_num: int) -> float:
        # apuesta por número exacto: +35 si acierta, -1 si falla
        # (aunque luego podrías convertir recompensa según payout de categoría)
        return 35.0 if accion_idx == self._numero_a_categoria_idx(real_num) else -1.0

    def _numero_a_categoria_idx(self, n: int) -> int:
        """Convierte un número (0–36) a índice de categoría (0–5)."""
        if n == 0:
            # opcional: descartar o mapear a una categoría especial
            return -1
        # par/impar
        cat = None
        if n % 2 == 0:
            cat = "par"
        else:
            cat = "impar"
        # ranges
        if 1 <= n <= 18:
            range_cat = "1-18"
        else:
            range_cat = "19-36"
        # color
        rojo = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        color_cat = "rojo" if n in rojo else "negro"

        # Aquí decides cuál es tu espacio de acción: 
        # si tu agente solo elige entre color, par/impar y ranges,
        # podrías mapear cada número a uno solo de esos seis.
        # Vamos a mapearlo al **color** (rojo/negro/par/impar/1-18/19-36):
        # usando sólo color como ejemplo:
        # return self.CATEGORIES.index(color_cat)

        # O si prefieres incluir par/impar y ranges en tu espacio de acción,
        # podrías decidir la prioridad. Aquí devolvemos color:
        return self.CATEGORIES.index(color_cat)

    def build(self):
        df = pd.read_csv(self.clean_csv)
        registros = []
        hist_numeros = []

        for idx in range(len(df) - 1):
            actual    = df.iloc[idx]
            siguiente = df.iloc[idx + 1]

            hist_numeros.append(int(actual["numero"]))
            if len(hist_numeros) < self.window:
                continue

            window_hist = hist_numeros[-self.window:]
            next_hist   = hist_numeros[-(self.window - 1):] + [int(siguiente["numero"])]

            state_dict      = self._numero_a_estado_vector(actual, window_hist, prefix="state_")
            next_state_dict = self._numero_a_estado_vector(siguiente, next_hist, prefix="next_state_")

            # obtenemos el índice de categoría 0–5 para la apuesta
            accion_idx = self._numero_a_categoria_idx(int(actual["numero"]))
            recompensa = self._calcular_recompensa(accion_idx, int(siguiente["numero"]))

            registro = {}
            registro.update(state_dict)
            registro["accion"]     = accion_idx
            registro["recompensa"] = recompensa
            registro.update(next_state_dict)

            registros.append(registro)

        os.makedirs(os.path.dirname(self.output_csv), exist_ok=True)
        out_df = pd.DataFrame(registros)

        # Columnas en orden: solo state_ (no next_state_), acción, recompensa, next_state_
        state_cols      = sorted([c for c in out_df.columns if c.startswith("state_") and not c.startswith("next_state_")])
        next_state_cols = sorted([c for c in out_df.columns if c.startswith("next_state_")])
        final_cols = state_cols + ["accion", "recompensa"] + next_state_cols

        out_df = out_df[final_cols]
        out_df.to_csv(self.output_csv, index=False)

        print(f"✅ FeatureEngineerRL: {len(out_df)} muestras guardadas en '{self.output_csv}'")
