import time
from wplay.auth.login import LoginAutomation
from wplay.detectors.region_finder import RegionFinder
from wplay.detectors.giro_detector import GiroDetector
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.detectors.numero_detector import NumeroDetector
from wplay.controllers.bet_controller import BetController
from wplay.controllers.spin_controller import SpinController
from wplay.detectors.data_collector import DataCollector
# from wplay.strategy.your_strategy import YourStrategy

class MainEngine:
    def __init__(self, creds, simulate=False):
        # 1) Login
        self.login = LoginAutomation(creds, RegionFinder([
            # aquí instancia los detectores de pantalla
            GiroDetector(...),
            # ...otros detectores para login también...
        ]), simulate=simulate)

        # 2) Región/detección
        self.rf = RegionFinder([
            GiroDetector(...),
            RuletaDetector(...),
            NumeroDetector(...),
            # etc.
        ])

        # 3) Controladores
        table_map = {...}  # tu dict categoría→coords
        self.bet_ctrl = BetController(table_map, human_click)
        self.data_col = DataCollector(RuletaDetector(...), NumeroDetector(...))
        self.spin_ctrl = SpinController(self.rf, self.data_col)
        # 4) Estrategia
        # self.strategy = YourStrategy(...)

    def run(self):
        # Login hasta la ruleta
        if not self.login.login_or_continue():
            return
        # Bucle principal
        while True:
            # 1) Decidir si apostar
            # if self.strategy.should_bet():
            #     amt = self.strategy.next_bet_amount()
            #     if self.bet_ctrl.place_bet(self.strategy.category, amt):
            #         self.spin_ctrl.notify_bet_placed()
            #
            # 2) Actualizar spin
            self.spin_ctrl.update()
            #
            # 3) Al completar spin, procesar stats
            if self.data_col.spin_complete():
                stats = self.data_col.get_spin_stats()
                print("Resultado del giro:", stats)
                # self.strategy.update(stats)
            time.sleep(0.01)
