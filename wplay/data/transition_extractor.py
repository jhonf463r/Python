# wplay/data/transition_extractor.py
import sqlite3
import pandas as pd
import numpy as np
from typing import Tuple

class TransitionExtractor:
    """
    Extrae (state, action, reward, next_state, done) 
    desde la base de datos para entrenar agentes RL.
    Asume que en la tabla 'registros' tienes columnas:
      - velocity, dir_bin, jugadores_presentes, category(action), ganancia(reward)
      - además historiales de ausencias s_<cat>, y tras cada fila un next_state similar.
    """
    def __init__(self, db_path: str, window: int = 50):
        self.db_path = db_path
        self.window = window

    def extract(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM registros ORDER BY fecha_hora", conn)
        conn.close()

        # construir states: ausencias + velocidad + dir_bin + jugadores
        # aquí asumimos que ya hay columnas s_rojo, s_negro, ..., dir_bin, velocity, jugadores_presentes
        state_cols = [c for c in df.columns if c.startswith("s_")] + \
                     ["velocity", "dir_bin", "jugadores_presentes"]
        states = df[state_cols].values
        # acciones codificadas como entero
        actions = df["opcion_apuesta"].astype("category").cat.codes.values
        # recompensas
        rewards = df["ganancia"].values
        # next_states: desplazamos estados uno hacia atrás; la última es terminal
        next_states = np.vstack([states[1:], np.zeros_like(states[0])])
        dones = np.zeros(len(df), dtype=bool)
        dones[-1] = True

        return states, actions, rewards, next_states, dones
