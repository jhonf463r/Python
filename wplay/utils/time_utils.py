# wplay/utils/time_utils.py

import time
from datetime import datetime, timedelta

def now_timestamp() -> float:
    """
    Devuelve el timestamp actual en segundos (float).
    """
    return time.time()

def now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Devuelve la fecha y hora actuales como string formateado.
    Por defecto: "YYYY-MM-DD HH:MM:SS".
    """
    return datetime.now().strftime(fmt)

def parse_timestamp(ts_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> float:
    """
    Parsea un string de fecha/hora y devuelve el timestamp en segundos.
    """
    dt = datetime.strptime(ts_str, fmt)
    return dt.timestamp()

def format_timestamp(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formatea un timestamp (segundos) como string de fecha/hora.
    """
    return datetime.fromtimestamp(ts).strftime(fmt)

def sleep_until(target_ts: float):
    """
    Duérmete hasta el timestamp objetivo (en segundos).
    Si ya ha pasado, no espera nada.
    """
    now = time.time()
    wait = target_ts - now
    if wait > 0:
        time.sleep(wait)

class Cooldown:
    """
    Decorador / helper para aplicar un cooldown a funciones.
    Ejemplo:
        cd = Cooldown(10.0)   # 10 segundos de cooldown
        @cd.wrap
        def fetch_data():
            ...
    """

    def __init__(self, interval: float):
        self.interval = interval
        self._last_call = 0.0

    def ready(self) -> bool:
        """
        Indica si ha pasado el intervalo de cooldown desde la última llamada.
        """
        return (time.time() - self._last_call) >= self.interval

    def record(self):
        """
        Registra el momento de la llamada (reinicia el cooldown).
        """
        self._last_call = time.time()

    def wrap(self, fn):
        """
        Decorador que aplica cooldown antes de ejecutar la función.
        Si no se devuelve ready(), no llama y retorna None.
        """
        def wrapped(*args, **kwargs):
            if self.ready():
                self.record()
                return fn(*args, **kwargs)
            # no está listo, se salta la llamada
            return None
        return wrapped
