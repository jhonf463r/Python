import os
import sqlite3
import pandas as pd
from typing import Optional


class DBReader:
    """
    Carga el histórico de rondas desde SQLite y calcula ausencias de cada categoría.
    """

    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            base = os.path.dirname(__file__)
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

    def load_all(self) -> pd.DataFrame:
        """
        Alias de `load_rounds` para compatibilidad con BettingEngine.
        """
        return self.load_rounds()

    def compute_absences(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade columnas de ausencias para cada categoría en el DataFrame de rondas.
        Cada columna 'aus_<c>' indica cuántas rondas han pasado desde la última aparición de la categoría c.
        """
        # Inicializar últimas apariciones
        last_seen = {c: -1 for c in self.CATEGORIES}
        aus_data = {f'aus_{c}': [] for c in self.CATEGORIES}

        # Asegurar que exista la columna 'numero'
        if 'numero' not in df.columns:
            raise ValueError("El DataFrame debe tener una columna 'numero' para calcular ausencias.")

        # Función auxiliar para clasificar un número en categorías
        def categorias_por_numero(numero: int):
            rojo_set = {1, 3, 5, 7, 9, 12, 14, 16, 18,
                        19, 21, 23, 25, 27, 30, 32, 34, 36}
            return {
                "rojo":   (numero in rojo_set),
                "negro":  (numero != 0 and numero not in rojo_set),
                "par":    (numero != 0 and numero % 2 == 0),
                "impar":  (numero % 2 == 1),
                "1-18":   (1 <= numero <= 18),
                "19-36":  (19 <= numero <= 36),
            }

        for idx, numero in enumerate(df['numero']):
            belongs = categorias_por_numero(int(numero))
            for c in self.CATEGORIES:
                if belongs[c]:
                    last_seen[c] = idx
                    aus_data[f'aus_{c}'].append(0)
                else:
                    last = last_seen[c]
                    aus_data[f'aus_{c}'].append(idx - last if last >= 0 else idx)

        for col, vals in aus_data.items():
            df[col] = vals

        return df
