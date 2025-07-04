# Archivo: wplay/models/hypernetwork.py

import tensorflow as tf
from tensorflow.keras import layers, Model, Input

# Importa tu contenedor de hiperparámetros:
from wplay.wplay_config.hyperparams import HyperParams

def build_hypernetwork(hp: HyperParams) -> Model:
    """
    Construye un Hypernetwork que toma un vector de estadísticas meta
    y genera coeficientes adaptativos para ponderar las estrategias.

    Parámetros esperados en hp:
      - meta_stats_dim: dimensionalidad del vector de estadísticas meta.
      - hyper_hidden_units: lista de enteros con tamaños de capas ocultas.
      - hyper_num_coeffs: número de coeficientes (estrategias) a generar.
      - (opcional) hyper_model_path: ruta donde guardar el modelo, si se desea.

    Salida:
      - tf.keras.Model que mapea stats_meta -> coeficientes normalizados.
    """

    # 1) Definición de la entrada
    inputs = Input(shape=(hp.meta_stats_dim,), name="hyper_input")
    x = inputs

    # 2) Capas ocultas según configuración
    for idx, units in enumerate(hp.hyper_hidden_units):
        x = layers.Dense(
            units,
            activation="relu",
            name=f"hyper_dense_{idx}"
        )(x)

    # 3) Capa de salida: coeficientes crudos
    coeffs_raw = layers.Dense(
        hp.hyper_num_coeffs,
        activation=None,
        name="coeffs_raw"
    )(x)

    # 4) Normalización para que sum(|w_i|)=1 (evita sesgo de magnitud)
    coeffs_norm = layers.Lambda(
        lambda z: z / tf.reduce_sum(tf.abs(z), axis=1, keepdims=True),
        name="coeffs_norm"
    )(coeffs_raw)

    # 5) Construcción del modelo
    model = Model(inputs=inputs, outputs=coeffs_norm, name="Hypernetwork")

    # (Opcional) guarda un modelo base vacío para inspectability
    # if hp.hyper_model_path:
    #     model.save(hp.hyper_model_path, include_optimizer=False)

    return model
