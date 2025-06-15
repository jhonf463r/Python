# wplay/data/db_manager.py

import sqlite3
import os
import time
import threading
import queue
from typing import Dict, Tuple

class DBManager:
    """
    Gestiona la persistencia de datos de ruleta en SQLite.
    Escritura asíncrona a través de un hilo dedicado para no bloquear el hilo principal.
    Tabla: ruleta_data
    """

    def __init__(self, db_path: str, write_queue_size: int = 1000):
        self.db_path = db_path
        # Asegura el directorio
        folder = os.path.dirname(db_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        # Conexión principal (solo para lectura/creación de tabla)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()

        # Cola y thread de escritura
        self._queue = queue.Queue(maxsize=write_queue_size)
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._writer_loop, daemon=True)
        self._worker.start()

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
        Encola un registro completo de giro + apuesta para inserción asíncrona.
        Campos en `data`:
          fecha_hora, numero, jugadores_presentes,
          velocity, direction, strategy,
          fichas, ganancia, saldo, opcion_apuesta
        """
        try:
            rec = {
                "fecha_hora": data.get("fecha_hora", time.strftime("%Y-%m-%d %H:%M:%S")),
                "numero": data.get("numero"),
                "jugadores_presentes": int(data.get("jugadores_presentes", 0)),
                "velocity": data.get("velocity", 0.0),
                "direction": data.get("direction", ""),
                "strategy": data.get("strategy", ""),
                "fichas": data.get("fichas", 0),
                "ganancia": data.get("ganancia", 0.0),
                "saldo": data.get("saldo", 0.0),
                "opcion_apuesta": data.get("opcion_apuesta", "")
            }
            self._queue.put_nowait(rec)
        except queue.Full:
            print("[DB][WARN] cola de escritura llena; registro descartado")

    def _writer_loop(self):
        """Hilo en background que consume la cola y hace los INSERTs en SQLite."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cur = conn.cursor()
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                rec = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                cur.execute("""
                    INSERT INTO ruleta_data (
                        fecha_hora, numero, jugadores_presentes,
                        velocity, direction, strategy,
                        fichas, ganancia, saldo,
                        opcion_apuesta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec["fecha_hora"],
                    rec["numero"],
                    rec["jugadores_presentes"],
                    rec["velocity"],
                    rec["direction"],
                    rec["strategy"],
                    rec["fichas"],
                    rec["ganancia"],
                    rec["saldo"],
                    rec["opcion_apuesta"]
                ))
                conn.commit()
            except Exception as e:
                print(f"[DB][ERROR] al escribir registro: {e!r}")
            finally:
                self._queue.task_done()

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
                if c in seen:
                    continue
                if opt == c:
                    seen.add(c)
                    absences[c] = 0
                else:
                    absences[c] += 1
            if len(seen) == len(categorias):
                break

        return absences

    def cerrar(self) -> None:
        """
        Cierra la conexión, detiene el hilo de escritura y drena la cola.
        """
        # Señal de parada al worker
        self._stop_event.set()
        self._worker.join(timeout=2.0)
        self.conn.close()
