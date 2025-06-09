# Archivo: wplay/utils/helpers.py

import os
import numpy as np
import pandas as pd

from wplay.strategy.strategy_manager_dl import StrategyManagerDL
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent

from wplay.data.data_cleaner import DataCleaner
from wplay.data.feature_engineer_deep import FeatureEngineerDeep
from wplay.data.model_trainer import ModelTrainer
from wplay.data.transformer_trainer import TransformerTrainer
from wplay.data.db_reader import DBReader


def obtener_datos_actualizados() -> StrategyManagerDL:
    # Rutas relativas al root del proyecto
    ROOT_DIR   = os.path.dirname(os.path.dirname(__file__))
    RAW_DB     = os.path.join(ROOT_DIR, "database", "ruleta_stats.db")
    CLEAN_CSV  = os.path.join(ROOT_DIR, "wplay", "data", "clean_records.csv")
    FEAT_CSV   = os.path.join(ROOT_DIR, "wplay", "data", "lstm_input.csv")
    RL_CSV     = os.path.join(ROOT_DIR, "wplay", "data", "rl_input.csv")
    LSTM_MODEL = os.path.join(ROOT_DIR, "wplay", "models", "lstm.h5")
    DQN_MODEL  = os.path.join(ROOT_DIR, "wplay", "models", "dqn.h5")
    PPO_MODEL  = os.path.join(ROOT_DIR, "wplay", "models", "ppo.h5")

    for fichero in (CLEAN_CSV, FEAT_CSV, RL_CSV, LSTM_MODEL, DQN_MODEL, PPO_MODEL):
        os.makedirs(os.path.dirname(fichero), exist_ok=True)

    print("🔄 DataCleaner: limpiando registros…")
    DataCleaner(RAW_DB, CLEAN_CSV).clean()

    print("🔄 FeatureEngineerDeep: generando características…")
    fe = FeatureEngineerDeep(
        clean_csv = CLEAN_CSV,
        lstm_csv  = FEAT_CSV,
        rl_csv    = RL_CSV,
        window    = 50,
        window_rl = 10
    )
    fe.transform()

    # ✅ CORRECCIÓN APLICADA AQUÍ
    print("🔄 ModelTrainer: entrenando LSTM…")
    if os.path.exists(LSTM_MODEL):
        os.remove(LSTM_MODEL)

    trainer = ModelTrainer(
        feat_csv      = FEAT_CSV,
        model_type    = 'lstm',
        window        = 10,
        test_size     = 0.2,
        learning_rate = 1e-3,
        epochs        = 20,
        dropout_rate  = 0.2
    )
    trainer.train_model(output_model_path = LSTM_MODEL)

    try:
        print("🔄 TransformerTrainer: entrenando Transformer…")
        TransformerTrainer(
            feat_csv   = FEAT_CSV,
            model_path = os.path.join(ROOT_DIR, "wplay", "models", "transformer.h5"),
            epochs     = 10,
            batch_size = 64
        ).train()
    except Exception as e:
        print("[WARN] Entrenamiento Transformer falló:", e)

    print("🔄 FeatureEngineerDeep (RL): generando transiciones para RL…")
    df_rl = pd.read_csv(RL_CSV)
    if len(df_rl) >= 100:
            from wplay.strategy.constants import MONTO_MAX
            cats = StrategyManagerDL.CATEGORIES

            def map_to_cat(num):
                if num in range(1, 37):
                    half = "1-18" if num <= 18 else "19-36"
                    par  = "par"   if num % 2 == 0 else "impar"
                    rojo_set = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
                    color = "rojo" if num in rojo_set else "negro"
                    for key in (color, par, half):
                        if key in cats:
                            return cats.index(key)
                return 0

            print("🔄 Preentrenando agentes DQN/PPO offline…")
            df_rl["action_cat"] = df_rl["numero"].apply(map_to_cat)
            df_rl["action_idx"] = df_rl["action_cat"] * MONTO_MAX + 0

            state_cols  = [c for c in df_rl.columns if c.startswith("state_")]
            next_cols   = [c for c in df_rl.columns if c.startswith("next_state_")]
            states      = df_rl[state_cols].values.astype(np.float32)
            actions     = df_rl["action_idx"].values.astype(np.int32)
            rewards     = df_rl["recompensa"].values.astype(np.float32)
            next_states = df_rl[next_cols].values.astype(np.float32)
            dones       = np.array([False] * (len(states) - 1) + [True], dtype=np.bool_)

            # ----------------- DQN offline (sin cambios) -----------------
            dqn = DQNAgent(
                state_dim  = states.shape[1],
                action_dim = len(cats) * MONTO_MAX
            )
            try:
                dqn.load(DQN_MODEL)
            except:
                pass

            dqn.train(
                batch_size  = 32,
                states      = states,
                actions     = actions,
                rewards     = rewards,
                next_states = next_states,
                dones       = dones,
                epochs      = 50
            )
            dqn.save(DQN_MODEL)



            # --------------- PPO offline (ajustado) ---------------------
            ppo = PPOAgent(
                state_dim  = states.shape[1],
                action_dim = len(cats) * MONTO_MAX
            )
            # Intentar cargar modelo existente (actor + critic)
            try:
                ppo.load(PPO_MODEL.replace(".h5", "_actor.h5"),
                        PPO_MODEL.replace(".h5", "_critic.h5"))
            except:
                pass

            # Calcular values actuales (para returns y ventajas)
            values = ppo.critic.predict(states, verbose=0).flatten()  # (N,)
            # Calcular returns a partir de rewards y dones
            returns = []
            discounted_sum = 0
            for r, is_done in zip(reversed(rewards), reversed(dones)):
                if is_done:
                    discounted_sum = 0
                discounted_sum = r + ppo.gamma * discounted_sum
                returns.insert(0, discounted_sum)
            returns = np.array(returns, dtype=np.float32)

            # Ventajas
            advantages = returns - values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

            # Para “old_logprobs”, sintetizamos usando la política actual del actor
            probs = ppo.actor.predict(states, verbose=0)  # (N, action_dim)
            old_logp = np.log(np.choose(actions, probs.T) + 1e-8)  # (N,)  

            # Entrenar offline en batch
            ppo.train_offline(
                states       = states,
                actions      = actions,
                returns      = returns,
                advantages   = advantages,
                old_logprobs = old_logp,
                epochs       = 50,
                batch_size   = 32
            )
            ppo.save(
                PPO_MODEL.replace(".h5", "_actor.h5"),
                PPO_MODEL.replace(".h5", "_critic.h5")
            )
            # --------------------------------------------------------------

            manager = StrategyManagerDL(
                lstm_path     = LSTM_MODEL,
                rl_agent_dqn  = dqn,
                rl_agent_ppo  = ppo,
                window_lstm   = 50,
                window_rl     = 10
            )

    else:
        print("⚠ No hay suficientes muestras RL. Cargando modelos existentes (si los hay)...")
        from wplay.strategy.constants import MONTO_MAX
        dqn = DQNAgent(
            state_dim  = 1,
            action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX,
            model_path = DQN_MODEL
        )
        try:
            dqn.load()
        except:
            pass
        ppo = PPOAgent(
            state_dim  = 1,
            action_dim = len(StrategyManagerDL.CATEGORIES) * MONTO_MAX,
            model_path = PPO_MODEL
        )
        try:
            ppo.load()
        except:
            pass

        manager = StrategyManagerDL(
            lstm_path     = LSTM_MODEL,
            rl_agent_dqn  = dqn,
            rl_agent_ppo  = ppo,
            window_lstm   = 50,
            window_rl     = 10
        )

    return manager
