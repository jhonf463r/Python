# wplay/predict/model_predictor.py

import os
import joblib
import numpy as np
from typing import Optional, Union
from tensorflow.keras.models import load_model
from sklearn.base import BaseEstimator

class ModelPredictor:
    """
    Carga el scaler y el modelo entrenado para ofrecer inferencia:
      - Para modelos secuenciales (LSTM/Transformer) de Keras.
      - (Opcional) Para un baseline sklearn serializado.

    Uso típico:
        mp = ModelPredictor(
            scaler_path="artifacts/scaler.pkl",
            model_path="artifacts/model.h5",
            model_type="lstm",
            window=50,
            baseline_path="artifacts/rf.pkl"  # opcional
        )
        probs = mp.predict(raw_features_array)
        action = mp.predict_action(raw_features_array)
    """

    def __init__(
        self,
        scaler_path: str,
        model_path: str,
        model_type: str = 'lstm',
        window: int = 10,
        baseline_path: Optional[str] = None
    ):
        """
        :param scaler_path:   Ruta al MinMaxScaler serializado con joblib.
        :param model_path:    Ruta al modelo Keras (.h5 o carpeta SavedModel).
        :param model_type:    'lstm', 'transformer' o 'flat' (no secuencial).
        :param window:        Longitud de secuencia para LSTM/Transformer.
        :param baseline_path: (Opcional) Ruta a modelo sklearn (RandomForest o LGBM).
        """
        # Cargar el scaler de features
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler no encontrado en '{scaler_path}'")
        self.scaler = joblib.load(scaler_path)

        # Cargar el modelo de Keras
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo Keras no encontrado en '{model_path}'")
        self.model = load_model(model_path)

        self.model_type   = model_type.lower()
        self.window       = window

        # Cargar baseline sklearn si se proporcionó
        self.baseline: Optional[BaseEstimator] = None
        if baseline_path:
            if not os.path.exists(baseline_path):
                raise FileNotFoundError(f"Baseline no encontrado en '{baseline_path}'")
            self.baseline = joblib.load(baseline_path)

    def _reshape_for_sequence(self, X: np.ndarray) -> np.ndarray:
        """
        Toma un vector 1D o matriz 2D escalada y, si es secuencial,
        lo convierte a forma (1, window, features_per_step).
        """
        # asegurar 2D: (n_samples, n_features)
        X2 = X.reshape(1, -1)
        if self.model_type in ('lstm', 'transformer'):
            total_feats = X2.shape[1]
            if total_feats % self.window != 0:
                raise ValueError(
                    f"Features ({total_feats}) no divisible por window ({self.window})"
                )
            feat_dim = total_feats // self.window
            return X2.reshape(1, self.window, feat_dim)
        # para modelo 'flat', devolvemos (1, n_features)
        return X2

    def preprocess(self, raw_feats: Union[np.ndarray, list]) -> np.ndarray:
        """
        Escala y da formato a raw_feats usando el scaler cargado.
        :param raw_feats: Array 1D con features sin escalar.
        :return: Array listo para pasar a self.model.predict().
        """
        arr = np.asarray(raw_feats, dtype=float)
        if arr.ndim != 1:
            raise ValueError("raw_feats debe ser un vector 1D")
        # escalar
        scaled = self.scaler.transform(arr.reshape(1, -1))
        # dar forma para secuenciales o flat
        return self._reshape_for_sequence(scaled)

    def predict(self, raw_feats: Union[np.ndarray, list]) -> np.ndarray:
        """
        Devuelve la probabilidad (softmax) predicha por el modelo Keras.
        :param raw_feats: Vector 1D de features sin procesar.
        :return: Array de probabilidades de forma (1, num_classes).
        """
        x = self.preprocess(raw_feats)
        probs = self.model.predict(x)
        return probs

    def predict_action(self, raw_feats: Union[np.ndarray, list]) -> int:
        """
        Devuelve el índice de la acción/categoría con mayor probabilidad.
        """
        probs = self.predict(raw_feats)
        return int(np.argmax(probs, axis=-1)[0])

    def predict_baseline(self, raw_feats: Union[np.ndarray, list]) -> Optional[int]:
        """
        (Opcional) Utiliza el modelo sklearn cargado para predecir.
        :return: Clase predicha o None si no se cargó baseline.
        """
        if self.baseline is None:
            return None
        arr = np.asarray(raw_feats, dtype=float).reshape(1, -1)
        arr_scaled = self.scaler.transform(arr)
        return int(self.baseline.predict(arr_scaled)[0])
