# wplay/utils/chaos.py

import numpy as np
from collections import Counter

def compute_hurst(ts: np.ndarray) -> float:
    """
    Estima el exponente de Hurst H de una serie temporal ts
    usando la relación escalar de la desviación típica de diferencias.
    H ≈ slope de log(std) vs log(lags).
    """
    ts = np.asarray(ts, dtype=float)
    n = len(ts)
    if n < 20:
        return 0.5  # valor por defecto en series muy cortas

    # lags de 2 hasta n//2
    max_lag = min(n // 2, 100)
    lags = np.arange(2, max_lag)
    tau = [np.std(ts[lag:] - ts[:-lag]) for lag in lags]
    # ajuste lineal en escala log-log
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    H = poly[0]
    return float(H)


def compute_lyapunov(ts: np.ndarray) -> float:
    """
    Aproximación muy simple del exponente de Lyapunov a partir
    de la divergencia de distancias sucesivas.
    λ ≈ mean( ln |x_{t+1} - x_t| )
    """
    ts = np.asarray(ts, dtype=float)
    diffs = np.abs(np.diff(ts))
    # evitar log(0)
    diffs = diffs[diffs > 0]
    if len(diffs) == 0:
        return 0.0
    lambdas = np.log(diffs)
    return float(np.mean(lambdas))


def shannon_entropy(x: np.ndarray) -> float:
    """
    Calcula la entropía de Shannon de la distribución de valores en x.
    H = -sum(p_i * log2(p_i))
    """
    x = np.asarray(x)
    if x.size == 0:
        return 0.0
    counts = Counter(x.flatten())
    probs = np.array(list(counts.values()), dtype=float) / x.size
    # solo p>0
    probs = probs[probs > 0]
    H = -np.sum(probs * np.log2(probs))
    return float(H)
