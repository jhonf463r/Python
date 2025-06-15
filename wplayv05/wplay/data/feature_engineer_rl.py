# Archivo: wplay/data/feature_engineer_rl.py

import os
import pandas as pd
import numpy as np
from wplay.data.constants import MAX_JUGADORES
from wplay.strategy.strategy_manager_dl import StrategyManagerDL  # ejemplo de gestor de estrategia

class FeatureEngineerRL:
    def __init__(self, clean_csv: str, output_csv: str, window: int = 10):
        self.clean_csv = clean_csv
        self.output_csv = output_csv
        self.window = window

    def generate_transitions(self):
        """
        Lee el CSV limpio (con columnas: numero, velocity, direction, jugadores_presentes, aus_*).
        Genera un CSV con transiciones (state, action, reward, next_state).
        """
        # 1. Cargar CSV limpio
        df = pd.read_csv(self.clean_csv)
        # Asegurar que no haya valores nulos en columnas críticas
        df = df.dropna(subset=['numero', 'velocity', 'direction', 'jugadores_presentes'])
        df = df.reset_index(drop=True)

        # 2. Inicializar lista para registros
        registros = []

        # 3. Creamos instancia del manager de estrategia (ejemplo)
        strategy_manager = StrategyManagerDL()

        # 4. Iterar desde 'window' hasta el penúltimo índice para generar (state, action, reward, next_state)
        for i in range(self.window, len(df) - 1):
            # Construir estado: últimos `window` números, velocidad, dirección, jugadores normalizado
            state = {}
            # 4.1. Ventana de números de ruleta en estado
            for w in range(self.window):
                state[f'state_pos_{w}'] = df.loc[i - self.window + w, 'numero'] / 36.0  # normalizamos a [0,1]
            # 4.2. Otras features de estado
            state['state_velocidad'] = df.loc[i, 'velocity'] / df['velocity'].max()  # normalización simple
            state['state_dir_bin'] = 1 if df.loc[i, 'direction'] == 'horario' else 0
            state['state_jugadores'] = df.loc[i, 'jugadores_presentes'] / MAX_JUGADORES

            # 4.3. Obtenemos acción y recompensa usando la estrategia
            action = strategy_manager.select_action_for_state(state.copy())
            reward = strategy_manager.compute_reward(state.copy(), action, df.loc[i + 1, 'numero'])

            # 4.4. Construir next_state: desplazamos un paso la ventana
            next_state = {}
            for w in range(self.window):
                next_state[f'next_state_pos_{w}'] = df.loc[i - self.window + 1 + w, 'numero'] / 36.0
            next_state['next_state_velocidad'] = df.loc[i + 1, 'velocity'] / df['velocity'].max()
            next_state['next_state_dir_bin'] = 1 if df.loc[i + 1, 'direction'] == 'horario' else 0
            next_state['next_state_jugadores'] = df.loc[i + 1, 'jugadores_presentes'] / MAX_JUGADORES

            # 4.5. Indicar si es terminal (quizá nunca se use en ruleta, aquí lo ponemos False)
            done = False

            # 4.6. Componer registro completo
            registro = {
                **state,
                'action': action,
                'reward': reward,
                **next_state,
                'done': done
            }
            registros.append(registro)

        # 5. Crear DataFrame con todas las transiciones y guardarlo
        out_df = pd.DataFrame(registros)
        # Verificar que no haya valores NaN
        out_df = out_df.dropna()
        out_df.to_csv(self.output_csv, index=False)
        print(f"[FeatureEngineerRL] Generadas {len(out_df)} transiciones en {self.output_csv}")
        return out_df
