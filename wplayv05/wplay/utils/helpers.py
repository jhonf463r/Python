# Archivo: wplay/utils/helpers.py
import time
import pyautogui
import unicodedata
import re
import os
import pandas as pd
import numpy as np
from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from wplay.strategy.constants import MONTO_MAX

from wplay.data.data_cleaner import DataCleaner
from wplay.data.feature_engineer_deep import FeatureEngineerDeep
from wplay.data.model_trainer import ModelTrainer
from wplay.data.transformer_trainer import TransformerTrainer
from wplay.data.db_reader import DBReader
from wplay.training.rl_trainer import RLTrainer


def obtener_datos_actualizados() -> StrategyManagerDL:
    # Rutas relativas al root del proyecto
    ROOT_DIR    = os.path.dirname(os.path.dirname(__file__))
    RAW_DB      = os.path.join(ROOT_DIR, "database", "ruleta_stats.db")
    CLEAN_CSV   = os.path.join(ROOT_DIR, "wplay", "data", "clean_records.csv")
    FEAT_CSV    = os.path.join(ROOT_DIR, "wplay", "data", "lstm_input.csv")
    RL_CSV      = os.path.join(ROOT_DIR, "wplay", "data", "rl_input.csv")
    LSTM_MODEL  = os.path.join(ROOT_DIR, "wplay", "models", "lstm.h5")
    TRANS_MODEL = os.path.join(ROOT_DIR, "wplay", "models", "transformer.h5")
    DQN_MODEL   = os.path.join(ROOT_DIR, "wplay", "models", "dqn.h5")
    PPO_MODEL   = os.path.join(ROOT_DIR, "wplay", "models", "ppo.h5")

    # Crear carpetas si no existen
    for path in (CLEAN_CSV, FEAT_CSV, RL_CSV, LSTM_MODEL, TRANS_MODEL, DQN_MODEL, PPO_MODEL):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # 1) Limpieza
    print("🔄 DataCleaner: limpiando registros…")
    DataCleaner(RAW_DB, CLEAN_CSV).clean()

    # 2) Features
    print("🔄 FeatureEngineerDeep: generando características…")
    fe = FeatureEngineerDeep(
        clean_csv = CLEAN_CSV,
        lstm_csv  = FEAT_CSV,
        rl_csv    = RL_CSV,
        window    = 50,
        window_rl = 10
    )
    fe.transform()

    # 3) Entrenar LSTM
    print("🔄 ModelTrainer: entrenando LSTM…")
    if os.path.exists(LSTM_MODEL):
        os.remove(LSTM_MODEL)
    lstm_trainer = ModelTrainer(
        feat_csv      = FEAT_CSV,
        model_type    = 'lstm',
        window        = 10,
        test_size     = 0.2,
        learning_rate = 1e-3,
        epochs        = 20,
        dropout_rate  = 0.2
    )
    lstm_trainer.train_model(output_model_path=LSTM_MODEL)

    # 4) Entrenar Transformer
    print("🔄 TransformerTrainer: entrenando Transformer…")
    try:
        transformer_trainer = TransformerTrainer(
            feat_csv   = FEAT_CSV,
            model_path = TRANS_MODEL,
            epochs     = 10,
            batch_size = 64
        )
        transformer_trainer.train()
    except Exception as e:
        print("[WARN] Entrenamiento Transformer falló:", e)

    # 5) Pre-entrenamiento offline DQN/PPO (reemplaza df_rl['numero'])
    print("🔄 Preentrenando agentes DQN/PPO offline…")
    # Leer solo para contar filas y columnas
    df_rl = pd.read_csv(RL_CSV)
    if len(df_rl) >= 100:
        # Dimensions
        cols       = df_rl.columns
        state_cols = [c for c in cols if c not in ("action","reward","done") and not c.startswith("next_")]
        state_dim  = len(state_cols)
        action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX

        # Instanciar agentes
        dqn = DQNAgent(state_dim=state_dim, action_dim=action_dim, model_path=DQN_MODEL)
        ppo = PPOAgent(state_dim=state_dim, action_dim=action_dim, model_path=PPO_MODEL)

        # Entrenar offline con RLTrainer
        rl_trainer = RLTrainer(
            rl_csv_path    = RL_CSV,
            strategy_manager=None,
            dqn_agent      = dqn,
            ppo_agent      = ppo,
            buffer_size    = 10000,
            batch_size     = 64,
            train_interval = 50,
            gamma          = 0.99,
            save_dir       = os.path.join(ROOT_DIR, "wplay", "models")
        )
        rl_trainer.pretrain_offline(epochs=5)
        print("✔️ Preentrenamiento RL offline completado.")
    else:
        print("⚠ No hay suficientes muestras RL. Cargando modelos existentes (si los hay)...")
        # Cargar DQN existente
        dqn = DQNAgent(
            state_dim  = 1,
            action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX,
            model_path = DQN_MODEL
        )
        try:
            dqn.load()
        except:
            pass
        # Cargar PPO existente
        ppo = PPOAgent(
            state_dim  = 1,
            action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX,
            model_path = PPO_MODEL
        )
        try:
            ppo.load()
        except:
            pass

    # 6) Construir y devolver el manager
    manager = StrategyManagerDL(
        lstm_path     = LSTM_MODEL,
        rl_agent_dqn  = dqn,
        rl_agent_ppo  = ppo,
        window_lstm   = 50,
        window_rl     = 10
    )
    return manager

def human_click(x: int, y: int, hold_time: float = 0.05, move_duration: float = 0.1, simulate: bool = False) -> None:
    """
    Trae la ventana de Chrome al frente (si la encuentra) y hace click “humano” en (x,y).
    Si simulate=True, sólo imprime la acción.
    """
    try:
        win = pyautogui.getWindowsWithTitle("Chrome")[0]
        if not win.isActive:
            win.activate()
            time.sleep(0.1)
    except Exception:
        pass

    if simulate:
        print(f"[SIMULATE] Click en ({x},{y})")
    else:
        pyautogui.moveTo(x, y, duration=move_duration)
        pyautogui.mouseDown()
        time.sleep(hold_time)
        pyautogui.mouseUp()

def center(region: tuple[int, int, int, int]) -> tuple[int, int]:
    """
    Dado (x, y, w, h), devuelve el punto medio (cx, cy).
    """
    x, y, w, h = region
    return x + w // 2, y + h // 2

def normalize_filename(name: str) -> str:
    """
    Convierte un string arbitrario a un nombre de fichero “seguro”:
    - Elimina tildes y caracteres no ASCII.
    - Sustituye todo lo que no sea [A-Za-z0-9] por '_'.
    - Minusculiza y recorta guiones sobrantes.
    """
    nf = unicodedata.normalize("NFKD", name)
    ascii_only = nf.encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only)
    return safe.strip("_").lower()