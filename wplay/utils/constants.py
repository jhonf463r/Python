# wplay/utils/constants.py
"""
Constantes compartidas para DataCollector y FeatureEngineerDeep
"""

# Normalización de intervalos de tiempo entre giros (segundos)
MIN_DT = 0.5        # mínimo intervalo permitido
MAX_DT = 20.0       # máximo intervalo permitido
# Para normalización offline y LSTM/RL
MAX_INTERVAL = MAX_DT  

# Ventana y puntos mínimos para métricas de caos
CHAOS_WINDOW_SIZE = 20
MIN_CHAOS_POINTS  = 5
# Umbrales mínimos para bloque de aceleración y jugadores
MIN_ACCEL_POINTS  = 2
MIN_PLAYER_POINTS = 1


# wplay/utils/time_features.py
"""
Funciones utilitarias para obtener características de tiempo (hora y día) en forma sen/cos.
"""
import math
from datetime import datetime

def get_time_sin_cos(timestamp: float):
    """
    Dado un timestamp UNIX, devuelve las representaciones senoidales y cosenoidales
    de la hora del día y del día de la semana.

    Args:
        timestamp: tiempo UNIX en segundos.

    Returns:
        Un dict con llaves:
            - hour_sin, hour_cos: sen/cos de la hora normalizada [0,24).
            - dow_sin, dow_cos:  sen/cos del día de la semana (0=Lunes..6=Domingo).
    """
    # Convertir a datetime local
    now = datetime.fromtimestamp(timestamp)

    # Hora del día con fracción
    hour = now.hour + now.minute / 60.0 + now.second / 3600.0
    theta = 2 * math.pi * hour / 24.0
    hour_sin = math.sin(theta)
    hour_cos = math.cos(theta)

    # Día de la semana
    dow = now.weekday()
    phi = 2 * math.pi * dow / 7.0
    dow_sin = math.sin(phi)
    dow_cos = math.cos(phi)

    return {
        'hour_sin': hour_sin,
        'hour_cos': hour_cos,
        'dow_sin': dow_sin,
        'dow_cos': dow_cos
    }
