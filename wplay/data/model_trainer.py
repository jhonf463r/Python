import os
import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, LayerNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder

class ModelTrainer:
    def __init__(
        self,
        feat_csv: str,
        model_type: str = 'lstm',
        window: int = 10,
        test_size: float = 0.2,
        learning_rate: float = 1e-3,
        epochs: int = 50,
        dropout_rate: float = 0.2,
        model_path: str = None
    ):
        """
        :param feat_csv: Ruta al CSV con características y target.
        :param model_type: 'lstm' o 'transformer'.
        :param window: Longitud de la secuencia para LSTM/Transformer.
        :param test_size: Fracción de datos para validación.
        :param learning_rate: Learning rate inicial.
        :param epochs: Número máximo de épocas de entrenamiento.
        :param dropout_rate: Tasa de dropout en las capas recurrentes.
        :param model_path: (Opcional) Ruta para cargar pesos preexistentes.
        """
        self.feat_csv = feat_csv
        self.model_type = model_type
        self.window = window
        self.test_size = test_size
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.dropout_rate = dropout_rate
        self.model = None
        self.model_path = model_path

        # Si se provee model_path y existe, cargamos pesos antes de entrenar
        if self.model_path and os.path.exists(self.model_path):
            # Construimos modelo dummy para poder cargar pesos
            # (Las dimensiones reales se establecerán en train_model)
            self.model = Sequential()
            # No conocemos aún input_shape aquí; se cargará en train_model si corresponde.
            try:
                self.model.load_weights(self.model_path)
                print(f"[ModelTrainer] Pesos cargados desde {self.model_path}")
            except Exception:
                # Ignoramos errores de carga anticipada; será creado en train_model
                pass

    def train_model(self, output_model_path: str):
        # 1. Cargar CSV de features
        df = pd.read_csv(self.feat_csv)
        if df.empty:
            raise ValueError(f"[ModelTrainer] El archivo CSV está vacío: {self.feat_csv}")

        # 2. Separar X e y
        if 'target_cat' in df.columns:
            # Convertir categorías string a enteros
            le = LabelEncoder()
            y_int = le.fit_transform(df['target_cat'].astype(str))
            y = to_categorical(y_int, num_classes=len(le.classes_))
        else:
            # Mantener lógica anterior si target es numérico
            y = df['target'].values
            y = to_categorical(y, num_classes=int(df['target'].max()) + 1)

        # 3. Construir matriz X con todas las columnas excepto target
        X = df.drop(columns=['target', 'target_cat'], errors='ignore').values

        # 4. Calcular cantidad de características por paso
        total_features = X.shape[1]
        features_x_step = total_features // self.window

        # Validación crítica:
        if features_x_step == 0:
            raise ValueError(
                f"[ModelTrainer] El número total de características ({total_features}) "
                f"es insuficiente para una ventana de {self.window} pasos. "
                "Reduce el parámetro 'window' o aumenta las columnas de entrada."
            )

        # 5. Dividir en entrenamiento y validación
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=self.test_size, shuffle=True, random_state=42
        )

        # 6. Reshape para LSTM/Transformer
        X_train = X_train.reshape(-1, self.window, features_x_step)
        X_val = X_val.reshape(-1, self.window, features_x_step)

        # 7. Construir modelo según tipo
        if self.model_type.lower() == 'lstm':
            self.model = Sequential()
            self.model.add(
                LSTM(
                    units=64,
                    return_sequences=True,
                    input_shape=(self.window, features_x_step)
                )
            )
            self.model.add(Dropout(self.dropout_rate))
            self.model.add(LSTM(units=32))
            self.model.add(Dropout(self.dropout_rate))
            self.model.add(LayerNormalization())
            self.model.add(Dense(y.shape[1], activation='softmax'))

        elif self.model_type.lower() == 'transformer':
            from tensorflow.keras.layers import Input, MultiHeadAttention, GlobalAveragePooling1D
            from tensorflow.keras.models import Model

            inputs = Input(shape=(self.window, features_x_step))
            attn_output = MultiHeadAttention(num_heads=4, key_dim=features_x_step)(
                inputs, inputs
            )
            attn_output = Dropout(self.dropout_rate)(attn_output)
            out = Dense(64, activation='relu')(attn_output)
            out = GlobalAveragePooling1D()(out)
            out = Dense(32, activation='relu')(out)
            outputs = Dense(y.shape[1], activation='softmax')(out)
            self.model = Model(inputs=inputs, outputs=outputs)

        else:
            raise ValueError(f"[ModelTrainer] Tipo de modelo desconocido: {self.model_type}")

        # 8. Compilar modelo
        self.model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        # 9. Callbacks: EarlyStopping y ModelCheckpoint
        os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
        es = EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        mc = ModelCheckpoint(
            output_model_path,
            monitor='val_loss',
            save_best_only=True
        )

        # 10. Entrenar
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.epochs,
            batch_size=32,
            callbacks=[es, mc],
            verbose=2,
            shuffle=True
        )

        print(f"[ModelTrainer] Entrenamiento completado. Modelo guardado en {output_model_path}")
        return history
