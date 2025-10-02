import os
import time
import logging

import pandas as pd
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, MultiHeadAttention, LayerNormalization, Dense, Dropout, GlobalAveragePooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.utils import to_categorical


class TransformerTrainer:
    """
    Entrena un modelo Transformer para series temporales
    basado en un CSV de features, con logs y timing.
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
        self.feat_csv         = feat_csv
        self.model_path       = model_path
        self.epochs           = epochs
        self.batch_size       = batch_size
        self.validation_split = validation_split
        self.num_heads        = num_heads
        self.key_dim          = key_dim
        self.ff_dim           = ff_dim
        self.dropout          = dropout
        self.model            = None

        logging.basicConfig(level=logging.INFO,
                            format='[%(levelname)s] %(message)s')

        # ✅ Cargar .keras si existe para evitar error de batch_shape
        keras_path = self.model_path.replace('.h5', '.keras')
        if os.path.exists(keras_path):
            try:
                t0 = time.perf_counter()
                self.model = load_model(keras_path)
                dt = (time.perf_counter() - t0) * 1000
                self.model_path = keras_path  # ← actualizar path
                logging.info(f"Loaded pretrained Transformer in {dt:.1f} ms from '{keras_path}'")
            except Exception as e:
                logging.warning(f"Could not load pretrained model: {e}")

    def train(self):
        # 1) Cargar datos
        t0 = time.perf_counter()
        df = pd.read_csv(self.feat_csv)
        if 'target_cat' in df.columns:
            y_codes = pd.Categorical(df['target_cat']).codes
        else:
            y_codes = df['target'].astype(int).values
        y = to_categorical(y_codes)
        X = df.drop(columns=[c for c in ('target','target_cat') if c in df.columns]).values
        X = X.reshape(-1, 1, X.shape[1])  # (batch, timesteps, features)
        logging.info(f"Loaded data X={X.shape}, y={y.shape} in {time.perf_counter()-t0:.2f}s")

        if self.model is not None:
            logging.info("Skipping training, using loaded model.")
            return self.model

        # 2) Construir modelo
        t0 = time.perf_counter()
        timesteps, features = X.shape[1], X.shape[2]
        inp = Input(shape=(timesteps, features))
        attn = MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.key_dim or features
        )(inp, inp)
        x = LayerNormalization(epsilon=1e-6)(inp + attn)
        ff = Dense(self.ff_dim, activation='relu')(x)
        ff = Dense(features)(ff)
        x = LayerNormalization(epsilon=1e-6)(x + ff)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(self.dropout)(x)
        out = Dense(y.shape[1], activation='softmax')(x)
        model = Model(inputs=inp, outputs=out)
        logging.info(f"Built Transformer model in {time.perf_counter()-t0:.2f}s")

        # 3) Compilar
        t0 = time.perf_counter()
        model.compile(
            optimizer=Adam(),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        logging.info(f"Compiled model in {time.perf_counter()-t0:.2f}s")

        # 4) Guardar modelo en formato nativo (.keras)
        os.makedirs(os.path.dirname(self.model_path) or '.', exist_ok=True)
        chkpt_path = self.model_path.replace('.h5', '.keras')
        checkpoint = ModelCheckpoint(
            filepath=chkpt_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1,
            save_format='keras'  # ← evita el error de batch_shape
        )
        early_stop = EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True,
            verbose=1
        )

        # 5) Entrenar
        t0 = time.perf_counter()
        history = model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=self.validation_split,
            callbacks=[checkpoint, early_stop],
            verbose=2,
            shuffle=False
        )
        dt = time.perf_counter() - t0
        logging.info(f"Completed training in {dt:.2f}s; best val_loss={min(history.history['val_loss']):.4f}")

        # 6) Guardar estado
        self.model = model
        self.model_path = chkpt_path  # ← actualizado para futuras cargas
        logging.info(f"Transformer saved to '{self.model_path}'")
        return model

    def save(self, path: str = None):
        """
        Guarda el modelo entrenado en la ruta especificada.
        """
        if self.model is None:
            raise RuntimeError("Call train() before save().")
        target = path or self.model_path
        t0 = time.perf_counter()
        self.model.save(target)
        logging.info(f"Model exported to '{target}' in {(time.perf_counter()-t0)*1000:.1f} ms")
