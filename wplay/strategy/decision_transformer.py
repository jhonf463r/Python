# wplay/strategy/decision_transformer.py
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Dense, LayerNormalization, MultiHeadAttention

class DecisionTransformer(Model):
    """
    Simplified Decision Transformer:  
    - codifica secuencias de (state, action, return-to-go)  
    - entrena a predecir la siguiente acción
    """
    def __init__(self, seq_len: int, state_dim: int, action_dim: int, d_model: int = 128, n_head: int = 4):
        super().__init__()
        self.seq_len = seq_len
        self.state_dim = state_dim
        self.action_dim = action_dim

        # embeddings
        self.state_emb = Dense(d_model)
        self.return_emb = Dense(d_model)
        self.act_emb = Dense(d_model)

        # transformer block
        self.attn = MultiHeadAttention(n_head, key_dim=d_model)
        self.norm1 = LayerNormalization()
        self.norm2 = LayerNormalization()
        self.ff = tf.keras.Sequential([
            Dense(d_model*4, activation="relu"),
            Dense(d_model),
        ])

        # cabeza acción
        self.head = Dense(action_dim)

    def call(self, states, actions, returns_to_go):
        # estados: (B, T, S), acciones: (B, T), returns_to_go: (B, T)
        B, T, _ = tf.shape(states)
        s_emb = self.state_emb(states)        # (B, T, d)
        r_emb = self.return_emb(returns_to_go[..., None])
        a_emb = self.act_emb(actions[..., None])
        x = s_emb + r_emb + a_emb
        attn_out = self.attn(x, x)
        x = self.norm1(x + attn_out)
        ff_out = self.ff(x)
        x = self.norm2(x + ff_out)
        logits = self.head(x)  # (B, T, A)
        return logits

    def train_offline(self, dataset, epochs=10):
        """
        dataset: tf.data of (states_seq, actions_seq, returns_seq)
        """
        optimizer = tf.keras.optimizers.Adam()
        for epoch in range(epochs):
            for s_seq, a_seq, r_seq in dataset:
                with tf.GradientTape() as tape:
                    logits = self(s_seq, a_seq, r_seq)
                    # loss: crossentropy sobre la posición t+1 de acción
                    # ... implementación detallada según paper
                    loss = ...
                grads = tape.gradient(loss, self.trainable_variables)
                optimizer.apply_gradients(zip(grads, self.trainable_variables))
            print(f"[DT] Epoch {epoch+1}/{epochs} loss={loss.numpy():.4f}")
        # guardar
        os.makedirs("models", exist_ok=True)
        self.save_weights("models/decision_transformer.ckpt")
