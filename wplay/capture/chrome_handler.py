# wplay/capture/chrome_handler.py

import subprocess
import time
import os

from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.capture.numero_detector import NumeroDetector
from wplay.capture.jugadores_detector import JugadoresDetector
from wplay.data.data_processor import DataProcessor

class ChromeHandler:
    """
    Encapsula la apertura de Chrome y expone
    los detectores y procesadores necesarios para DataCollector.
    """
    def __init__(self, executable_path: str, user_data_dir: str, profile: str):
        self.executable_path = executable_path
        self.user_data_dir   = user_data_dir
        self.profile         = profile

        # Detectores que usaremos durante toda la sesión
        self.ruleta_detector   = RuletaDetector()
        self.numero_detector   = NumeroDetector()
        self.jugadores_detector = JugadoresDetector()

        # Procesador de datos para velocidades y ángulos
        self.data_processor    = DataProcessor(
            max_angle_jump=80.0,
            max_velocity=500.0
        )

    def open_chrome(self, url: str):
        """
        Lanza una instancia de Google Chrome con el perfil y URL deseada.
        """
        if not os.path.isfile(self.executable_path):
            raise FileNotFoundError(f"Chrome no encontrado en: {self.executable_path}")

        cmd = [
            self.executable_path,
            f"--user-data-dir={self.user_data_dir}",
            f"--profile-directory={self.profile}",
            "--start-maximized",
            "--disable-notifications",
            "--new-window",
            url
        ]

        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            raise RuntimeError(f"Error al lanzar Chrome: {e}")

        # Pequeña espera para que la ventana termine de cargar
        time.sleep(5)
