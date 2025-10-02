import numpy as np


def compute_meta_stats(probabilities, reward_history, window=50):
    """
    Calcula estadísticas meta para alimentar el Hypernetwork o la lógica de selección.

    :param probabilities: Iterable de longitud 3 con probabilidades [p_dqn, p_ppo, p_skip].
    :param reward_history: Secuencia (list o deque) de recompensas recientes.
    :param window: Tamaño de la ventana para la media móvil y desviación estándar.

    :return: numpy.array de 4 floats: [conf_max, reward_mean, variability, uncertainty]
    """
    # 1) Confianza máxima entre los algoritmos
    conf_max = float(np.max(probabilities))

    # 2) Recompensa media en la ventana
    recent = list(reward_history)[-window:] if len(reward_history) > 0 else []
    if recent:
        reward_mean = float(np.mean(recent))
        variability = float(np.std(recent))
    else:
        reward_mean = 0.0
        variability = 0.0

    # 3) Incertidumbre: diferencia absoluta entre DQN y PPO
    p_dqn, p_ppo, p_skip = probabilities
    uncertainty = float(abs(p_dqn - p_ppo))

    return np.array([conf_max, reward_mean, variability, uncertainty], dtype=np.float32)
