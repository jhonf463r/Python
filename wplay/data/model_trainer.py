# Archivo: wplay/data/model_trainer.py

import os
import pandas as pd
from tensorflow.keras import Sequential, Input
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.utils import to_categorical

class ModelTrainer:
    """
    Entrena un modelo de secuencia (LSTM o Transformer) a partir de un CSV de features.
    - Soporta entrenamiento con EarlyStopping y puntos de control.
    - Guarda el mejor modelo según validación.
    """

    def __init__(self,
                 feat_csv: str,
                 model_path: str,
                 epochs: int = 20,
                 batch_size: int = 64,
                 validation_split: float = 0.2,
                 use_transformer: bool = False,
                 transformer_config: dict = None):
        self.feat_csv = feat_csv
        self.model_path = model_path
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.validation_split = validation_split
        self.use_transformer = use_transformer
        self.transformer_config = transformer_config or {}

    def train(self):
        # 1) Carga de datos
        df = pd.read_csv(self.feat_csv)

        # 2) Preparación de X e y
        if 'target_cat' in df.columns:
            y = pd.Categorical(df['target_cat']).codes
        elif 'target' in df.columns:
            y = df['target'].astype(int)
        else:
            raise ValueError("El CSV no contiene ni 'target_cat' ni 'target' como columna de salida.")

        y = to_categorical(y)
        X = df.drop(columns=[c for c in ['target', 'target_cat'] if c in df.columns]).values
        X = X.reshape(-1, 1, X.shape[1])  # Para LSTM o Transformer: (samples, timesteps, features)

        # 3) Definición del modelo
        if self.use_transformer:
            model = self._build_transformer_model(input_shape=X.shape[1:], output_dim=y.shape[1])
        else:
            model = Sequential([
                Input(shape=(1, X.shape[2])),
                LSTM(64, return_sequences=False),
                Dense(y.shape[1], activation='softmax')
            ])

        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        # 4) Callbacks: EarlyStopping y ModelCheckpoint
        os.makedirs(os.path.dirname(self.model_path) or '.', exist_ok=True)
        checkpoint = ModelCheckpoint(
            self.model_path,
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

        # 6) Evaluación final
        loss, acc = model.evaluate(X, y, verbose=0)
        print(f"📊 Evaluación final - Loss: {loss:.4f}, Accuracy: {acc:.4f}")
        print(f"✔️ ModelTrainer: mejor modelo guardado en '{self.model_path}'")

    def _build_transformer_model(self, input_shape, output_dim):
        """
        Construye un modelo Transformer simple para series temporales.
        Requiere TensorFlow >= 2.9 con soporte para MultiHeadAttention.
        """
        from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization, Dropout, GlobalAveragePooling1D
        from tensorflow.keras import Model

        seq_input = Input(shape=input_shape)
        attn_output = MultiHeadAttention(
            num_heads=self.transformer_config.get('num_heads', 2),
            key_dim=self.transformer_config.get('key_dim', input_shape[-1])
        )(seq_input, seq_input)

        x = LayerNormalization(epsilon=1e-6)(seq_input + attn_output)
        ffn = Dense(self.transformer_config.get('ff_dim', 64), activation='relu')(x)
        ffn_output = Dense(input_shape[-1])(ffn)
        x = LayerNormalization(epsilon=1e-6)(x + ffn_output)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(self.transformer_config.get('dropout', 0.1))(x)
        output = Dense(output_dim, activation='softmax')(x)

        model = Model(inputs=seq_input, outputs=output)
        return model
    def save(self):
        # Ya se guarda con ModelCheckpoint, este método se deja por compatibilidad
        print(f"✔️ ModelTrainer: modelo ya guardado automáticamente en '{self.model_path}'")
