import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
import os

class PPOAgent:
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.99,
        eps_clip: float = 0.2,
        K_epochs: int = 4,
        use_lr_schedule: bool = False,
        lr_decay_steps: int = 10000,
        lr_decay_rate: float = 0.9,
        path_actor: str = None,
        path_critic: str = None,
    ):
        self.state_dim      = state_dim
        self.action_dim     = action_dim
        self.gamma          = gamma
        self.eps_clip       = eps_clip
        self.K_epochs       = K_epochs
        self.use_lr_schedule = use_lr_schedule

        # ————— Scheduler opcional —————
        if use_lr_schedule:
            self.actor_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=lr_actor,
                decay_steps=lr_decay_steps,
                decay_rate=lr_decay_rate,
                staircase=True
            )
            self.critic_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=lr_critic,
                decay_steps=lr_decay_steps,
                decay_rate=lr_decay_rate,
                staircase=True
            )
            actor_lr  = self.actor_scheduler
            critic_lr = self.critic_scheduler
        else:
            self.actor_scheduler  = None
            self.critic_scheduler = None
            actor_lr  = lr_actor
            critic_lr = lr_critic

        # Construir redes con el lr (o scheduler) decidido
        self.actor   = self._build_actor(actor_lr)
        self.critic  = self._build_critic(critic_lr)

        # Cargar pesos si existen
        self.path_actor  = path_actor
        self.path_critic = path_critic
        if path_actor and os.path.exists(path_actor):
            self.actor.load_weights(path_actor)
        if path_critic and os.path.exists(path_critic):
            self.critic.load_weights(path_critic)

        # Buffers
        self.buffer_states   = []
        self.buffer_actions  = []
        self.buffer_logprobs = []
        self.buffer_rewards  = []
        self.buffer_dones    = []
        self.buffer_values   = []

    def _build_actor(self, lr) -> Sequential:
        model = Sequential([
            Dense(128, activation='relu', input_shape=(self.state_dim,)),
            Dense(64, activation='relu'),
            Dense(self.action_dim, activation='softmax'),
        ])
        model.compile(optimizer=Adam(learning_rate=lr), loss='categorical_crossentropy')
        return model

    def _build_critic(self, lr) -> Sequential:
        model = Sequential([
            Dense(128, activation='relu', input_shape=(self.state_dim,)),
            Dense(64, activation='relu'),
            Dense(1, activation='linear'),
        ])
        model.compile(optimizer=Adam(learning_rate=lr), loss='mse')
        return model

    def select_action(self, state: np.ndarray):
        """
        Devuelve (action_idx, log_prob, value) SIN tocar los buffers.
        """
        state_vect = state.reshape(1, -1)
        probs = self.actor.predict(state_vect, verbose=0)[0]
        action_idx = np.random.choice(self.action_dim, p=probs)
        log_prob = np.log(probs[action_idx] + 1e-8)
        value = float(self.critic.predict(state_vect, verbose=0)[0, 0])

        return action_idx, log_prob, value

    def store_transition(self, state, action, log_prob, reward, done, drawdown=0.0):
        """
        Guarda en los buffers de PPO:
        - state, action, logprob,
        - reward (con shaping penalizando drawdown),
        - done,
        - value estimado por el critic para ese state.
        """
        # 1) Shaping de recompensa penalizando drawdown
        shaped = np.clip(reward, -1.0, 1.0) - 0.1 * drawdown

        # 2) Append a cada buffer
        self.buffer_states.append(state)
        self.buffer_actions.append(action)
        self.buffer_logprobs.append(log_prob)
        self.buffer_rewards.append(shaped)
        self.buffer_dones.append(done)

        # 3) Guardar valor estimado por el critic para este state
        value = float(self.critic.predict(state.reshape(1, -1), verbose=0)[0, 0])
        self.buffer_values.append(value)


    def compute_values(self, states):
        # Normalizar outputs del critic
        values = self.critic(np.array(states))
        mean, std = tf.reduce_mean(values), tf.math.reduce_std(values)
        normed = (values - mean) / (std + 1e-8)
        return tf.clip_by_value(normed, -1, 1)
    
    def update(self):
            """
            Actualiza actor y critic usando los buffers.
            Retorna: (policy_loss, value_loss, avg_entropy)
            """
            # 1) Apilar los arrays
            all_states     = np.vstack(self.buffer_states)
            all_actions    = np.array(self.buffer_actions)
            all_logprobs   = np.array(self.buffer_logprobs)
            rewards        = np.array(self.buffer_rewards, dtype=np.float32)
            dones          = np.array(self.buffer_dones, dtype=bool)

            N = len(rewards)
            # 2) Recalcular valores y recortar al tamaño N
            all_values = self.critic.predict(all_states, verbose=0).flatten()
            states     = all_states[-N:]
            actions    = all_actions[-N:]
            old_logprobs= all_logprobs[-N:]
            values     = all_values[-N:]

            # 3) Calcular returns
            returns = []
            discounted = 0.0
            for r, done in zip(reversed(rewards), reversed(dones)):
                if done:
                    discounted = 0.0
                discounted = r + self.gamma * discounted
                returns.insert(0, discounted)
            returns = np.array(returns, dtype=np.float32)

            # 4) Ventajas normalizadas
            advantages = returns - values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

            # 5) Scheduler de LR (si aplica)
            if self.use_lr_schedule and self.actor_scheduler is not None:
                for epoch in range(self.K_epochs):
                    lr_a = self.actor_scheduler(epoch)
                    lr_c = self.critic_scheduler(epoch)
                    self.actor.optimizer.lr.assign(lr_a)
                    self.critic.optimizer.lr.assign(lr_c)

            # 6) Entrenamiento
            policy_loss = value_loss = entropy_sum = 0.0
            for _ in range(self.K_epochs):
                # Actor
                with tf.GradientTape() as tape_a:
                    probs = self.actor(states, training=True)
                    sel   = tf.reduce_sum(probs * tf.one_hot(actions, self.action_dim), axis=1)
                    new_logprobs = tf.math.log(sel + 1e-8)
                    ratios = tf.exp(new_logprobs - old_logprobs)
                    s1     = ratios * advantages
                    s2     = tf.clip_by_value(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
                    loss_a = -tf.reduce_mean(tf.minimum(s1, s2))
                    ent    = -tf.reduce_mean(tf.reduce_sum(probs * tf.math.log(probs + 1e-8), axis=1))
                    loss_a -= 0.01 * ent
                grads_a = tape_a.gradient(loss_a, self.actor.trainable_variables)
                self.actor.optimizer.apply_gradients(zip(grads_a, self.actor.trainable_variables))

                # Critic
                with tf.GradientTape() as tape_c:
                    vpred  = tf.squeeze(self.critic(states, training=True))
                    loss_c = tf.reduce_mean(tf.square(returns - vpred))
                grads_c = tape_c.gradient(loss_c, self.critic.trainable_variables)
                self.critic.optimizer.apply_gradients(zip(grads_c, self.critic.trainable_variables))

                policy_loss += loss_a.numpy()
                value_loss  += loss_c.numpy()
                entropy_sum += ent.numpy()

            # 7) Mantener sólo los últimos M elementos en el buffer
            M = 100
            self.buffer_states   = self.buffer_states[-M:]
            self.buffer_actions  = self.buffer_actions[-M:]
            self.buffer_logprobs = self.buffer_logprobs[-M:]
            self.buffer_rewards  = self.buffer_rewards[-M:]
            self.buffer_dones    = self.buffer_dones[-M:]
            self.buffer_values   = self.buffer_values[-M:]

            # 8) Promedios
            avg_policy  = policy_loss / self.K_epochs
            avg_value   = value_loss  / self.K_epochs
            avg_entropy = entropy_sum / self.K_epochs

            return avg_policy, avg_value, avg_entropy


    def train_offline(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        returns: np.ndarray,
        advantages: np.ndarray,
        old_logprobs: np.ndarray,
        epochs: int = 1,
        batch_size: int = 64
    ):
        """
        Entrenamiento offline usando los arrays dados.
        """
        for _ in range(epochs):
            # Actor
            with tf.GradientTape() as tape_actor:
                probs = self.actor(states, training=True)
                action_probs = tf.reduce_sum(
                    probs * tf.one_hot(actions, self.action_dim), axis=1)
                new_logprobs = tf.math.log(action_probs + 1e-8)
                ratios = tf.exp(new_logprobs - old_logprobs)
                surr1 = ratios * advantages
                surr2 = tf.clip_by_value(
                    ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
                loss_actor = -tf.reduce_mean(tf.minimum(surr1, surr2))
            grads_actor = tape_actor.gradient(
                loss_actor, self.actor.trainable_variables)
            self.actor.optimizer.apply_gradients(
                zip(grads_actor, self.actor.trainable_variables))

            # Critic
            with tf.GradientTape() as tape_critic:
                value_preds = tf.squeeze(self.critic(states, training=True))
                loss_critic = tf.reduce_mean(
                    tf.square(returns - value_preds))
            grads_critic = tape_critic.gradient(
                loss_critic, self.critic.trainable_variables)
            self.critic.optimizer.apply_gradients(
                zip(grads_critic, self.critic.trainable_variables))

    def save(self, path_actor: str, path_critic: str):
        os.makedirs(os.path.dirname(path_actor), exist_ok=True)
        os.makedirs(os.path.dirname(path_critic), exist_ok=True)
        self.actor.save(path_actor)
        self.critic.save(path_critic)

    def load(self, path_actor: str, path_critic: str):
        if os.path.exists(path_actor):
            self.actor.load_weights(path_actor)
        if os.path.exists(path_critic):
            self.critic.load_weights(path_critic)

    def log_metrics(
        self,
        episode: int,
        total_reward: float,
        loss_actor: float,
        loss_critic: float,
        avg_return: float
    ):
        print(
            f"[PPO] Episodio {episode} | Reward total: {total_reward:.2f} | "
            f"Return_prom: {avg_return:.2f} | Actor_loss: {loss_actor:.4f} | "
            f"Critic_loss: {loss_critic:.4f}"
        )
