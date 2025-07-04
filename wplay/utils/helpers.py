# File: wplay/utils/helpers.py

import os
import pandas as pd
from typing import Optional
from wplay.wplay_config.hyperparams import HyperParams
from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent
from wplay.strategy.constants import MONTO_MAX
from wplay.models.hypernetwork import build_hypernetwork

def obtener_datos_actualizados(
    *,
    hp: HyperParams,
    dqn_agent_cls: type = DQNAgent,
    ppo_agent_cls: type = PPOAgent,
    dqn_kwargs: Optional[dict] = None,
    ppo_kwargs: Optional[dict] = None,
) -> StrategyManagerDL:
    """
    Ejecuta todo el pipeline offline (limpieza, features, LSTM, Transformer,
    preentrenamiento RL) usando el objeto `hp` para configurar cada componente,
    y devuelve un StrategyManagerDL listo para online, CARGANDO
    automáticamente los pesos finales de PBT si existen.
    """
    from wplay.data.data_cleaner import DataCleaner
    from wplay.data.feature_engineer_deep import FeatureEngineerDeep
    from wplay.data.model_trainer import ModelTrainer
    from wplay.data.transformer_trainer import TransformerTrainer
    from wplay.training.rl_trainer import RLTrainer

    # Rutas base
    ROOT_DIR         = os.path.dirname(os.path.dirname(__file__))
    RAW_DB           = os.path.join(ROOT_DIR, "database", "ruleta_stats.db")
    CLEAN_CSV        = os.path.join(ROOT_DIR, "wplay", "data", "clean_records.csv")
    FEAT_CSV         = os.path.join(ROOT_DIR, "wplay", "data", "lstm_input.csv")
    RL_CSV           = os.path.join(ROOT_DIR, "wplay", "data", "rl_input.csv")
    LSTM_MODEL       = os.path.join(ROOT_DIR, "wplay", "models", "lstm.h5")
    TRANS_MODEL      = os.path.join(ROOT_DIR, "wplay", "models", "transformer.keras")
    DQN_MODEL        = os.path.join(ROOT_DIR, "wplay", "models", "dqn.h5")
    PPO_MODEL        = os.path.join(ROOT_DIR, "wplay", "models", "ppo.h5")

    # **Nuevos paths** de los modelos generados por run_pbt.py
    BEST_DQN_MODEL         = os.path.join(ROOT_DIR, "wplay", "models", "dqn.h5")
    BEST_PPO_MODEL         = os.path.join(ROOT_DIR, "wplay", "models", "ppo.h5")
    BEST_META_SELECTOR_DIR = os.path.join(ROOT_DIR, "wplay", "models", "meta_selector")


    # Asegurar directorios
    for p in (CLEAN_CSV, FEAT_CSV, RL_CSV, LSTM_MODEL, TRANS_MODEL, DQN_MODEL, PPO_MODEL):
        os.makedirs(os.path.dirname(p), exist_ok=True)
    os.makedirs(os.path.dirname(BEST_DQN_MODEL),          exist_ok=True)
    os.makedirs(BEST_META_SELECTOR_DIR,                   exist_ok=True)

    # 1) Limpieza de datos
    print("🔄 DataCleaner: limpiando registros…")
    DataCleaner(RAW_DB, CLEAN_CSV).clean()

    # 2) Feature engineering
    print("🔄 FeatureEngineerDeep: generando características…")
    fe = FeatureEngineerDeep(
        clean_csv   = CLEAN_CSV,
        lstm_csv    = FEAT_CSV,
        rl_csv      = RL_CSV,
        window      = 50,   # fijo
        window_rl   = 10    # fijo
    )
    fe.transform()

    # 3) Entrenar LSTM
    print("🔄 ModelTrainer: entrenando LSTM…")
    if os.path.exists(LSTM_MODEL):
        os.remove(LSTM_MODEL)
    ModelTrainer(
        feat_csv      = FEAT_CSV,
        model_type    = 'lstm',
        window        = 50,
        test_size     = 0.2,
        learning_rate = hp.dqn_lr,
        epochs        = 20,
        dropout_rate  = 0.2
    ).train_model(output_model_path=LSTM_MODEL)

    # 4) Entrenar Transformer
    print("🔄 TransformerTrainer: entrenando Transformer…")
    try:
        if os.path.exists(TRANS_MODEL):
            os.remove(TRANS_MODEL)
        TransformerTrainer(
            feat_csv   = FEAT_CSV,
            model_path = TRANS_MODEL,
            epochs     = 10,
            batch_size = hp.meta_batch_size
        ).train()
    except Exception as e:
        print("[WARN] Entrenamiento Transformer falló:", e)

    # 5) Pre-entrenamiento RL offline
    print("🔄 Preentrenando agentes DQN/PPO offline…")
    df_rl = pd.read_csv(RL_CSV)
    rl_trainer = None

    if len(df_rl) >= 100:
        rl_trainer = RLTrainer(
            clean_csv_path   = CLEAN_CSV,
            rl_csv_path      = RL_CSV,
            strategy_manager = None,
            dqn_agent_cls    = dqn_agent_cls,
            ppo_agent_cls    = ppo_agent_cls,
            dqn_kwargs       = dqn_kwargs or {},
            ppo_kwargs       = ppo_kwargs or {},
            buffer_size      = hp.rl_buffer_size,
            batch_size       = hp.rl_batch_size,
            train_interval   = hp.rl_train_interval,
            gamma            = hp.rl_gamma,
            save_dir         = os.path.join(ROOT_DIR, "wplay", "models"),
            hp               = hp
        )
        rl_trainer.pretrain_offline(epochs=5)
        dqn = rl_trainer.dqn_agent
        ppo = rl_trainer.ppo_agent
        print("✔️ Preentrenamiento RL offline completado.")
    else:
        print("⚠ No hay suficientes muestras RL. Cargando modelos existentes…")
        # Construcción mínima basada en shape
        action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX
        dqn = dqn_agent_cls(
            state_dim  = 1,
            action_dim = action_dim,
            **(dqn_kwargs or {"model_path": DQN_MODEL})
        )
        ppo = ppo_agent_cls(
            state_dim  = 1,
            action_dim = action_dim,
            **(ppo_kwargs or {"model_path": PPO_MODEL})
        )

    # ——— A partir de aquí: CARGA DE PESOS «best» si existen ———
    # 6) Cargar DQN
    if os.path.exists(BEST_DQN_MODEL):
        try:
            print(f"🔄 Cargando DQN entrenado: {BEST_DQN_MODEL}")
            dqn.load_model(BEST_DQN_MODEL)
        except Exception as e:
            print(f"[WARN] No pude cargar DQN best: {e}")

    # 7) Cargar PPO
    if os.path.exists(BEST_PPO_MODEL):
        try:
            print(f"🔄 Cargando PPO entrenado: {BEST_PPO_MODEL}")
            ppo.load_model(BEST_PPO_MODEL)
        except Exception as e:
            print(f"[WARN] No pude cargar PPO best: {e}")

    # 8) Construir StrategyManagerDL (internamente crea MetaStrategySelector)
    hypernet = build_hypernetwork(hp)
    strategy_manager = StrategyManagerDL(
        lstm_path        = LSTM_MODEL,
        rl_agent_dqn     = dqn,
        rl_agent_ppo     = ppo,
        rl_trainer       = rl_trainer,
        hypernet         = hypernet,
        hp               = hp,
        window_lstm      = 50,
        window_rl        = 10
    )

    # 9) Cargar pesos del MetaStrategySelector final
    if os.path.exists(BEST_META_SELECTOR_DIR):
        try:
            print(f"🔄 Cargando MetaSelector entrenado: {BEST_META_SELECTOR_DIR}")
            strategy_manager.selector.load(BEST_META_SELECTOR_DIR)
        except Exception as e:
            print(f"[WARN] No pude cargar MetaSelector best: {e}")

    return strategy_manager
