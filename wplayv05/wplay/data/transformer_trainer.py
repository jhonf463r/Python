import os
import pandas as pd
from wplay.detectors.data_collector import DataCollector
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager

from tensorflow.keras import Model, Input
from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization, Dense, Dropout, GlobalAveragePooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.utils import to_categorical

class TransformerTrainer:
    """
    Entrena un modelo Transformer para series temporales basado en un CSV de features.
    Ubicación sugerida: 'wplay/data/transformer_trainer.py'
    """
    def __init__(self,
                feat_csv: str,
                model_path: str,
                epochs: int = 20,
                batch_size: int = 64,
                validation_split: float = 0.2,
                num_heads: int = 4,
                key_dim: int = None,
                ff_dim: int = 64,
                dropout: float = 0.1):
        self.feat_csv = feat_csv
        self.model_path = model_path
        self.epochs = epochs
        self.batch_size = batch_size
        self.validation_split = validation_split
        self.num_heads = num_heads
        self.key_dim = key_dim
        self.ff_dim = ff_dim
        self.dropout = dropout
        self.model = None

    def train(self):
        """
        Entrena el modelo Transformer y lo guarda en self.model_path.
        """
        # 1) Carga de datos
        df = pd.read_csv(self.feat_csv)
        if 'target_cat' in df.columns:
            y = pd.Categorical(df['target_cat']).codes
        else:
            y = df['target'].astype(int)
        y = to_categorical(y)

        X = df.drop(columns=[c for c in ['target', 'target_cat'] if c in df.columns]).values
        X = X.reshape(-1, 1, X.shape[1])

        # 2) Construcción del modelo
        timesteps, features = 1, X.shape[2]
        seq_input = Input(shape=(timesteps, features))
        attn_out = MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.key_dim or features
        )(seq_input, seq_input)
        x = LayerNormalization(epsilon=1e-6)(seq_input + attn_out)
        ff = Dense(self.ff_dim, activation='relu')(x)
        ff = Dense(features)(ff)
        x = LayerNormalization(epsilon=1e-6)(x + ff)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(self.dropout)(x)
        output = Dense(y.shape[1], activation='softmax')(x)
        model = Model(inputs=seq_input, outputs=output)

        # 3) Compilación
        model.compile(
            optimizer=Adam(),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        # 4) Callbacks
        os.makedirs(os.path.dirname(self.model_path) or '.', exist_ok=True)
        checkpoint = ModelCheckpoint(
            filepath=self.model_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        )
        early_stop = EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True,
            verbose=1
        )

        # 5) Entrenamiento
        model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=self.validation_split,
            callbacks=[checkpoint, early_stop]
        )

        print(f"✔️ TransformerTrainer: modelo guardado en '{self.model_path}'")
        self.model = model

    def save(self, path: str = None):
        """
        Guarda el modelo entrenado en la ruta especificada.
        """
        path = path or self.model_path
        if self.model is None:
            raise RuntimeError("Entrena el modelo antes de guardar con train()")
        self.model.save(path)
        print(f"✔️ TransformerTrainer: modelo exportado en '{path}'")
