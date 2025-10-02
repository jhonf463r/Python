import math
from datetime import datetime
from typing import Tuple

def get_time_sin_cos(ts: float) -> Tuple[float, float, float, float]:
    """
    Devuelve las componentes senoidal y cosenoidal para:
    - la hora del día (en formato decimal)
    - el día de la semana

    Args:
    - ts: timestamp UNIX

    Returns:
    - hour_sin, hour_cos, dow_sin, dow_cos
    """
    now = datetime.fromtimestamp(ts)
    hour = now.hour + now.minute / 60.0
    dow = now.weekday()

    hour_sin = math.sin(2 * math.pi * hour / 24)
    hour_cos = math.cos(2 * math.pi * hour / 24)

    dow_sin = math.sin(2 * math.pi * dow / 7)
    dow_cos = math.cos(2 * math.pi * dow / 7)

    return hour_sin, hour_cos, dow_sin, dow_cos
