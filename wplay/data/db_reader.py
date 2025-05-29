# Archivo: wplay/data/db_reader.py

import os
import sqlite3
import pandas as pd

class DBReader:
    """
    Carga el histórico de rondas desde SQLite y calcula ausencias de cada categoría.

    Ubicación sugerida: 'wplay/data/db_reader.py'
    """
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(self, db_path: str = None):
        # Si no se pasa db_path, usa la misma carpeta 'database' junto al paquete
        if db_path:
            self.db_path = db_path
        else:
            base = os.path.dirname(__file__)
            # asumimos que la base de datos está en ../database/ruleta_stats.db
            self.db_path = os.path.join(base, os.pardir, "database", "ruleta_stats.db")

    def load_rounds(self) -> pd.DataFrame:
        """
        Lee la tabla 'ruleta_data' ordenada por fecha_hora y devuelve un DataFrame.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql("SELECT * FROM ruleta_data ORDER BY fecha_hora", conn)
        finally:
            conn.close()
        return df

    def compute_absences(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade columnas de ausencias para cada categoría en el DataFrame de rondas.
        Cada columna 'aus_<c>' indica cuántas rondas han pasado desde la última aparición de la categoría c.
        """
        # Inicializar últimas apariciones
        last_seen = {c: -1 for c in self.CATEGORIES}
        aus_data = {f'aus_{c}': [] for c in self.CATEGORIES}

        # Asegurarse de que existe columna 'categoria'
        if 'categoria' not in df.columns:
            # Derivar categoría mínimo (rojo/negro)
            def num_to_cat(numero):
                if numero == 0:
                    return '0'
                rojo = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
                return 'rojo' if numero in rojo else 'negro'
            df['categoria'] = df['numero'].apply(num_to_cat)

        for idx, cat in enumerate(df['categoria']):
            for c in self.CATEGORIES:
                last = last_seen[c]
                aus = idx - last if last >= 0 else idx
                aus_data[f'aus_{c}'].append(aus)
            last_seen[cat] = idx

        # Insertar columnas de ausencias
        for col, vals in aus_data.items():
            df[col] = vals
        return df
