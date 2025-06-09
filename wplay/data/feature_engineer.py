import os
import pandas as pd
from datetime import datetime

# Ajuste según número máximo de jugadores observado o estimado
MAX_JUGADORES = 20

class FeatureEngineer:
    """
    Genera un conjunto de características a partir de un CSV limpio que ya contiene columnas de ausencias.
    Cada fila de salida corresponde a una ventana móvil de resultados previos y las variables del registro actual,
    además de incluir características temporales (hora del día) y ausencias precomputadas.
    Ubicación sugerida: 'wplay/data/feature_engineer.py'
    """
    def __init__(self, clean_csv: str, feat_csv: str, window: int = 50):
        self.clean_csv = clean_csv
        self.feat_csv = feat_csv
        self.window = window

    def build(self):
        # Carga datos limpios que incluyen columnas 'aus_<categoria>'
        df = pd.read_csv(self.clean_csv)

        features = []
        # Recorre desde la posición 'window' hasta el final
        for idx in range(self.window, len(df)):
            row = df.iloc[idx]

            # Extraer ausencias precomputadas
            aus_cols = [c for c in df.columns if c.startswith('aus_')]
            absences = {c: row[c] for c in aus_cols}

            # Característica temporal: hora del día normalizada [0,1]
            try:
                dt = datetime.fromisoformat(row['fecha_hora'])
                hour_norm = dt.hour / 23.0
            except Exception:
                hour_norm = 0.0

            # Variables de entrada
            feat = {
                **absences,
                'velocidad': row.get('velocity', 0.0),
                'dir_bin': 1 if row.get('direction','') == 'horario' else 0,
                'jugadores': min(row.get('jugadores_presentes', 0) / MAX_JUGADORES, 1.0),
                'hora_norm': hour_norm,
                # Target: número para el LSTM o categoría según tu modelo
                'target': row['numero']
            }
            features.append(feat)

        # Guardar CSV de características
        feature_df = pd.DataFrame(features)
        os.makedirs(os.path.dirname(self.feat_csv) or ".", exist_ok=True)
        feature_df.to_csv(self.feat_csv, index=False)
        print(f"✔️ FeatureEngineer: {len(features)} filas generadas en '{self.feat_csv}'")
