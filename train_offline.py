# Dentro de main(), tras cargar credenciales y regiones…

# Prepara el agente híbrido DL
from wplay.strategy.rl_agent           import RLAgent
from wplay.strategy.strategy_manager_dl import StrategyManagerDL

dqn = RLAgent(state_dim=8, action_dim=6, model_path="models/dqn.h5")
dqn.load()
dl  = StrategyManagerDL("models/lstm.h5", dqn)

# Y pasa `dl` en lugar de tu StrategyManager clásico:
engine = BettingEngine(
    region_finder   = login,
    data_collector  = collector,
    strategy_manager= dl,            # << aquí
    stats_helper    = stats_helper,  # opcional si aún quieres ausencias
    db_manager      = db_manager,
    place_bet_fn    = login.apostar_opcion
    
)
engine.run()
