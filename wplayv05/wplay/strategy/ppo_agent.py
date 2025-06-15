# wplay/strategy/ppo_agent.py

import os
import logging
from typing import Optional, List, Tuple
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import load_model, clone_model


class PPOAgent:
    """
    Proximal Policy Optimization agent con:
      - Actor-critic (densas)
      - Scheduling opcional de LR
      - Buffer on-policy para online
      - Pre-entrenamiento offline
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.99,
        eps_clip: float = 0.2,
        K_epochs: int = 4,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        use_lr_schedule: bool = False,
        lr_decay_steps: int = 10000,
        lr_decay_rate: float = 0.9,
        path_actor: Optional[str] = None,
        path_critic: Optional[str] = None,
        model_path: Optional[str] = None,
    ):
        # Ajuste de rutas
        if model_path and not (path_actor or path_critic):
            path_actor = model_path.replace('.h5', '_actor.h5')
            path_critic = model_path.replace('.h5', '_critic.h5')

        # Parámetros PPO
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef

        # Configurar LR o scheduler
        if use_lr_schedule:
            self.actor_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                lr_actor, lr_decay_steps, lr_decay_rate, staircase=True
            )
            self.critic_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                lr_critic, lr_decay_steps, lr_decay_rate, staircase=True
            )
            lr_actor_used = self.actor_scheduler
            lr_critic_used = self.critic_scheduler
        else:
            self.actor_scheduler = None
            self.critic_scheduler = None
            lr_actor_used = lr_actor
            lr_critic_used = lr_critic

        # Construir redes y optimizadores
        self._build_networks(lr_actor_used, lr_critic_used)

        # Cargar pesos si hay path válidos
        if path_actor and os.path.exists(path_actor):
            self.actor.load_weights(path_actor)
        if path_critic and os.path.exists(path_critic):
            self.critic.load_weights(path_critic)

        # Buffers on-policy
        self.buffer_states: List[np.ndarray] = []
        self.buffer_actions: List[int] = []
        self.buffer_logprobs: List[float] = []
        self.buffer_rewards: List[float] = []
        self.buffer_dones: List[bool] = []
        self.buffer_values: List[float] = []
        self.update_counter = 0

        logging.basicConfig(level=logging.INFO)

    def _build_networks(self, lr_actor, lr_critic):
        """
        Construye actor y critic y guarda optimizadores.
        """
        # Actor
        self.actor = Sequential([
            Input(shape=(self.state_dim,)),
            Dense(128, activation='relu'),
            Dense(64, activation='relu'),
            Dense(self.action_dim, activation='softmax'),
        ])
        self.actor.compile(optimizer=Adam(learning_rate=lr_actor), loss='categorical_crossentropy')

        # Critic
        self.critic = Sequential([
            Input(shape=(self.state_dim,)),
            Dense(128, activation='relu'),
            Dense(64, activation='relu'),
            Dense(1, activation='linear'),
        ])
        self.critic.compile(optimizer=Adam(learning_rate=lr_critic), loss='mse')

        # Referencias a optimizadores
        self.actor_optimizer = self.actor.optimizer
        self.critic_optimizer = self.critic.optimizer

    def rebuild_network(self, new_state_dim: int):
        """
        Rebuild actor/critic preservando esquema de LR.
        """
        logging.info(f"[PPOAgent] Rebuild networks: {self.state_dim}→{new_state_dim}")
        self.state_dim = new_state_dim
        # Extraer lr o scheduler
        lr_a = self.actor_scheduler or float(self.actor.optimizer.learning_rate)
        lr_c = self.critic_scheduler or float(self.critic.optimizer.learning_rate)
        self._build_networks(lr_a, lr_c)

    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """
        Selecciona acción según la política, devuelve (action, logp, value).
        """
        s = state.reshape(1, -1)
        try:
            probs = self.actor.predict(s, verbose=0)[0]
        except:
            probs = np.ones(self.action_dim) / self.action_dim
        probs = np.clip(probs, 1e-8, None)
        probs /= probs.sum()
        action = np.random.choice(self.action_dim, p=probs)
        logp = float(np.log(probs[action]))
        try:
            value = float(self.critic.predict(s, verbose=0)[0, 0])
        except:
            value = 0.0
        return action, logp, value

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        log_prob: float,
        reward: float,
        done: bool,
        drawdown: float = 0.0
    ) -> None:
        """
        Guarda transición on-policy con reward shaping.
        """
        shaped = float(np.clip(reward, -1, 1) - 0.01 * drawdown)
        self.buffer_states.append(state)
        self.buffer_actions.append(action)
        self.buffer_logprobs.append(log_prob)
        self.buffer_rewards.append(shaped)
        self.buffer_dones.append(done)
        # valor actual
        v = self.critic.predict(state.reshape(1,-1), verbose=0)[0,0]
        self.buffer_values.append(float(v))

    def _compute_gae(self, rewards, dones, values, lam=0.95) -> np.ndarray:
        adv = np.zeros_like(rewards, dtype=np.float32)
        gae = 0.0
        for i in reversed(range(len(rewards))):
            mask = 1.0 - float(dones[i])
            delta = rewards[i] + self.gamma * values[i+1] * mask - values[i]
            gae = delta + self.gamma * lam * mask * gae
            adv[i] = gae
        return adv

    def update(self) -> Optional[Tuple[float, float, float]]:
        """
        Entrenamiento online PPO:
          - Calcula retornos y GAE
          - Ejecuta K_epochs de actualización
          - Limpia buffers y retorna métricas.
        """
        if not self.buffer_states:
            return None
        # Preparar batch
        S = np.vstack(self.buffer_states)
        A = np.array(self.buffer_actions)
        LP = np.array(self.buffer_logprobs)
        R = np.array(self.buffer_rewards, dtype=np.float32)
        D = np.array(self.buffer_dones, dtype=bool)
        V = np.array(self.buffer_values + [0.0], dtype=np.float32)

        # Retornos Monte Carlo
        returns = []
        G = 0.0
        for r, d in zip(reversed(R), reversed(D)):
            G = 0.0 if d else G
            G = r + self.gamma * G
            returns.insert(0, G)
        returns = np.array(returns, dtype=np.float32)

        # Ventajas (GAE)
        advantages = self._compute_gae(R, D, V)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Métricas acumuladas
        total_pl = total_vl = total_ent = 0.0
        # K epochs
        for _ in range(self.K_epochs):
            # Policy update
            with tf.GradientTape() as tape:
                probs = self.actor(S, training=True)
                dist = tfp.distributions.Categorical(probs=probs)
                new_lp = dist.log_prob(A)
                ent = tf.reduce_mean(dist.entropy())
                ratios = tf.exp(new_lp - LP)
                s1 = ratios * advantages
                s2 = tf.clip_by_value(ratios, 1-self.eps_clip, 1+self.eps_clip) * advantages
                pl = -tf.reduce_mean(tf.minimum(s1, s2))
            grads = tape.gradient(pl, self.actor.trainable_variables)
            self.actor_optimizer.apply_gradients(zip(grads, self.actor.trainable_variables))

            # Critic update
            with tf.GradientTape() as tape:
                vpred = tf.squeeze(self.critic(S, training=True))
                vl = tf.reduce_mean((returns - vpred)**2)
            grads_c = tape.gradient(vl, self.critic.trainable_variables)
            self.critic_optimizer.apply_gradients(zip(grads_c, self.critic.trainable_variables))

            total_pl += float(pl.numpy())
            total_vl += float(vl.numpy())
            total_ent += float(ent.numpy())

        # Limpiar buffers
        for buf in (self.buffer_states, self.buffer_actions, self.buffer_logprobs,
                    self.buffer_rewards, self.buffer_dones, self.buffer_values):
            buf.clear()

        self.update_counter += 1
        # Retornar métricas promedio
        return (
            total_pl / self.K_epochs,
            total_vl / self.K_epochs,
            total_ent / self.K_epochs
        )

    def _train_offline_core(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        returns: np.ndarray,
        advantages: np.ndarray,
        old_logprobs: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Single-step PPO offline update.
        """
        with tf.GradientTape(persistent=True) as tape:
            logits = self.actor(states, training=True)
            dist = tfp.distributions.Categorical(logits=logits)
            logp = dist.log_prob(actions)
            ent = tf.reduce_mean(dist.entropy())
            ratios = tf.exp(logp - old_logprobs)
            s1 = ratios * advantages
            s2 = tf.clip_by_value(ratios, 1-self.eps_clip, 1+self.eps_clip) * advantages
            policy_loss = -tf.reduce_mean(tf.minimum(s1, s2))

            values = tf.squeeze(self.critic(states, training=True), axis=-1)
            value_loss = tf.reduce_mean((returns - values)**2)

            actor_loss = policy_loss - self.entropy_coef * ent
            critic_loss = self.value_coef * value_loss

        grads_a = tape.gradient(actor_loss, self.actor.trainable_variables)
        grads_c = tape.gradient(critic_loss, self.critic.trainable_variables)
        self.actor_optimizer.apply_gradients(zip(grads_a, self.actor.trainable_variables))
        self.critic_optimizer.apply_gradients(zip(grads_c, self.critic.trainable_variables))
        del tape
        return (
            float(policy_loss.numpy()),
            float(value_loss.numpy()),
            float(ent.numpy())
        )

    def train_offline(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        returns: np.ndarray,
        advantages: np.ndarray,
        old_logprobs: np.ndarray,
        batch_size: int = 64,
        epochs: int = 3
    ) -> Optional[float]:
        """
        Batch training offline PPO.
        """
        N = len(states)
        if N < batch_size:
            return None
        pl_losses: List[float] = []
        for _ in range(epochs):
            perm = np.random.permutation(N)
            for start in range(0, N, batch_size):
                mb = perm[start:start+batch_size]
                pl, _, _ = self._train_offline_core(
                    states[mb], actions[mb], returns[mb], advantages[mb], old_logprobs[mb]
                )
                pl_losses.append(pl)
        return float(np.mean(pl_losses)) if pl_losses else None

    def save(self, path: str) -> None:
        """
        Guarda actor y critic y sus optimizadores.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Pesos
        self.actor.save_weights(path + '_actor.h5')
        self.critic.save_weights(path + '_critic.h5')

    def load(self, path: str) -> None:
        """
        Carga pesos de actor y critic.
        """
        if os.path.exists(path + '_actor.h5'):
            self.actor.load_weights(path + '_actor.h5')
        if os.path.exists(path + '_critic.h5'):
            self.critic.load_weights(path + '_critic.h5')
