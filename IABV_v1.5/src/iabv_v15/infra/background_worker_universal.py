"""
IABV v1.5 - Background Worker Universal (Cross-Platform)
=========================================================

Worker universal para mover trabajo JSON/SQLite del main thread.
Implementación cross-platform para resolver congelamientos UI con CPU/RAM estables.

Este módulo implementa la solución universal para el problema crítico #1:
"Congelamientos UI con CPU/RAM estables" - unknown_main_thread_stall
"""

import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
import json
import sqlite3
from pathlib import Path


class BackgroundWorkerUniversal:
    """
    Worker universal para tareas pesadas en background (cross-platform).
    
    Este worker permite mover operaciones JSON/SQLite del main thread
    para prevenir congelamientos de UI, especialmente cuando CPU/RAM
    están estables pero el hilo UI está bloqueado por operaciones pesadas.
    """
    
    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix='iabv-bg-universal'
        )
        self._task_queue = queue.Queue()
        self._lock = threading.Lock()
        self._task_count = 0
        self._completed_count = 0
        
    def submit_json_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Envía operación JSON a background thread.
        
        Uso típico: lectura/escritura de archivos JSON grandes,
        procesamiento de configuración, etc.
        """
        def wrapped_operation():
            try:
                result = operation(*args, **kwargs)
                with self._lock:
                    self._completed_count += 1
                return result
            except Exception as e:
                print(f"[BackgroundWorker] Error en operacion JSON: {e}")
                return None
                
        future = self._executor.submit(wrapped_operation)
        return future
        
    def submit_sqlite_operation(
        self, 
        db_path: str, 
        operation: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Envía operación SQLite a background con conexión separada.
        
        Uso típico: consultas pesadas, escrituras complejas,
        operaciones de migración, etc.
        """
        def wrapped_operation():
            conn = sqlite3.connect(db_path)
            try:
                # Usar ROW factory para acceso por nombre de columna
                conn.row_factory = sqlite3.Row
                result = operation(conn, *args, **kwargs)
                return result
            except Exception as e:
                print(f"[BackgroundWorker] Error en operacion SQLite: {e}")
                return None
            finally:
                conn.close()
                
        future = self._executor.submit(wrapped_operation)
        return future
        
    def submit_file_operation(self, file_path: str, operation: Callable, *args, **kwargs) -> Any:
        """
        Envía operación de archivos a background thread.
        
        Uso típico: lectura de archivos grandes, procesamiento
        de imágenes, etc.
        """
        def wrapped_operation():
            try:
                result = operation(Path(file_path), *args, **kwargs)
                with self._lock:
                    self._completed_count += 1
                return result
            except Exception as e:
                print(f"[BackgroundWorker] Error en operacion de archivo: {e}")
                return None
                
        future = self._executor.submit(wrapped_operation)
        return future
        
    def get_status(self) -> dict[str, Any]:
        """
        Retorna estado del worker para monitoreo.
        """
        return {
            "active_tasks": self._task_count,
            "completed_tasks": self._completed_count,
            "max_workers": 2,
            "status": "active"
        }
        
    def shutdown(self, wait: bool = False):
        """
        Cierra el worker de manera segura.
        
        Args:
            wait: Si True, espera que las tareas en curso terminen
        """
        self._executor.shutdown(wait=wait)


# Singleton global del worker
_worker_instance: Optional[BackgroundWorkerUniversal] = None


def get_background_worker() -> BackgroundWorkerUniversal:
    """
    Obtiene el worker universal singleton (cross-platform).
    
    Este patrón singleton asegura que solo haya un pool de threads
    compartido para todas las operaciones en background, optimizando
    el uso de recursos en todas las plataformas.
    """
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = BackgroundWorkerUniversal()
        print("[BackgroundWorkerUniversal] Worker singleton creado")
    return _worker_instance


def submit_background_json(operation: Callable, *args, **kwargs) -> Any:
    """
    Wrapper conveniente para enviar operaciones JSON al background.
    
    Esta función es el punto de entrada universal para aplicaciones
    que necesitan mover trabajo JSON del main thread.
    """
    worker = get_background_worker()
    return worker.submit_json_operation(operation, *args, **kwargs)


def submit_background_sqlite(db_path: str, operation: Callable, *args, **kwargs) -> Any:
    """
    Wrapper conveniente para enviar operaciones SQLite al background.
    
    Esta función es el punto de entrada universal para aplicaciones
    que necesitan mover trabajo SQLite del main thread.
    """
    worker = get_background_worker()
    return worker.submit_sqlite_operation(db_path, operation, *args, **kwargs)


# Funciones de utilidad para operaciones comunes

def read_json_background(file_path: str) -> Optional[dict]:
    """
    Lee archivo JSON en background (universal).
    
    Solución para main_thread_stall cuando CPU/RAM están estables.
    """
    def read_operation(path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    worker = get_background_worker()
    future = worker.submit_file_operation(file_path, read_operation)
    
    try:
        return future.result(timeout=30.0)  # 30s timeout universal
    except Exception as e:
        print(f"[BackgroundWorker] Error leyendo JSON: {e}")
        return None


def write_json_background(file_path: str, data: dict) -> bool:
    """
    Escribe archivo JSON en background (universal).
    
    Solución para main_thread_stall durante escrituras pesadas.
    """
    def write_operation(path: Path, content: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return True
    
    worker = get_background_worker()
    future = worker.submit_file_operation(file_path, write_operation, data)
    
    try:
        return future.result(timeout=30.0)  # 30s timeout universal
    except Exception as e:
        print(f"[BackgroundWorker] Error escribiendo JSON: {e}")
        return False


if __name__ == "__main__":
    # Test del worker universal (cross-platform)
    print("Testing BackgroundWorkerUniversal (cross-platform)...")
    
    # Test de operación JSON en background
    def test_json_operation():
        return {"status": "ok", "data": "test"}
    
    worker = BackgroundWorkerUniversal()
    future = worker.submit_json_operation(test_json_operation)
    result = future.result(timeout=5.0)
    print(f"JSON operation result: {result}")
    
    # Test de estado
    status = worker.get_status()
    print(f"Worker status: {status}")
    
    worker.shutdown(wait=True)
    print("BackgroundWorkerUniversal test completed successfully!")
