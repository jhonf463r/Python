# wplay/utils/helpers.py

import os
import pandas as pd
import sqlite3

from wplay.data.data_cleaner       import DataCleaner
from wplay.data.feature_engineer    import FeatureEngineer
from wplay.data.feature_engineer_rl import FeatureEngineerRL
from wplay.data.model_trainer      import ModelTrainer
from wplay.strategy.dqn_agent      import DQNAgent
from wplay.strategy.strategy_manager_dl import StrategyManagerDL


ROOT_DIR   = os.path.dirname(os.path.dirname(__file__))
RAW_DB     = os.path.join(ROOT_DIR, "database", "ruleta_stats.db")
CLEAN_CSV  = os.path.join(ROOT_DIR, "data",     "clean_records.csv")
FEAT_CSV   = os.path.join(ROOT_DIR, "data",     "features.csv")
RL_CSV     = os.path.join(ROOT_DIR, "data",     "transitions_rl.csv")
LSTM_MODEL = os.path.join(ROOT_DIR, "models",   "lstm.h5")
DQN_MODEL  = os.path.join(ROOT_DIR, "models",   "dqn.h5")

def obtener_datos_actualizados() -> StrategyManagerDL:
    # Aseguramos carpetas
    for p in (CLEAN_CSV, FEAT_CSV, RL_CSV, LSTM_MODEL, DQN_MODEL):
        os.makedirs(os.path.dirname(p), exist_ok=True)

    # 1) Limpieza
    print("🔄 DataCleaner: limpiando registros…")
    DataCleaner(RAW_DB, CLEAN_CSV).clean()

    # 2) Features LSTM
    print("🔄 FeatureEngineer: generando características para LSTM…")
    FeatureEngineer(CLEAN_CSV, FEAT_CSV).build()

    # 3) Entrenamiento LSTM
    print("🔄 ModelTrainer: entrenando LSTM…")
    ModelTrainer(FEAT_CSV, LSTM_MODEL).train()

    # 4a) Dataset RL
    print("🔄 FeatureEngineerRL: generando transiciones para DQN…")
    FeatureEngineerRL(CLEAN_CSV, RL_CSV, window=10).build()

    # 4b) Pre-entrenar DQN
    print("🔄 DQNAgent: pre-entrenando red de Q…")
    df_rl = pd.read_csv(RL_CSV)

    if len(df_rl) >= 100:
        # Filtrado correcto: solo columnas que empiezan con "state_"
        states      = df_rl.filter(regex=r"^state_").values
        actions     = df_rl["accion"].astype(int).values
        rewards     = df_rl["recompensa"].astype(float).values
        next_states = df_rl.filter(regex=r"^next_state_").values
        dones       = [False]*(len(states)-1) + [True]

        agent = DQNAgent(
            state_dim  = states.shape[1],
            action_dim = int(actions.max()) + 1,
            model_path = DQN_MODEL
        )
        agent.load()
        agent.train(
            states      = states,
            actions     = actions,
            rewards     = rewards,
            next_states = next_states,
            dones       = dones,
            epochs      = 5,
            batch_size  = 32
        )
        agent.save()
        print(f"✔️ DQNAgent: entrenado y guardado en '{DQN_MODEL}'")
    else:
        agent = DQNAgent(
            state_dim  = 1,
            action_dim = 6,
            model_path = DQN_MODEL
        )
        agent.load()

    print("🔄 StrategyManagerDL: preparando agente híbrido…")
   # en helpers.py
    return StrategyManagerDL(LSTM_MODEL, agent, window_lstm=50, window_rl=10)
