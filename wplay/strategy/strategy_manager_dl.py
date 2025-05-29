import numpy as np 
from tensorflow.keras.models import load_model
from wplay.strategy.fibonacci import FibonacciStrategy
from wplay.strategy.dalembert import DalembertStrategy
from wplay.strategy.meta_strategy_selector import MetaStrategySelector

class StrategyManagerDL:
    """
    Combina un modelo LSTM y un agente RL para decidir categoría y monto.
    Fija estrategias Fibonacci/D’Alembert hasta completar su ciclo antes de reelegir.
    """
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36"]

    def __init__(
        self,
        lstm_path: str,
        rl_agent,
        bank: float = 1000.0,
        window_lstm: int = 50,
        window_rl: int = 10,
        max_bet_dqn: int = 8,
        max_bet_ppo: int = 10,
    ):
        # Carga de modelo y configuraciones
        self.lstm = load_model(lstm_path)
        _, self.timesteps, self.feature_dim = self.lstm.input_shape
        self.n_categories = self.lstm.output_shape[-1]
        if self.n_categories != len(self.CATEGORIES):
            self.CATEGORIES = self.CATEGORIES[:self.n_categories]

        # Agentes
        self.rl_agent = rl_agent
        self.meta_agent = MetaStrategySelector(
            state_dim=window_rl + 2,
            strategy_list=["dqn", "ppo", "fibonacci", "dalembert"],
            model_path="wplay/models/meta_strategy_selector.h5",
            window=100
        )

        # Parámetros de bankroll y límites
        self.bank = bank
        self.max_bet_dqn = max_bet_dqn       # fichas absolutas
        self.max_bet_ppo = max_bet_ppo       # fichas absolutas

        # Objetos de estrategia
        self.fibo = FibonacciStrategy()
        self.dalemb = DalembertStrategy()

        # Historial y estados
        self.window_lstm = window_lstm
        self.window_rl = window_rl
        self.hist_cat = []
        self.hist_nums = []
        self.last_win = False
        self._lstm_state = None
        self._rl_state = None

        # **Nuevos atributos**
        self.active_strat = None      # estrategia fija hasta completar la racha
        self.category_idx = None      # índice rotatorio de categoría

    def _num_to_category(self, numero: int) -> str:
        if numero == 0:
            return "0"
        rojo = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        return "rojo" if numero in rojo else "negro"

    def add_record(self, record: dict):
        # Preparar inputs para LSTM y RL (igual que antes)
        num = int(record["numero"])
        cat = self._num_to_category(num)
        self.hist_cat.append(cat)
        if len(self.hist_cat) > self.window_lstm:
            self.hist_cat.pop(0)
        self.hist_nums.append(num)
        if len(self.hist_nums) > self.window_rl:
            self.hist_nums.pop(0)

        self.last_win = record["ganancia"] > 0.0

        # Features para LSTM
        absences = []
        for c in self.CATEGORIES:
            if c in self.hist_cat:
                last_i = len(self.hist_cat)-1 - self.hist_cat[::-1].index(c)
                absences.append((len(self.hist_cat)-1) - last_i)
            else:
                absences.append(self.window_lstm)
        feats = absences + [
            float(record["velocity"]),
            1.0 if record["direction"] == "horario" else 0.0,
            float(record["jugadores_presentes"])
        ]
        feats = (feats + [0.0]*(self.feature_dim-len(feats)))[:self.feature_dim]
        self._lstm_state = np.array(feats).reshape(1, self.timesteps, self.feature_dim)

        # Estado RL
        norm_nums = [n/36.0 for n in self.hist_nums]
        phys = [
            float(record["velocity"])/100.0,
            1.0 if record["direction"]=="horario" else 0.0,
            float(record["jugadores_presentes"])/50.0
        ]
        self._rl_state = np.array(norm_nums+phys).reshape(1, -1)

    def choose_bet(self) -> dict:
        # 1) Predicción LSTM
        probs = self.lstm.predict(self._lstm_state, verbose=0)[0]
        pred_idx = int(np.argmax(probs))
        pred_idx = max(0, min(pred_idx, len(self.CATEGORIES)-1))

        # Si no hay ciclo en curso, inicializamos category_idx
        if self.active_strat is None:
            self.category_idx = pred_idx

        categoria = self.CATEGORIES[self.category_idx]
        confianza = float(probs[pred_idx])

        # 2) Meta-estrategia (solo si no hay ciclo clásico)
        if self.active_strat is None:
            strat = self.meta_agent.select_strategy(
                np.concatenate([self._rl_state.flatten(), [confianza, self.bank]])
            )
            if strat in ("fibonacci","dalembert"):
                self.active_strat = strat
        else:
            strat = self.active_strat

        # 3) Cálculo de monto según estrategia
        if strat == "dqn":
            action = self.rl_agent.select_action(self._rl_state.flatten())
            desired = int(self.bank * (2**action) / 100)
            monto = min(desired, self.max_bet_dqn)

        elif strat == "ppo":
            frac = self.rl_agent.select_action(self._rl_state.flatten())
            monto = min(int(frac * self.bank), self.max_bet_ppo)

        elif strat == "fibonacci":
            monto = self.fibo.next_bet(self.last_win)

        elif strat == "dalembert":
            monto = self.dalemb.next_bet(self.last_win)

        else:
            monto = 1

        monto = max(1, min(monto, int(self.bank)))
        self.bank -= monto

        return {
            "categoria_idx": self.category_idx,
            "categoria": categoria,
            "monto": monto,
            "strategy": strat
        }

    def choose(self):
        bet = self.choose_bet()
        idx = bet["categoria_idx"]
        categoria = bet["categoria"]
        monto = bet["monto"]
        strat = bet["strategy"]

        # Si es ciclo clásico y termina (win o max_step)
        if strat in ("fibonacci","dalembert") and self.active_strat == strat:
            strat_obj = self.fibo if strat=="fibonacci" else self.dalemb
            max_reached = hasattr(strat_obj, "max_step") and monto >= strat_obj.max_step
            if self.last_win or max_reached:
                strat_obj.reset()
                self.active_strat = None  # libera para meta-selector

        # Rotar categoría para la siguiente apuesta
        self.category_idx = (self.category_idx + 1) % len(self.CATEGORIES)

        return categoria, monto, strat
