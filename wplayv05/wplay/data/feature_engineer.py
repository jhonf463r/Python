import os
import pandas as pd
import numpy as np
from datetime import datetime

# Parámetros globales
MAX_JUGADORES = 20
MAX_VELOCITY = 100.0

class FeatureEngineer:
    """
    Ingeniería de características básica para modelos supervisados.
    Genera características tabulares para modelos densos o LSTM simples.
    """
    def __init__(self, clean_csv: str, feat_csv: str, window: int = 50):
        self.clean_csv = clean_csv
        self.feat_csv = feat_csv
        self.window = window

    def build(self):
        df = pd.read_csv(self.clean_csv)
        features = []
        for idx in range(self.window, len(df)):
            row = df.iloc[idx]
            aus_cols = [c for c in df.columns if c.startswith('aus_')]
            absences = {c: row[c] for c in aus_cols}
            try:
                dt = datetime.fromisoformat(row['fecha_hora'])
                hour_norm = dt.hour / 23.0
            except Exception:
                hour_norm = 0.0
            feat = {
                **absences,
                'velocidad': row.get('velocity', 0.0),
                'dir_bin': 1 if row.get('direction', '') == 'horario' else 0,
                'jugadores': min(row.get('jugadores_presentes', 0) / MAX_JUGADORES, 1.0),
                'hora_norm': hour_norm,
                'target': row['numero']
            }
            features.append(feat)

        feature_df = pd.DataFrame(features)
        os.makedirs(os.path.dirname(self.feat_csv) or ".", exist_ok=True)
        feature_df.to_csv(self.feat_csv, index=False)
        print(f"\u2714\ufe0f FeatureEngineer: {len(features)} filas generadas en '{self.feat_csv}'")