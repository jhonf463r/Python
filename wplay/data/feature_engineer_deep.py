# Archivo: wplay/data/feature_engineer_deep.py

import pandas as pd
import os

class FeatureEngineerDeep:
    """
    Combina el CSV limpio con el cálculo de ausencias para generar:
    - Un CSV para entrenamiento LSTM/Transformer (data/lstm_input.csv)
    - Un CSV para entrenamiento RL (data/rl_input.csv)
    """
    def __init__(self,
                 clean_csv: str,
                 lstm_csv: str,
                 rl_csv: str,
                 window_lstm: int = 50,
                 window_rl: int = 10):
        self.clean_csv = clean_csv
        self.lstm_csv = lstm_csv
        self.rl_csv = rl_csv
        self.window_lstm = window_lstm
        self.window_rl = window_rl
        self.categories = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def transform(self):
        # 1) Carga CSV limpio
        df = pd.read_csv(self.clean_csv)

        # 2) Asegurar columnas aus_<cat>
        for cat in self.categories:
            col = f"aus_{cat}"
            if col not in df.columns:
                # calcular ausencias a partir del historial de números
                aus = []
                hist = []
                for num in df["numero"]:
                    # convertir número a categoría
                    if num == 0:
                        c = "0"
                    elif num in {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}:
                        c = "rojo"
                    else:
                        c = "negro"
                    hist.append(c)
                    # calcular cuántos giros desde última aparición de cat
                    if cat in hist[:-1]:
                        last = len(hist)-2 - hist[:-1][::-1].index(cat)
                        aus.append((len(hist)-1) - last)
                    else:
                        aus.append(self.window_lstm)
                df[col] = aus

        # 3) Generar LSTM CSV
        lstm_rows = []
        for idx in range(self.window_lstm, len(df)):
            window = df.iloc[idx-self.window_lstm:idx]
            row = df.iloc[idx]
            features = {}
            # ausencias directas
            for cat in self.categories:
                features[f"aus_{cat}"] = int(row[f"aus_{cat}"])
            # otras features
            features["velocity"] = float(row.get("velocity", 0.0))
            features["direction_bin"] = 1 if row.get("direction","")=="horario" else 0
            features["jugadores"] = int(row.get("jugadores_presentes", 0))
            # target
            features["target_cat"] = row["categoria_predicha"] if "categoria_predicha" in row else row["categoria"]
            lstm_rows.append(features)

        df_lstm = pd.DataFrame(lstm_rows)
        os.makedirs(os.path.dirname(self.lstm_csv) or ".", exist_ok=True)
        df_lstm.to_csv(self.lstm_csv, index=False)
        print(f"✔️ FeatureEngineerDeep: {len(df_lstm)} filas guardadas en '{self.lstm_csv}'")

        # 4) Generar RL CSV
        rl_rows = []
        for idx in range(self.window_rl, len(df)-1):
            state_window = df["numero"].iloc[idx-self.window_rl:idx].tolist()
            next_num = int(df["numero"].iloc[idx+1])
            state = {f"state_pos_{i}": state_window[i]/36.0 for i in range(self.window_rl)}
            state["state_vel"] = df["velocity"].iloc[idx]/100.0
            state["state_dir"] = 1 if df["direction"].iloc[idx]=="horario" else 0
            state["state_jug"] = df["jugadores_presentes"].iloc[idx]/50.0

            action = int(df["numero"].iloc[idx])
            reward = 35.0 if action==next_num else -1.0

            next_window = df["numero"].iloc[idx-self.window_rl+1:idx+1].tolist()
            next_state = {f"next_state_pos_{i}": next_window[i]/36.0 for i in range(self.window_rl)}
            next_state["next_vel"] = df["velocity"].iloc[idx+1]/100.0
            next_state["next_dir"] = 1 if df["direction"].iloc[idx+1]=="horario" else 0
            next_state["next_jug"] = df["jugadores_presentes"].iloc[idx+1]/50.0

            row = {}
            row.update(state)
            row["accion"] = action
            row["recompensa"] = reward
            row.update(next_state)
            rl_rows.append(row)

        df_rl = pd.DataFrame(rl_rows)
        os.makedirs(os.path.dirname(self.rl_csv) or ".", exist_ok=True)
        df_rl.to_csv(self.rl_csv, index=False)
        print(f"✔️ FeatureEngineerDeep: {len(df_rl)} filas guardadas en '{self.rl_csv}'")
