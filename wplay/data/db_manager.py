# wplay/data/db_manager.py

import sqlite3
import os
import time
from typing import Dict, Tuple

class DBManager:
    """
    Gestiona la persistencia de datos de ruleta en SQLite.
    Tabla: ruleta_data
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Asegura el directorio
        folder = os.path.dirname(db_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self) -> None:
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ruleta_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT,
                numero INTEGER,
                jugadores_presentes INTEGER,
                velocity REAL,
                direction TEXT,
                strategy TEXT,
                fichas INTEGER,
                ganancia REAL,
                saldo REAL,
                opcion_apuesta TEXT
            )
        """)
        self.conn.commit()

    def guardar_registro(self, data: dict) -> None:
        """
        Inserta un registro completo de giro + apuesta.
        Campos esperados en `data`:
          fecha_hora, numero, jugadores_presentes,
          velocity, direction, strategy,
          fichas, ganancia, saldo, opcion_apuesta
        """
        self.cursor.execute("""
            INSERT INTO ruleta_data (
                fecha_hora, numero, jugadores_presentes,
                velocity, direction, strategy,
                fichas, ganancia, saldo,
                opcion_apuesta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("fecha_hora", time.strftime("%Y-%m-%d %H:%M:%S")),
            data.get("numero"),
            int(data.get("jugadores_presentes", 0)),
            data.get("velocity", 0.0),
            data.get("direction", ""),
            data.get("strategy", ""),
            data.get("fichas", 0),
            data.get("ganancia", 0.0),
            data.get("saldo", 0.0),
            data.get("opcion_apuesta", "")
        ))
        self.conn.commit()

    def get_strategy_stats(self) -> Dict[str, Tuple[float, int]]:
        """
        Devuelve para cada strategy:
          (ganancia_total, count_de_veces)
        """
        self.cursor.execute("""
            SELECT strategy, 
                   SUM(ganancia) AS total_gain, 
                   COUNT(*)        AS cnt
            FROM ruleta_data
            WHERE strategy <> ''
            GROUP BY strategy
        """)
        return {
            row[0]: (row[1] or 0.0, row[2])
            for row in self.cursor.fetchall()
        }

    def get_avg_gain_per_strategy(self) -> Dict[str, float]:
        """
        Promedio de ganancia por apuesta para cada estrategia.
        """
        stats = self.get_strategy_stats()
        return {
            strat: (total / cnt if cnt > 0 else 0.0)
            for strat, (total, cnt) in stats.items()
        }

    def get_absence_counts(self) -> Dict[str, int]:
        """
        Cuenta cuántas rondas han pasado desde la última aparición
        de cada categoría de apuesta.
        Retorna un dict {opcion_apuesta: ausencias_consecutivas}.
        """
        categorias = ["rojo", "negro", "par", "impar", "1-18", "19-36"]
        absences = {c: 0 for c in categorias}

        self.cursor.execute("""
            SELECT opcion_apuesta 
            FROM ruleta_data
            WHERE opcion_apuesta <> ''
            ORDER BY fecha_hora DESC
        """)
        rows = [r[0] for r in self.cursor.fetchall()]

        seen = set()
        for opt in rows:
            for c in categorias:
                # si ya vimos esta categoría, no la contamos más
                if c in seen:
                    continue
                if opt == c:
                    seen.add(c)
                    absences[c] = 0
                else:
                    absences[c] += 1
            # detener si todas las categorías ya fueron vistas
            if len(seen) == len(categorias):
                break

        return absences

    def cerrar(self) -> None:
        """Cierra la conexión a la base de datos."""
        self.conn.close()
