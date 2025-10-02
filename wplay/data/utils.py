# wplay/data/utils.py

import json
import h5py
from tensorflow.keras.models import model_from_json

def safe_load_model(h5_path: str):
    """
    Carga un modelo HDF5 eliminando 'batch_shape' de la config JSON
    y manejando correctamente si la config ya viene como str.
    """
    # 1) Leer el atributo model_config
    with h5py.File(h5_path, 'r') as f:
        raw = f.attrs.get('model_config')
        # Si es bytes, decodificamos; si ya es str, lo usamos directamente
        if isinstance(raw, bytes):
            config_str = raw.decode('utf-8')
        elif isinstance(raw, str):
            config_str = raw
        else:
            raise ValueError(f"Tipo inesperado para model_config: {type(raw)}")
        config = json.loads(config_str)

    # 2) Eliminar batch_shape de todas las capas
    for layer in config.get('config', {}).get('layers', []):
        layer_cfg = layer.get('config', {})
        if 'batch_shape' in layer_cfg:
            layer_cfg.pop('batch_shape', None)

    # 3) Reconstruir el modelo y cargar pesos
    model = model_from_json(json.dumps(config))
    model.load_weights(h5_path)
    return model
