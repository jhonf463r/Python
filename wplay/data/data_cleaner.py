import os
import sqlite3
import pandas as pd

class DataCleaner:
    """
    Limpia registros de ruleta desde una fuente (CSV o SQLite) y escribe un CSV limpio.
    Si la fuente acaba en '.db', extrae la tabla 'ruleta_data'.
    Además, calcula ausencias de cada categoría como features adicionales.
    """
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(self,
                 raw_src: str      = "database/ruleta_stats.db",
                 clean_csv: str    = "data/clean_records.csv",
                 min_interval: float = 0.1):
        self.raw_src      = raw_src
        self.clean_csv    = clean_csv
        self.min_interval = min_interval

    def _load_data(self) -> pd.DataFrame:
        # Si es base SQLite, leemos la tabla 'ruleta_data' ordenada por fecha_hora
        if self.raw_src.lower().endswith(".db"):
            conn = sqlite3.connect(self.raw_src)
            try:
                df = pd.read_sql("SELECT * FROM ruleta_data ORDER BY fecha_hora", conn)
            finally:
                conn.close()
            return df
        # Si no, asumimos CSV
        return pd.read_csv(self.raw_src)

    def clean(self):
        df = self._load_data()

        # 1) descartamos velocity == 0 o nulo
        if "velocity" in df.columns:
            df = df[df.velocity > 0]

        # 2) descartamos duplicados exactos
        df = df.drop_duplicates()

        # 3) descartamos intervalos absurdos entre registros
        if "delta_time" in df.columns:
            df = df[df.delta_time >= self.min_interval]

        # 4) calcular categoría para cada registro
        def num_to_cat(numero):
            if numero == 0:
                return "0"
            rojo = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
            return "rojo" if numero in rojo else "negro"

        df['categoria'] = df['numero'].apply(num_to_cat)

        # 5) calcular ausencias de cada categoría
        last_seen = {c: -1 for c in self.CATEGORIES}
        aus_data = {f'aus_{c}': [] for c in self.CATEGORIES}
        for idx, cat in enumerate(df['categoria']):
            for c in self.CATEGORIES:
                last = last_seen[c]
                aus = idx - last if last >= 0 else idx
                aus_data[f'aus_{c}'].append(aus)
            last_seen[cat] = idx

        # añadir columnas de ausencias
        for col, vals in aus_data.items():
            df[col] = vals

        # 6) guardamos CSV limpio con nuevas features
        os.makedirs(os.path.dirname(self.clean_csv) or ".", exist_ok=True)
        df.to_csv(self.clean_csv, index=False)
        print(f"✔️ DataCleaner: {len(df)} registros tras limpieza (CSV en '{self.clean_csv}')")
