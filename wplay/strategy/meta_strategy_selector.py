# wplay/strategies/meta_strategy_selector.py

import os
import logging
import joblib
import numpy as np
import tensorflow as tf
from collections import deque
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam
from wplay.data.utils import safe_load_model
from wplay.utils.chaos import compute_hurst, compute_lyapunov, shannon_entropy
from wplay.utils.meta_utils import compute_meta_stats
from wplay.wplay_config.hyperparams import HyperParams
from typing import Optional, List
from tensorflow.keras.models import load_model as tf_load_model

class MetaStrategySelector:
    def __init__(self, *args, **kwargs):
        """
        Constructor compatible con:
          - Viejas llamadas posicionales: (state_dim, action_dim, hypernet, hp)
          - Viejas llamadas keyword: state_dim=…, action_dim=…, hypernet=…, hp=…
          - Nuevas con overrides legacy: strategy_list, strategies, model_path, window…
          - Nuevas basadas en hp: hp=HyperParams(...)
        """
        import tensorflow as tf
        from wplay.wplay_config.hyperparams import HyperParams
        from collections import deque
        import numpy as np
        import os

        # 1) Extraer state_dim y action_dim
        if 'state_dim' in kwargs:
            self.state_dim = kwargs.pop('state_dim')
        elif len(args) >= 1:
            self.state_dim = args[0]
        else:
            raise TypeError("state_dim no proporcionado a MetaStrategySelector")

        if 'action_dim' in kwargs:
            self.action_dim = kwargs.pop('action_dim')
        elif len(args) >= 2:
            self.action_dim = args[1]
        else:
            raise TypeError("action_dim no proporcionado a MetaStrategySelector")

        # 2) Extraer hp y hypernet (por tipo o keyword)
        hp = kwargs.pop('hp', None)
        hypernet = kwargs.pop('hypernet', None)
        for a in args[2:]:
            if isinstance(a, HyperParams):
                hp = a
            elif isinstance(a, tf.keras.Model):
                hypernet = a
        if hp is None:
            raise TypeError("hp (HyperParams) no proporcionado a MetaStrategySelector")
        if hypernet is None:
            raise TypeError("hypernet (tf.keras.Model) no proporcionado a MetaStrategySelector")

        # 3) Overrides legacy: strategy_list/strategies, model_path, window
        strategy_list = kwargs.pop('strategy_list', None) or kwargs.pop('strategies', None)
        model_path    = kwargs.pop('model_path', None)
        window        = kwargs.pop('window', hp.meta_window)

        # --- lista de estrategias ---
        if strategy_list is not None:
            self.strategy_list = strategy_list
        else:
            self.strategy_list = hp.meta_strategies or ["dqn", "ppo", "skip"]
        self.n_strategies = len(self.strategy_list)

        # --- path de modelo ---
        self.model_path = model_path or hp.meta_model_path

        # --- parámetros básicos ---
        self.hypernet   = hypernet
        self.use_ts     = hp.meta_use_ts
        self.ucb_c      = hp.meta_ucb_c

        # --- hiperparámetros inyectados ---
        self.window          = window
        self.meta_lr         = hp.meta_lr
        self.meta_epochs     = hp.meta_epochs
        self.meta_batch_size = hp.meta_batch_size or window
        self.L_thresh        = hp.L_thresh
        self.H_thresh        = hp.H_thresh
        self.ENT_thresh      = hp.ENT_thresh

        # --- buffers y contadores ---
        self.reward_history  = deque(maxlen=self.window)
        self._offline_states = deque(maxlen=self.window)
        self._offline_idxs   = deque(maxlen=self.window)
        self.counts          = np.zeros(self.n_strategies, dtype=int)
        self.values          = np.zeros(self.n_strategies, dtype=float)
        self.total_counts    = 0
        self.successes       = np.zeros(self.n_strategies, dtype=int)
        self.failures        = np.zeros(self.n_strategies, dtype=int)

        # --- wiring de agentes (asignados externamente) ---
        self.dqn_agent = None
        self.ppo_agent = None

        # --- asegurar carpeta y cargar/crear modelo meta ---
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        self._build_or_load_model()
        logging.info(f"[META] window={self.window}")

    def _build_or_load_model(self):
        """
        Carga un modelo existente si sus shapes coinciden con state_dim/action_dim,
        o lo (re)construye en caso contrario. Logs de debug reforzados.
        """
        logging.debug(f"[META·LOAD] Intentando cargar modelo en {self.model_path}")
        if os.path.exists(self.model_path):
            loaded = safe_load_model(self.model_path)
            in_dim  = getattr(loaded, "input_shape", (None, None))[1]
            out_dim = getattr(loaded, "output_shape", (None, None))[1]
            logging.debug(f"[META·LOAD] Modelo cargado: input_dim={in_dim}, output_dim={out_dim}")

            if in_dim != self.state_dim or out_dim != self.n_strategies:
                logging.warning(
                    f"[META·LOAD] Incompatible (in:{in_dim}/{self.state_dim}, "
                    f"out:{out_dim}/{self.n_strategies}) → rebuild_model()"
                )
                try: os.remove(self.model_path)
                except: pass
                self.rebuild_model()
                return

            # Debug: imprimimos summary a lista
            lines = []
            loaded.summary(print_fn=lambda s: lines.append(s))
            logging.debug("[META·LOAD] Model summary:\n" + "\n".join(lines))

            self.model = loaded
            return

        logging.debug("[META·LOAD] No existe modelo previo, llamando a rebuild_model()")
        self.rebuild_model()


    def rebuild_model(self):
        """
        Reconstruye el meta-modelo cuando cambia self.state_dim o al inicializar,
        usando self.meta_lr para el optimizador.
        """
        logging.info(f"[META·REBUILD] Reconstruyendo modelo input_dim={self.state_dim}, "
                     f"output_dim={self.n_strategies}")
        try:
            os.remove(self.model_path)
        except OSError:
            pass

        # Definición de la nueva arquitectura
        inp = Input(shape=(self.state_dim,), name="state_input")
        x = Dense(64, activation="relu")(inp)
        x = Dense(64, activation="relu")(x)
        out = Dense(self.n_strategies, activation="softmax")(x)
        self.model = tf.keras.Model(inputs=inp, outputs=out)

        # ⬆️ mod.: usar el learning rate configurable
        self.model.compile(
            optimizer=Adam(self.meta_lr),
            loss="categorical_crossentropy"
        )

        # Guardar inmediatamente la nueva versión en disco
        self.model.save(self.model_path)
        # Mostrar summary por debug
        summary_lines = []
        self.model.summary(print_fn=lambda s: summary_lines.append(s))
        logging.debug("[META·REBUILD] Nuevo summary:\n" + "\n".join(summary_lines))

    def _rebuild_meta(self):
        """
        Reconstruye el meta-selector con self.state_dim_total y self.action_dim,
        preservando estadísticas previas.
        """
        # Guardamos las estadísticas anteriores (si existía)
        old = None
        if self.meta:
            old = {
                'counts':        self.meta.counts.copy(),
                'values':        self.meta.values.copy(),
                'total_counts':  self.meta.total_counts,
                'successes':     self.meta.successes.copy(),
                'failures':      self.meta.failures.copy(),
                'reward_hist':   deque(self.meta.reward_history, maxlen=self.meta.window),
                'off_states':    deque(self.meta._offline_states, maxlen=self.meta.window),
                'off_idxs':      deque(self.meta._offline_idxs,   maxlen=self.meta.window),
            }

        # Reconstrucción
        self.meta = MetaStrategySelector(
            state_dim     = self.state_dim_total,
            action_dim    = self.action_dim,
            strategy_list = ["dqn", "ppo", "skip"],
            model_path    = os.path.join(self.model_dir, "meta_strategy_selector.keras"),
            window        = self.window_rl,
            ucb_c         = 1.0,
            use_ts        = True
        )
        self.meta.dqn_agent = self.rl_agent_dqn
        self.meta.ppo_agent = self.rl_agent_ppo

        # Restaurar estadísticas
        if old:
            self.meta.counts         = old['counts']
            self.meta.values         = old['values']
            self.meta.total_counts   = old['total_counts']
            self.meta.successes      = old['successes']
            self.meta.failures       = old['failures']
            self.meta.reward_history = old['reward_hist']
            self.meta._offline_states= old['off_states']
            self.meta._offline_idxs  = old['off_idxs']

        logging.info(
            f"[META] Reconstruido con state_dim_total={self.state_dim_total} "
            f"action_dim={self.action_dim}"
        )



    def update(self, strategy: str, reward: float, state: np.ndarray = None, retrain: bool = True):
        """
        Actualiza estadísticas UCB/TS y acumula samples para retrain.
        Cuando se cumple la ventana, dispara _retrain_meta_model().
        """
        try:
            idx = self.strategy_list.index(strategy)
        except ValueError:
            logging.warning(f"[META] update(): estrategia desconocida '{strategy}'")
            return

        # UCB/TS updates
        self.reward_history.append(reward)
        self.counts[idx] += 1
        self.total_counts += 1
        self.values[idx] += (reward - self.values[idx]) / self.counts[idx]
        (self.successes if reward>0 else self.failures)[idx] += 1

        # Off‐policy buffer
        st = np.zeros((self.state_dim,), dtype=np.float32) if state is None else state.astype(np.float32)
        self._offline_states.append(st)
        self._offline_idxs.append(idx)

        # Retrain periódico
        if retrain and len(self.reward_history) >= self.window and len(self.reward_history) % self.window == 0:
            logging.info(f"[META] Ventana {self.window} alcanzada → retrain")
            self._retrain_meta_model()


    def _retrain_meta_model(self):
            """
            Reentrena el meta‐modelo con X=estados offline, y Y=one-hot(off_idxs).
            """
            X = np.stack(self._offline_states, axis=0)
            y = np.eye(self.n_strategies, dtype=np.float32)[list(self._offline_idxs)]

            tf.config.run_functions_eagerly(True)
            # ⬆️ mod. usar self.meta_lr
            self.model.compile(optimizer=Adam(self.meta_lr), loss='categorical_crossentropy')

            # ⬆️ mod. usar self.meta_epochs y self.meta_batch_size
            self.model.fit(
                X, y,
                epochs=self.meta_epochs,
                batch_size=self.meta_batch_size,
                verbose=1
            )
            tf.config.run_functions_eagerly(False)

            self.model.save(self.model_path)
            logging.info(f"[META] meta‐modelo retrained (epochs={self.meta_epochs}, batch_size={self.meta_batch_size}) y guardado en {self.model_path}")



    def estimate_reward(self, arm: str, state: np.ndarray, action: int) -> float:
        """
        Estima recompensa hipotética para el brazo no elegido (off-policy):
        - DQN: Q(s,a) desde predict_q (que recorta a state_dim).
        - PPO: π(a|s) extraída de su actor.
        """
        # 0) Preparar el estado recortado/normalizado
        if arm == 'dqn':
            if self.dqn_agent is None:
                logging.warning("[META] estimate_reward: DQNAgent no inicializado")
                return 0.0
            # _clip_state_dqn devuelve un vector de longitud state_dim
            s_proc = self._clip_state_dqn(state)
        elif arm == 'ppo':
            if self.ppo_agent is None:
                logging.warning("[META] estimate_reward: PPOAgent no inicializado")
                return 0.0
            s_proc = self._clip_state_ppo(state)
        else:
            logging.warning(f"[META] estimate_reward: brazo desconocido '{arm}'")
            return 0.0

        # 1) Expandir batch dimension
        s_batch = np.expand_dims(s_proc.astype(np.float32), axis=0)

        # 2) DQN: obtener Q(s,a) usando predict_q (que recorta internamente)
        if arm == 'dqn':
            try:
                q_vals = self.dqn_agent.predict_q(s_batch)  # shape (1, action_dim)
                return float(q_vals[0, action])
            except Exception as e:
                logging.warning(f"[META] estimate_reward DQN.predict_q falló: {e}")
                return 0.0

        # 3) PPO: obtener π(a|s) desde el actor
        if arm == 'ppo':
            if hasattr(self.ppo_agent, 'actor'):
                try:
                    probs = self.ppo_agent.actor(
                        tf.constant(s_batch), training=False
                    ).numpy()  # shape (1, action_dim)
                    return float(probs[0, action])
                except Exception as e:
                    logging.warning(f"[META] estimate_reward PPO.actor falló: {e}")
                    return 0.0
            logging.warning("[META] PPOAgent no expone 'actor'")
            return 0.0

        return 0.0

    def estimate_reward(self, arm: str, state: np.ndarray, action: int) -> float:
        """
        Estima recompensa hipotética off-policy para un brazo NO elegido.
        """
        # 0) Aseguramos la forma (1, state_dim)
        s_full = np.expand_dims(state.astype(np.float32), 0)

        # 1) DQN → Q(s,a)
        if arm == 'dqn' and self.dqn_agent is not None:
            if hasattr(self.dqn_agent, 'predict_q'):
                return float(self.dqn_agent.predict_q(s_full)[0, action])
            if hasattr(self.dqn_agent, 'q_network'):
                try:
                    q_vals = self.dqn_agent.q_network(s_full, training=False).numpy()
                    return float(q_vals[0, action])
                except Exception as e:
                    logging.warning(f"[META] estimate_reward DQN q_network falló: {e}")
            logging.warning("[META] DQNAgent no expone ni predict_q ni q_network")
            return 0.0

        # 2) PPO → π(a|s)
        if arm == 'ppo' and self.ppo_agent is not None:
            if hasattr(self.ppo_agent, 'actor'):
                try:
                    probs = self.ppo_agent.actor(s_full, training=False).numpy()
                    return float(probs[0, action])
                except Exception as e:
                    logging.warning(f"[META] estimate_reward PPO actor falló: {e}")
            logging.warning("[META] PPOAgent no expone 'actor'")
            return 0.0

        return 0.0




    def update_offpolicy(self, chosen: str, other: str, state: np.ndarray, action: int, real_reward: float):
            """
            Llama a update() para elegido y otro brazo, y luego lanza el retraining justo una vez.
            """
            # 1) Brazo elegido (on‐policy)
            self.update(chosen, real_reward, state, retrain=False)

            # 2) Brazo no elegido (off‐policy)
            r_est = self.estimate_reward(other, state, action)
            self.update(other, r_est, state, retrain=False)

            logging.debug(
                f"[META] Off-policy update: chosen={chosen} r={real_reward:.3f}, "
                f"other={other} r_est={r_est:.3f}"
            )

            # 3) Sólo tras dos actualizaciones, revisamos retrain
            if len(self.reward_history) >= self.window and len(self.reward_history) % self.window == 0:
                self._retrain_meta_model()
    @tf.function
    def _tf_predict(self, states: tf.Tensor) -> tf.Tensor:
        # 📌 CORRECCIÓN: función compilada sólo UNA VEZ
        return self.model(states, training=False)    
    @tf.function
    def _infer_meta(self, x: tf.Tensor) -> tf.Tensor:
        """
        Inferencia del meta-modelo en modo no entrenamiento.
        """
        return self.model(x, training=False)

    def select_strategy(self, state: np.ndarray) -> str:
            """
            Selecciona estrategia usando:
            1) Heurística caótica (Hurst/Lyapunov/Entropía)
            2) Meta‐modelo (+ hypernet si existe)
            3) Fallback Thompson-sampling / UCB
            Registra además estado e índice en buffers.
            """
            st = state.astype(np.float32).reshape(-1)
            actual_dim = st.shape[0]
            if actual_dim != self.state_dim:
                logging.warning(f"[META·SELECT] state_dim cambió {self.state_dim}→{actual_dim}, rebuild_model()")
                self.state_dim = actual_dim
                self.rebuild_model()

            # 1) Heurística caótica con umbrales configurables
            rewards = np.array(self.reward_history) if self.reward_history else np.array([0.0], dtype=np.float32)
            H   = compute_hurst(rewards)
            L   = compute_lyapunov(rewards)
            ENT = shannon_entropy(rewards)

            if L > self.L_thresh and H < self.H_thresh:                # ⬆️ mod.
                idx = self.strategy_list.index("dqn")
                self._offline_states.append(st); self._offline_idxs.append(idx)
                return "dqn"
            if H > self.H_thresh and ENT < self.ENT_thresh:            # ⬆️ mod.
                idx = self.strategy_list.index("ppo")
                self._offline_states.append(st); self._offline_idxs.append(idx)
                return "ppo"

            # 2) Meta‐modelo + Hypernetwork (sin cambios)
            try:
                x = tf.constant(st.reshape(1, self.state_dim), dtype=tf.float32)
                base_probs = self.model(x, training=False).numpy()[0]
                logging.debug(f"[META] base_probs={base_probs}")

                if self.hypernet is not None:
                    stats  = compute_meta_stats(base_probs, list(self.reward_history), window=self.window)
                    coeffs = self.hypernet(tf.expand_dims(stats, 0), training=False).numpy()[0]
                    scores = np.array([
                        coeffs[0]*base_probs[0],
                        coeffs[1]*base_probs[1],
                        coeffs[2]*base_probs[2] + coeffs[3]*stats[3]
                    ], dtype=np.float32)
                    idx = int(np.argmax(scores))
                    logging.debug(f"[META] coeffs={coeffs}, scores={scores}")
                else:
                    idx = int(np.argmax(base_probs))

                choice = self.strategy_list[idx]
                self._offline_states.append(st); self._offline_idxs.append(idx)
                return choice

            except Exception as e:
                logging.warning(f"[META·SELECT] meta‐model falló: {e}")

            # 3) Fallback TS / UCB (sin cambios)
            if self.use_ts:
                samples = [np.random.beta(1+s, 1+f) for s,f in zip(self.successes, self.failures)]
                idx = int(np.argmax(samples))
            else:
                untried = [i for i,c in enumerate(self.counts) if c==0]
                if untried:
                    idx = untried[0]
                else:
                    ucb = [
                        self.values[i] + self.ucb_c * np.sqrt(np.log(self.total_counts)/self.counts[i])
                        for i in range(self.n_strategies)
                    ]
                    idx = int(np.argmax(ucb))

            choice = self.strategy_list[idx]
            self._offline_states.append(st); self._offline_idxs.append(idx)
            return choice

    def train(self, states, strategy_indices, epochs=5, batch_size=32):
        X = np.array(states, dtype=np.float32)
        y = np.eye(self.n_strategies, dtype=np.float32)[strategy_indices]
        self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=1)

  
    def save_model(self, path: str):
        """
        Guarda el meta-modelo y su estado interno en la carpeta dada.
        """
        dst = path or self.model_path
        os.makedirs(dst, exist_ok=True)

        # 1) Guardar la arquitectura/pesos del modelo
        model_path = os.path.join(dst, "hypernet.keras")
        self.model.save(model_path)
        logging.info(f"[META] Modelo hypernet guardado en {model_path}")

        # 2) Guardar el estado de UCB/TS y buffers
        state = {
            "counts":        self.counts,
            "values":        self.values,
            "total_counts":  self.total_counts,
            "successes":     self.successes,
            "failures":      self.failures,
            # Convertir deque a lista para serializar
            "reward_history":      list(self.reward_history),
            "_offline_states":     [s.tolist() for s in self._offline_states],
            "_offline_idxs":       list(self._offline_idxs),
        }
        state_path = os.path.join(dst, "state.pkl")
        joblib.dump(state, state_path)
        logging.info(f"[META] Estado interno guardado en {state_path}")

    def load_model(self, path: str):
        """
        Carga el meta-modelo y restaura su estado interno desde la carpeta dada.
        """
        src = path or self.model_path
        if not os.path.isdir(src):
            raise FileNotFoundError(f"No existe el directorio de MetaSelector en {src}")

        # 1) Cargar modelo
        model_path = os.path.join(src, "hypernet.keras")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No existe el modelo hypernet en {model_path}")
        self.model = tf_load_model(model_path)
        logging.info(f"[META] Modelo hypernet cargado desde {model_path}")

        # 2) Restaurar estado
        state_path = os.path.join(src, "state.pkl")
        if not os.path.exists(state_path):
            raise FileNotFoundError(f"No existe el estado interno en {state_path}")
        state = joblib.load(state_path)

        self.counts        = state["counts"]
        self.values        = state["values"]
        self.total_counts  = state["total_counts"]
        self.successes     = state["successes"]
        self.failures      = state["failures"]

        # Restaurar deques
        self.reward_history  = deque(state["reward_history"], maxlen=self.window)
        self._offline_states = deque(
            [np.array(s, dtype=np.float32) for s in state["_offline_states"]],
            maxlen=self.window
        )
        self._offline_idxs   = deque(state["_offline_idxs"], maxlen=self.window)

        logging.info(f"[META] Estado interno restaurado desde {state_path}")

    # Por compatibilidad con helper y run_pbt.py:
    alias_save_model = save_model
    alias_load_model = load_model