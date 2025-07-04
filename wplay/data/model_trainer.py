# wplay/train/model_trainer.py

import os
import logging
import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.layers import (
    Input, LSTM, Dense, Dropout, LayerNormalization,
    MultiHeadAttention, GlobalAveragePooling1D
)
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
from wplay.config import DATA_DIR

class ModelTrainer:
    """
    Entrenador de:
      - LSTM o Transformer para secuencias
      - Baselines RF y LightGBM con filtrado y selección de features

    Esta versión añade:
      • logging.info() con mediciones (time.perf_counter)
      • Carga de modelo preentrenado si existe, evitando retrain innecesario
    """

    def __init__(
        self, feat_csv, model_type='lstm', window=10, test_size=0.2,
        n_splits=None, learning_rate=1e-3, epochs=50, dropout_rate=0.2,
        model_path=None, rl_csv_path=os.path.join(DATA_DIR, 'rl_input.csv')
    ):
        # Parámetros básicos
        self.feat_csv      = feat_csv
        self.model_type    = model_type.lower()
        self.window        = window
        self.test_size     = test_size
        self.n_splits      = n_splits
        self.learning_rate = learning_rate
        self.epochs        = epochs
        self.dropout_rate  = dropout_rate
        self.model_path    = model_path
        self.rl_csv_path   = rl_csv_path

        # Estado interno
        self.model     = None
        self.state_dim = 0
        self.scaler    = MinMaxScaler()

        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

        # Intentar cargar modelo preentrenado
        if self.model_path and os.path.exists(self.model_path):
            try:
                t0 = time.perf_counter()
                self.model = load_model(self.model_path)
                dt = (time.perf_counter() - t0) * 1000
                logging.info(f"Modelo cargado desde {self.model_path} en {dt:.1f} ms")
            except Exception as e:
                logging.warning(f"No se pudo cargar modelo preentrenado: {e}")

    def train_model(self, output_model_path: str):
        # 1) Carga y orden
        t0 = time.perf_counter()
        df = pd.read_csv(self.feat_csv)
        if 'fecha_hora' in df.columns:
            df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
            df = (
                df.dropna(subset=['fecha_hora'])
                  .sort_values('fecha_hora')
                  .reset_index(drop=True)
            )
        if df.empty:
            raise ValueError(f"CSV vacío: {self.feat_csv}")
        logging.info(f"{len(df)} registros cargados en {time.perf_counter() - t0:.2f}s")

        # 2) Preparar etiquetas
        t0 = time.perf_counter()
        if 'target_cat' in df.columns:
            le    = LabelEncoder()
            y_int = le.fit_transform(df['target_cat'].astype(str))
            y     = to_categorical(y_int)
        elif 'target' in df.columns:
            y_int = df['target'].astype(int)
            y     = to_categorical(y_int)
        else:
            raise ValueError("Falta 'target' o 'target_cat'")
        num_classes = y.shape[1]
        logging.info(f"Etiquetas procesadas en {time.perf_counter() - t0:.2f}s, clases={num_classes}")

        # 3) Seleccionar features y escalar
        t0 = time.perf_counter()
        drop_cols    = ['target','target_cat','fecha_hora']
        feature_cols = [c for c in df.columns if c not in drop_cols]
        X_raw = df[feature_cols].values
        X     = self.scaler.fit_transform(X_raw)
        logging.info(f"{len(feature_cols)} features escalados en {time.perf_counter() - t0:.2f}s")

        # 4) División train/val
        t0 = time.perf_counter()
        if isinstance(self.n_splits, int) and self.n_splits > 1:
            tss = TimeSeriesSplit(n_splits=self.n_splits)
            splits = list(tss.split(X))
            tr_idx, va_idx = splits[-1]
            X_tr, X_va = X[tr_idx], X[va_idx]
            y_tr, y_va = y[tr_idx], y[va_idx]
            logging.info(f"Walk-forward split: train={len(tr_idx)}, val={len(va_idx)}")
        else:
            X_tr, X_va, y_tr, y_va = train_test_split(
                X, y, test_size=self.test_size,
                shuffle=True, random_state=42
            )
            logging.info(f"Random split: test_size={self.test_size}")
        logging.info(f"División completada en {time.perf_counter() - t0:.2f}s")

        # 5) Truncar para secuencias
        def trunc(a): return a[: (len(a)//self.window)*self.window ]
        X_tr, y_tr = trunc(X_tr), trunc(y_tr)
        X_va, y_va = trunc(X_va), trunc(y_va)

        # 6) Baselines y filtrado
        t0 = time.perf_counter()
        df_tr = pd.DataFrame(X_tr, columns=feature_cols)
        df_va = pd.DataFrame(X_va, columns=feature_cols)
        rf    = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(df_tr, np.argmax(y_tr, axis=1))
        logging.info(f"RF initial acc: {rf.score(df_va, np.argmax(y_va, axis=1)):.4f}")

        # Selección top-30
        imps      = rf.feature_importances_
        top30     = np.argsort(imps)[-30:]
        sel_feats = [feature_cols[i] for i in top30]

        # Eliminar bajo var + correladas
        low_var   = [c for c in sel_feats if df_tr[c].nunique() <= 5]
        if low_var:
            logging.info(f"Eliminadas baja var: {low_var}")
            sel_feats = [c for c in sel_feats if c not in low_var]
        corr      = df_tr[sel_feats].corr().abs()
        upper     = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        high_corr = [c for c in sel_feats if any(upper[c] > 0.9)]
        if high_corr:
            logging.info(f"Eliminadas correladas: {high_corr}")
            sel_feats = [c for c in sel_feats if c not in high_corr]
        logging.info(f"Features finales: {sel_feats}")

        # Retrain baselines filtrados
        df_tr_sel = df_tr[sel_feats]
        df_va_sel = df_va[sel_feats]
        rf2       = RandomForestClassifier(n_estimators=100, random_state=42)
        rf2.fit(df_tr_sel, np.argmax(y_tr, axis=1))
        logging.info(f"RF filtered acc: {rf2.score(df_va_sel, np.argmax(y_va, axis=1)):.4f}")

        lgbm = LGBMClassifier(
            n_estimators=200, learning_rate=0.05,
            num_leaves=31, max_depth=6,
            min_split_gain=0.1, min_child_samples=20,
            reg_alpha=0.1, reg_lambda=0.1,
            subsample=0.8, colsample_bytree=0.8,
            verbosity=-1, random_state=42
        )
        lgbm.fit(df_tr_sel, np.argmax(y_tr, axis=1))
        logging.info(f"LGBM filtered acc: {lgbm.score(df_va_sel, np.argmax(y_va, axis=1)):.4f}")
        logging.info(f"Baselines entrenados en {time.perf_counter() - t0:.2f}s")

        # 7) Preparar secuencias para LSTM/Transformer
        t0 = time.perf_counter()
        fps = X_tr.shape[1]
        self.state_dim = fps
        X_seq_tr = X_tr.reshape(-1, self.window, fps)
        X_seq_va = X_va.reshape(-1, self.window, fps)
        y_seq_tr = y_tr.reshape(-1, self.window, num_classes)[:, -1, :]
        y_seq_va = y_va.reshape(-1, self.window, num_classes)[:, -1, :]
        logging.info(f"Secuencias generadas en {time.perf_counter() - t0:.2f}s: {X_seq_tr.shape}")

        # 8) Construir y compilar modelo
        t0 = time.perf_counter()
        if self.model_type == 'lstm':
            model = Sequential([
                Input((self.window, fps)),
                LSTM(32, return_sequences=True),
                Dropout(self.dropout_rate),
                LSTM(16),
                Dropout(self.dropout_rate),
                LayerNormalization(),
                Dense(num_classes, activation='softmax')
            ])
        else:
            inp = Input((self.window, fps))
            att = MultiHeadAttention(num_heads=4, key_dim=fps)(inp, inp)
            x   = Dropout(self.dropout_rate)(att)
            x   = GlobalAveragePooling1D()(x)
            out = Dense(num_classes, activation='softmax')(x)
            model = Model(inp, out)
        model.compile(
            optimizer=Adam(self.learning_rate),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        logging.info(f"Modelo compilado en {time.perf_counter() - t0:.2f}s")

        # 9) Entrenamiento final con callbacks
        t0 = time.perf_counter()
        os.makedirs(os.path.dirname(output_model_path) or '.', exist_ok=True)
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
            ModelCheckpoint(output_model_path, monitor='val_loss', save_best_only=True)
        ]
        history = model.fit(
            X_seq_tr, y_seq_tr,
            validation_data=(X_seq_va, y_seq_va),
            epochs=self.epochs, batch_size=32,
            callbacks=callbacks, verbose=2, shuffle=False
        )
        logging.info(f"Entrenamiento completed en {time.perf_counter() - t0:.2f}s")
        self.model = model

        # 10) Truncar rl_input.csv para sincronía
        try:
            rl_df = pd.read_csv(self.rl_csv_path)
            rl_df = rl_df.iloc[:len(X_tr)]
            rl_df.to_csv(self.rl_csv_path, index=False)
            logging.info(f"rl_input.csv truncado a {len(rl_df)} filas")
        except Exception as e:
            logging.warning(f"No se truncó rl_input.csv: {e}")

        return history
