import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder

class FeaturePipeline:
    """
    Pipeline unificado de preprocesamiento para RL:
     - Escalado de variables numéricas con StandardScaler.
     - One-hot encoding de variables categóricas con OneHotEncoder.
    Tras el fit offline, transform() asegura salida de dimensión fija.
    """

    def __init__(self, numeric_feats, categ_feats):
        """
        :param numeric_feats: lista de nombres de columnas numéricas.
        :param categ_feats:   lista de nombres de columnas categóricas.
        """
        self.numeric_feats = list(numeric_feats)
        self.categ_feats   = list(categ_feats)
        self.scaler        = StandardScaler()
        # Usamos sparse_output para versiones recientes de sklearn
        self.encoder       = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        self._fitted       = False
        # Atributos para features filtradas y mapeos de índices
        self.final_feats = []
        self.all_feats = []
        self.final_idx = []

    def fit_offline(self, df: pd.DataFrame):
        """
        Ajusta scaler y encoder sobre tu histórico (DataFrame completo).
        Debe llamarse antes de cualquier transform().
        """
        # Verificar que existan las columnas
        missing = set(self.numeric_feats + self.categ_feats) - set(df.columns)
        if missing:
            raise KeyError(f"Columnas faltantes en DataFrame offline: {missing}")

        # Fit
        self.scaler.fit(df[self.numeric_feats])
        self.encoder.fit(df[self.categ_feats])
        self._fitted = True

        # Guardar listado de features finales (numéricas filtradas)
        # (asumimos self.numeric_feats filtradas tras steps de varianza/correlación)
        self.final_feats = list(self.numeric_feats)

        # Todos los features originales, excluyendo la columna 'reward'
        self.all_feats = [c for c in df.columns if c != 'reward']

        # Índices de las features finales dentro del vector completo de estado
        self.final_idx = [self.all_feats.index(f) for f in self.final_feats]

    def get_final_indices(self) -> list[int]:
        """
        Devuelve la lista de índices de las features filtradas dentro del vector de estado completo.
        """
        if not self.final_idx:
            raise RuntimeError("fit_offline debe llamarse antes de get_final_indices")
        return self.final_idx

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transforma un DataFrame (offline u online) al vector de estado:
         [scaled numeric columns..., one-hot categorical columns...]
        :return: array de shape (n_samples, state_dim)
        """
        if not self._fitted:
            raise RuntimeError("FeaturePipeline debe fit_offline() antes de transform()")

        num = self.scaler.transform(df[self.numeric_feats])
        cat = self.encoder.transform(df[self.categ_feats])

        return np.hstack([num, cat])
