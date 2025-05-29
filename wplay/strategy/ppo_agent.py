# Archivo: wplay/strategy/ppo_agent.py

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam

class PPOAgent:
    """
    Implementación básica de PPO con política y valor en Actor-Critic compartido.
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 3e-4,
        clip_ratio: float = 0.2,
        model_path: str = None
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.clip_ratio = clip_ratio
        self.model_path = model_path

        # Red compartida
        inp = Input(shape=(state_dim,))
        x = Dense(64, activation="tanh")(inp)
        x = Dense(64, activation="tanh")(x)

        # Cabeza de política
        pi_logits = Dense(action_dim)(x)
        # Cabeza de valor
        value = Dense(1)(x)

        self.model = Model(inputs=inp, outputs=[pi_logits, value])
        self.optimizer = Adam(learning_rate=lr)

    def select_action(self, state):
        """
        Dada una observación, devuelve (acción, probabilidades de todas las acciones).
        """
        logits, _ = self.model.predict(state[None], verbose=0)
        probs = tf.nn.softmax(logits[0]).numpy()
        action = np.random.choice(self.action_dim, p=probs)
        return action, probs

    def train(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        advantages: np.ndarray,
        returns: np.ndarray,
        old_log_probs: np.ndarray,
        epochs: int = 10,
        batch_size: int = 64
    ):
        """
        Entrena el agente PPO usando los arrays ya preparados:
        - states: forma (N, state_dim)
        - actions: índices de acción, forma (N,)
        - advantages: ventajas estimadas, forma (N,)
        - returns: retornos estimados, forma (N,)
        - old_log_probs: log-probs anteriores, forma (N,)
        """
        dataset = tf.data.Dataset.from_tensor_slices(
            (states, actions, advantages, returns, old_log_probs)
        ).shuffle(1000).batch(batch_size)

        for epoch in range(epochs):
            for s_batch, a_batch, adv_batch, ret_batch, oldp_batch in dataset:
                with tf.GradientTape() as tape:
                    # Forward
                    logits, values = self.model(s_batch, training=True)
                    values = tf.squeeze(values, axis=1)

                    # Log-probs de las acciones tomadas
                    logp_all = tf.nn.log_softmax(logits)
                    new_logp = tf.gather(logp_all, a_batch, axis=1, batch_dims=1)

                    # Ratio de probabilidad
                    ratio = tf.exp(new_logp - oldp_batch)

                    # Clip PPO
                    clipped = tf.clip_by_value(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio)
                    policy_loss = -tf.reduce_mean(tf.minimum(ratio * adv_batch, clipped * adv_batch))

                    # Pérdida de valor (MSE)
                    value_loss = tf.reduce_mean((ret_batch - values) ** 2)

                    # Pérdida total
                    loss = policy_loss + 0.5 * value_loss

                grads = tape.gradient(loss, self.model.trainable_variables)
                self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))

    def save(self, path: str = None):
        """
        Guarda el modelo en disco (formato Keras nativo o HDF5 según extensión).
        """
        if path is None:
            path = self.model_path
        if path:
            self.model.save(path)
            print(f"✔️ PPOAgent: modelo guardado en '{path}'")

    def load(self, path: str = None):
        """
        Carga un modelo previamente guardado.
        """
        if path is None:
            path = self.model_path
        if path and os.path.isfile(path):
            self.model = tf.keras.models.load_model(path)
            print(f"✔️ PPOAgent: modelo cargado desde '{path}'")
