# Archivo: wplay/strategy/ppo_agent.py
import os
import logging
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
from typing import Optional, Tuple, List, Any
from wplay.wplay_config.hyperparams import HyperParams
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam

# ------------------------------------------------------------------
# Funciones de inferencia “desacopladas” (placeholders)
# Serán reemplazadas en __init__ por las redes reales
# ------------------------------------------------------------------
@tf.function(input_signature=[tf.TensorSpec([None, None], tf.float32)])
def _ppo_infer_actor(x):
    raise RuntimeError("_ppo_infer_actor debe ser reemplazado en __init__")

@tf.function(input_signature=[tf.TensorSpec([None, None], tf.float32)])
def _ppo_infer_critic(x):
    raise RuntimeError("_ppo_infer_critic debe ser reemplazado en __init__")


class PPOAgent:
    """
    Proximal Policy Optimization agent con:
      - Actor‐critic (densas)
      - Reconstrucción dinámica de redes
      - Buffer on‐policy para online
      - Pre‐entrenamiento offline
    """

    def _infer_actor(self, x: tf.Tensor) -> tf.Tensor:
        return self.actor(x, training=False)

    def _infer_critic(self, x: tf.Tensor) -> tf.Tensor:
        return self.critic(x, training=False)
    def _try_load_weights(self, model_obj: Model, weight_file: str):

            if os.path.exists(weight_file):
                try:
                    model_obj.load_weights(weight_file)
                    logging.info(f"[PPOAgent] Pesos cargados desde {weight_file}")
                except Exception as e:
                    logging.warning(f"[PPOAgent] No pude cargar pesos de {weight_file}: {e}")
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hp: HyperParams,
        model_path: Optional[str] = None,
    ):
        # —– Rutas y dimensiones –—
        # Normalizar a .h5 tanto actor como critic
        base = model_path or hp.model_base_path
        # Actor
        path_actor = base.replace('.json', '_actor.h5')
        if not path_actor.endswith('.h5'):
            path_actor = os.path.splitext(path_actor)[0] + '_actor.h5'
        # Critic
        path_critic = base.replace('.json', '_critic.h5')
        if not path_critic.endswith('.h5'):
            path_critic = os.path.splitext(path_critic)[0] + '_critic.h5'

        self.path_actor, self.path_critic = path_actor, path_critic
        self.state_dim, self.action_dim = state_dim, action_dim

        # —– Hiperparámetros PPO –—
        self.gamma        = hp.ppo_gamma
        self.lam          = hp.ppo_lam
        self.eps_clip     = hp.ppo_eps_clip
        self.K_epochs     = hp.ppo_K_epochs
        self.entropy_coef = hp.ppo_entropy_coef
        self.value_coef   = hp.ppo_value_coef

        # —– Arquitectura –—
        self.actor_hidden_units  = hp.ppo_actor_hidden
        self.critic_hidden_units = hp.ppo_critic_hidden

        # —– Scheduler opcional –—
        if hp.ppo_use_lr_schedule:
            self.actor_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                hp.ppo_lr_actor, hp.ppo_lr_decay_steps, hp.ppo_lr_decay_rate, staircase=True
            )
            self.critic_scheduler = tf.keras.optimizers.schedules.ExponentialDecay(
                hp.ppo_lr_critic, hp.ppo_lr_decay_steps, hp.ppo_lr_decay_rate, staircase=True
            )
            lr_actor, lr_critic = self.actor_scheduler, self.critic_scheduler
        else:
            self.actor_scheduler = self.critic_scheduler = None
            lr_actor, lr_critic = hp.ppo_lr_actor, hp.ppo_lr_critic

        # —– Construcción de actor & critic –—
        self._build_networks(lr_actor, lr_critic)
        self.actor.build(input_shape=(None, self.state_dim))
        self.critic.build(input_shape=(None, self.state_dim))

        # —– Carga de pesos preexistentes –—


        self._try_load_weights(self.actor,  self.path_actor)
        self._try_load_weights(self.critic, self.path_critic)


        # —– Optimizadores y compilación –—
        self.actor_optimizer  = Adam(learning_rate=lr_actor)
        self.critic_optimizer = Adam(learning_rate=lr_critic)
        self.actor.compile(optimizer=self.actor_optimizer, loss='categorical_crossentropy')
        self.critic.compile(optimizer=self.critic_optimizer, loss='mse')

        # —– Buffers on‐policy –—
        self.buffer_states   = []
        self.buffer_actions  = []
        self.buffer_logprobs = []
        self.buffer_rewards  = []
        self.buffer_dones    = []
        self.buffer_values   = []
        self.update_counter  = 0

        logging.info(
            f"[PPOAgent] Init state_dim={self.state_dim}, action_dim={self.action_dim}, "
            f"actor_hidden={self.actor_hidden_units}, critic_hidden={self.critic_hidden_units}"
        )
        logging.info(f"[PPOAgent] eps_clip={self.eps_clip}, gamma={self.gamma}")

       
        # “Quemar” la compilación con un dummy antes del bucle de entrenamiento
        dummy = tf.zeros([1, self.state_dim], dtype=tf.float32)
        _ = self._infer_actor(dummy)
        _ = self._infer_critic(dummy)
        logging.info("[PPOAgent] Funciones de inferencia compiladas con input_signature")


    def try_load_actor(self, path: str):
        try:
            tmp = tf.keras.models.load_model(path, compile=False)
            loaded_out = tmp.output_shape[-1]
            if loaded_out != self.action_dim:
                logging.warning(
                    f"[PPOAgent] actor_out={loaded_out} ≠ action_dim={self.action_dim} → "
                    "ajustando action_dim y reconstruyendo actor"
                )
                self.action_dim = loaded_out
                self._rebuild_actor()
            else:
                self.actor.load_weights(path)
                logging.info(f"[PPOAgent] Pesos actor cargados desde {path}")
        except Exception as e:
            logging.warning(f"[PPOAgent] No pude cargar actor de {path}: {e}")

    def try_load_critic(self, path: str):
        try:
            tmp = tf.keras.models.load_model(path, compile=False)
            self.critic.load_weights(path)
            logging.info(f"[PPOAgent] Pesos critic cargados desde {path}")
        except Exception as e:
            logging.warning(f"[PPOAgent] No pude cargar critic de {path}: {e}")

        if self.path_actor and os.path.exists(self.path_actor):
            self.try_load_actor(self.path_actor)
        if self.path_critic and os.path.exists(self.path_critic):
            self.try_load_critic(self.path_critic)


    def select_action(self, state: np.ndarray) -> int:
        """
        Selecciona acción usando la política actual. Si la salida del actor
        o la dimensión del estado cambian, reconstruye las redes oportunamente.
        """
        s = np.asarray(state, dtype=np.float32)
        if s.ndim == 1:
            s = s[np.newaxis, :]

        # Reconstrucción si cambia dimensión de estado
        curr_dim = s.shape[1]
        if curr_dim != self.state_dim:
            logging.warning(
                f"[PPOAgent] state_dim mismatch: {self.state_dim} → {curr_dim} → "
                "reconstruyendo redes completas"
            )
            self.state_dim = curr_dim
            self._rebuild_networks_and_compile()

        # Inferencia
        probs = self._infer_actor(tf.constant(s)).numpy()[0]
        # Si la salida del actor no coincide, reconstruimos solo el actor
        out_dim = probs.shape[-1]
        if out_dim != self.action_dim:
            logging.warning(
                f"[PPOAgent] actor_out mismatch: {out_dim} ≠ {self.action_dim} → "
                "reconstruyendo actor"
            )
            self.action_dim = out_dim
            self._rebuild_actor()
            probs = self._infer_actor(tf.constant(s)).numpy()[0]

        # Normalizar y muestrear
        probs = np.clip(probs, 1e-8, None)
        probs /= probs.sum()
        action = int(np.random.choice(self.action_dim, p=probs))

        # Registro on‑policy
        self.buffer_states.append(s[0])
        self.buffer_actions.append(action)
        self.buffer_logprobs.append(float(np.log(probs[action])))

        return action


    def predict_value(self, state: np.ndarray) -> float:
        s = np.asarray(state, dtype=np.float32)
        if s.ndim == 1:
            s = s[np.newaxis, :]
        return float(self._infer_critic(tf.constant(s)).numpy()[0, 0])

    def _build_networks(self, lr_actor: Any, lr_critic: Any):
        # Actor
        inp = Input(shape=(self.state_dim,))
        x = inp
        for u in self.actor_hidden_units:
            x = Dense(u, activation='relu')(x)
        out_actor = Dense(self.action_dim, activation='softmax')(x)
        self.actor = Model(inputs=inp, outputs=out_actor)

        # Critic
        inp_c = Input(shape=(self.state_dim,))
        y = inp_c
        for u in self.critic_hidden_units:
            y = Dense(u, activation='relu')(y)
        out_critic = Dense(1, activation='linear')(y)
        self.critic = Model(inputs=inp_c, outputs=out_critic)

        logging.info(
            f"[PPOAgent] Redes construidas: actor_hidden={self.actor_hidden_units}, "
            f"critic_hidden={self.critic_hidden_units}, action_dim={self.action_dim}"
        )

    def _rebuild_actor(self):
        """Reconstruye solo el actor para que coincida con self.action_dim."""
        logging.debug(f"[PPOAgent] Reconstruyendo actor → action_dim={self.action_dim}")
        inp = Input(shape=(self.state_dim,))
        x = inp
        for u in self.actor_hidden_units:
            x = Dense(u, activation='relu')(x)
        out_actor = Dense(self.action_dim, activation='softmax')(x)
        self.actor = Model(inputs=inp, outputs=out_actor)
        self.actor.compile(optimizer=self.actor_optimizer, loss='categorical_crossentropy')
        self.actor.build(input_shape=(None, self.state_dim))

    def _rebuild_networks_and_compile(self):
        """
        Reconstruye actor y critic tras un cambio en self.state_dim.
        Mantiene hiperparámetros de compilación.
        """
        logging.debug(f"[PPOAgent] Reconstruyendo actor+critic → state_dim={self.state_dim}")
        # Recuperar lr actuales
        try:
            lr_a = self.actor_scheduler or float(self.actor_optimizer.learning_rate)
            lr_c = self.critic_scheduler or float(self.critic_optimizer.learning_rate)
        except:
            lr_a = lr_c = 1e-4
            logging.warning("[PPOAgent] No pude recuperar lr, usando 1e-4 por defecto")

        # Rebuild
        self._build_networks(lr_a, lr_c)

        # Re‑compilar
        self.actor_optimizer  = Adam(learning_rate=lr_a)
        self.critic_optimizer = Adam(learning_rate=lr_c)
        self.actor.compile(optimizer=self.actor_optimizer, loss='categorical_crossentropy')
        self.critic.compile(optimizer=self.critic_optimizer, loss='mse')

        self.actor.build(input_shape=(None, self.state_dim))
        self.critic.build(input_shape=(None, self.state_dim))
        logging.info("[PPOAgent] Reconstrucción completa OK")

    def rebuild_network(self, new_state_dim: int):
        """
        Reconstruye actor y critic si cambia la dimensión del estado.
        Actualiza self.state_dim SOLO después de construir las redes.
        """
        logging.debug(f"[PPOAgent·REBUILD_REQUEST] {self.state_dim} → {new_state_dim}")
        if new_state_dim <= 0:
            logging.warning(f"[PPOAgent] Dim inválida: {new_state_dim}")
            return

        current_input_dim = self.actor.input_shape[-1]
        if new_state_dim == current_input_dim:
            return  # ya coincide, nada que hacer

        logging.warning(f"[PPOAgent] Rebuild necesario: input_shape={current_input_dim} → {new_state_dim}")

        # Recuperar LR actuales
        try:
            lr_a = self.actor_scheduler or float(self.actor_optimizer.learning_rate)
            lr_c = self.critic_scheduler or float(self.critic_optimizer.learning_rate)
        except Exception:
            lr_a = lr_c = 1e-4
            logging.warning("[PPOAgent] No se pudo recuperar LR, usando 1e-4")

        # Reconstruir redes con nuevo input
        self.state_dim = new_state_dim  # <- actualizar antes de llamar _build_networks
        self._build_networks(lr_a, lr_c)

        # Compilar y build
        self.actor_optimizer  = Adam(learning_rate=lr_a)
        self.critic_optimizer = Adam(learning_rate=lr_c)
        self.actor.compile(optimizer=self.actor_optimizer, loss='categorical_crossentropy')
        self.critic.compile(optimizer=self.critic_optimizer, loss='mse')

        self.actor.build(input_shape=(None, self.state_dim))
        self.critic.build(input_shape=(None, self.state_dim))

        logging.info(f"[PPOAgent·REBUILD_DONE] Redes reconstruidas con state_dim={self.state_dim}")


    
    def store_transition(
            self,
            state: np.ndarray,
            action: int,
            reward: float,
            next_state: Optional[np.ndarray] = None,
            done: bool = False,
            log_prob: float = 0.0,
            drawdown: float = 0.0,
            **kwargs
        ):
            """
            Almacena transición on-policy, rebuild si cambia dimensión.
            """
            s = state.flatten()
            dims = s.shape[0]
            if dims != self.state_dim:
                logging.debug(f"[PPOAgent·STORE] shape={dims}, agent.state_dim={self.state_dim}")
                self.rebuild_network(dims)

            shaped = float(np.clip(reward, -1, 1) - 0.01 * drawdown)
            self.buffer_states.append(s.astype(np.float32))
            self.buffer_actions.append(action)
            self.buffer_logprobs.append(log_prob)
            self.buffer_rewards.append(shaped)
            self.buffer_dones.append(done)
            # Valor estimado
            v = self.critic.predict(s.reshape(1, -1), verbose=0)[0, 0]
            self.buffer_values.append(float(v))

  
    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: Optional[np.ndarray],
        done: bool
    ) -> None:
        """
        Almacena la transición (s, a, r, s', done) en el buffer interno.
        Wrapper sobre store_transition. Se ignora next_state por compatibilidad.
        """
        # Validar y ajustar dimensión de estado
        dim = state.shape[0] if state.ndim == 1 else state.shape[1]
        if dim != self.state_dim:
            self.rebuild_network(dim)

        # Usar store_transition, ignorando next_state (por ahora no se usa)
        self.store_transition(
            state=state,
            action=action,
            reward=reward,
            done=done,
            next_state=next_state
        )



    def _compute_gae(self, rewards, dones, values, lam=0.95):
        """Genera ventajas con GAE."""
        adv = np.zeros_like(rewards, dtype=np.float32)
        gae = 0.0
        for i in reversed(range(len(rewards))):
            mask  = 1.0 - float(dones[i])
            delta = rewards[i] + self.gamma*values[i+1]*mask - values[i]
            gae   = delta + self.gamma*lam*mask*gae
            adv[i]= gae
        return adv

    def update(self) -> Optional[Tuple[float, float, float]]:
        """Entrenamiento online PPO completo."""
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

        # Ventajas normalizadas con GAE (usa self.lam internamente)
        advantages = self._compute_gae(R, D, V)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_pl = total_vl = total_ent = 0.0

        # K_epochs pasos de actualización
        for _ in range(self.K_epochs):
            # --- Update Actor ---
            with tf.GradientTape() as tape_a:
                probs = self.actor(S, training=True)
                dist = tfp.distributions.Categorical(probs=probs)
                new_lp = dist.log_prob(A)
                ent = tf.reduce_mean(dist.entropy())

                ratios = tf.exp(new_lp - LP)
                s1 = ratios * advantages
                s2 = tf.clip_by_value(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
                pl = -tf.reduce_mean(tf.minimum(s1, s2))

            grads_a = tape_a.gradient(pl, self.actor.trainable_variables)
            self.actor_optimizer.apply_gradients(zip(grads_a, self.actor.trainable_variables))

            # --- Update Critic ---
            with tf.GradientTape() as tape_c:
                vpred = tf.squeeze(self.critic(S, training=True), -1)
                vl = tf.reduce_mean((returns - vpred) ** 2)

            grads_c = tape_c.gradient(vl, self.critic.trainable_variables)
            self.critic_optimizer.apply_gradients(zip(grads_c, self.critic.trainable_variables))

            total_pl += float(pl.numpy())
            total_vl += float(vl.numpy())
            total_ent += float(ent.numpy())

        # Limpiar buffers para el siguiente ciclo
        for buf in (
            self.buffer_states,
            self.buffer_actions,
            self.buffer_logprobs,
            self.buffer_rewards,
            self.buffer_dones,
            self.buffer_values,
        ):
            buf.clear()

        self.update_counter += 1

        # Devolver pérdidas y entropía promedio
        return (
            total_pl / self.K_epochs,
            total_vl / self.K_epochs,
            total_ent / self.K_epochs,
        )


    def train(self) -> Optional[Tuple[float, float, float]]:
        """
        Entrena al agente PPO con las transiciones almacenadas (on-policy).
        Devuelve las pérdidas promedio si hay entrenamiento, o None si no hay datos.
        """
        return self.update()

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

    def save(self, path: str):
        """Guarda pesos actor y critic."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.actor.save_weights(path + '_actor.h5')
        self.critic.save_weights(path + '_critic.h5')

    def load(self, path: str):
        """Carga pesos actor y critic."""
        if os.path.exists(path + '_actor.h5'):
            self.actor.load_weights(path + '_actor.h5')
        if os.path.exists(path + '_critic.h5'):
            self.critic.load_weights(path + '_critic.h5')
    def save_model(self, path: str):
        """
        Guarda actor y critic en HDF5 dentro de 'path' (puede ser carpeta o prefijo).
        """
        # si path no tiene .h5, tratémoslo como carpeta
        if not path.endswith('.h5'):
            os.makedirs(path, exist_ok=True)
            actor_file  = os.path.join(path, 'actor.h5')
            critic_file = os.path.join(path, 'critic.h5')
        else:
            # path es un prefijo .h5: actor.h5 y critic.h5 al mismo nivel
            actor_file  = path.replace('.h5', '_actor.h5')
            critic_file = path.replace('.h5', '_critic.h5')
            os.makedirs(os.path.dirname(actor_file), exist_ok=True)

        self.actor.save_weights(actor_file)
        self.critic.save_weights(critic_file)
        logging.info(f"[PPOAgent] Pesos guardados en {actor_file} y {critic_file}")

    def load_model(self, path: str):
        """
        Carga actor/critic desde HDF5 en 'path' (carpeta o prefijo).
        """
        if not path.endswith('.h5'):
            actor_file  = os.path.join(path, 'actor.h5')
            critic_file = os.path.join(path, 'critic.h5')
        else:
            actor_file  = path.replace('.h5', '_actor.h5')
            critic_file = path.replace('.h5', '_critic.h5')

        self._try_load_weights(self.actor,  self.path_actor)
        self._try_load_weights(self.critic, self.path_critic)
# -------------------------------------------------------------
# FUERA de la definición de la clase, definimos una única vez
# el tf.function para ambas inferencias, con signature dinámico
# -------------------------------------------------------------
spec = tf.TensorSpec(shape=[None, None], dtype=tf.float32)
PPOAgent._infer_actor  = tf.function(PPOAgent._infer_actor,  input_signature=[spec], reduce_retracing=True)
PPOAgent._infer_critic = tf.function(PPOAgent._infer_critic, input_signature=[spec], reduce_retracing=True)