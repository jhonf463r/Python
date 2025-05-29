# wplay/training/rl_trainer.py

import sqlite3
import pandas as pd
import numpy as np
from wplay.strategy.dqn_agent import DQNAgent

class RLTrainer:
    def __init__(self, db_path, state_cols, action_col, reward_col, next_state_cols, done_col, model_path):
        self.db_path         = db_path
        self.state_cols      = state_cols
        self.action_col      = action_col
        self.reward_col      = reward_col
        self.next_state_cols = next_state_cols
        self.done_col        = done_col
        self.model_path      = model_path

    def _load_transitions(self):
        conn = sqlite3.connect(self.db_path)
        df   = pd.read_sql("SELECT * FROM registros", conn)
        conn.close()
        if self.done_col not in df.columns:
            df[self.done_col] = False
        df = df.dropna(subset=self.state_cols + [self.action_col, self.reward_col] + self.next_state_cols + [self.done_col])
        S  = df[self.state_cols].to_numpy()
        A  = df[self.action_col].astype(int).to_numpy()
        R  = df[self.reward_col].to_numpy()
        S2 = df[self.next_state_cols].to_numpy()
        D  = df[self.done_col].astype(bool).to_numpy()
        return S, A, R, S2, D

    def train(self, epochs=10, batch_size=32):
        S, A, R, S2, D = self._load_transitions()
        if len(S)==0:
            print("⚠️ RLTrainer: no hay datos para entrenar.")
            return DQNAgent(state_dim=len(self.state_cols), action_dim=1, model_path=self.model_path)
        agent = DQNAgent(state_dim=S.shape[1], action_dim=int(A.max())+1, model_path=self.model_path)
        agent.load()
        agent.train(S, A, R, S2, D, epochs=epochs, batch_size=batch_size)
        agent.save()
        return agent
