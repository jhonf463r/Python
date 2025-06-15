# wplay/auth/login.py

import os
import time
import cv2
import numpy as np
import pyautogui
import pyperclip

from typing import Dict, Any, Optional, Callable
from glob import glob

from wplay.config import (
    CHROME_EXECUTABLE, USER_DATA_DIR, CHROME_PROFILE,
    TARGET_URL, DB_PATH, TEMPLATES_DIR
)
from wplay.capture.chrome_handler import ChromeHandler
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.detectors.numero_detector import NumeroDetector
from wplay.data.db_manager import DBManager
from wplay.strategy.manager import StrategyManager
from wplay.utils.helpers import human_click


class LoginAutomation:
    """
    Automatiza el login y la inicialización de DB + estrategia.
    Firma:
      __init__(creds: dict,
               region_finder,
               simulate: bool = True,
               human_click_fn: Optional[Callable] = None)
    """

    def __init__(
        self,
        creds: Dict[str, Any],
        region_finder,
        simulate: bool = True,
        human_click_fn: Optional[Callable[[int, int], None]] = None
    ):
        """
        Args:
          creds: diccionario con credenciales. Puede usar claves:
                 - 'correo' y 'contraseña' (español), o
                 - 'username' y 'password' (inglés).
          region_finder: instancia de RegionFinder con lista de detectores.
          simulate: si True, no hace clicks reales (solo prints).
          human_click_fn: función opcional que recibe (x, y) para hacer click.
        """
        self.simulate       = simulate
        self.human_click_fn = human_click_fn
        self.rf             = region_finder  # ahora accederemos a find_all()

        # Normalizar credenciales:
        email = creds.get("correo") or creds.get("username")
        pwd   = creds.get("contraseña") or creds.get("password")
        if not email or not pwd:
            raise KeyError("Credenciales inválidas: requieren 'correo'/'username' y 'contraseña'/'password'")
        self.email    = email
        self.password = pwd

        # Inicializamos ChromeHandler (no abrimos URL todavía)
        self.chrome = ChromeHandler(
            executable_path=CHROME_EXECUTABLE,
            user_data_dir=USER_DATA_DIR,
            profile=CHROME_PROFILE
        )
        self.driver = None

        # Detectores para validaciones posteriores (firma unificada)
        self.ruleta_detector = RuletaDetector(
            pattern=os.path.join(TEMPLATES_DIR, "ruleta_*.png"),
            threshold=0.9
        )
        self.numero_detector = NumeroDetector(
            pattern=os.path.join(TEMPLATES_DIR, "numero_*.png"),
            threshold=0.9
        )

        # DB + estrategia (se usan tras login)
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.db_manager      = DBManager(db_path=DB_PATH)
        self.strategy_manager = None  # se cargará tras login

    def _get_region(self, name: str):
        """
        Usa RegionFinder.find_all() y devuelve coords si existe.
        """
        regions = self.rf.find_all()
        coords = regions.get(name)
        if coords is None:
            raise RuntimeError(f"Región '{name}' no encontrada en {list(regions)}")
        return coords

    def _click_region(self, region_name: str):
        """Busca coords con RegionFinder y hace click o simula."""
        x, y, w, h = self._get_region(region_name)
        cx, cy = x + w // 2, y + h // 2

        if self.human_click_fn:
            self.human_click_fn(cx, cy)
        elif self.simulate:
            print(f"[SIM] click en '{region_name}' → ({cx},{cy})")
        else:
            human_click((cx, cy))

    def _type_region(self, region_name: str, text: str):
        """Click en campo, copia texto al portapapeles y pega."""
        self._click_region(region_name)
        time.sleep(0.3)
        if self.simulate:
            print(f"[SIM] escribir '{text}' en '{region_name}'")
        else:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)

    def open_site(self, url: str):
        """Lanza Chrome y abre la URL dada (una sola vez)."""
        if getattr(self, "_site_opened", False):
            return
        self.chrome.open_chrome(url)
        self.driver = getattr(self.chrome, "driver", None)
        print("Esperando a que la página se cargue…")
        time.sleep(8)
        self._site_opened = True

    def login_or_continue(self) -> bool:
        """
        Flujo de login:
          1) open_site(TARGET_URL)
          2) click+type en correo/username
          3) click+type en contraseña/password
          4) click en botón entrar
          5) validar detección de ruleta y número
          6) inicializar StrategyManager
        Devuelve True si OK.
        """
        try:
            # 1) Abrimos la web (solo la primera vez)
            self.open_site(TARGET_URL)

            # 2) Campo correo/username
            self._type_region("correo", self.email)
            time.sleep(1)

            # 3) Campo contraseña/password
            self._type_region("contraseña", self.password)
            time.sleep(1)

            # 4) Botón entrar
            self._click_region("boton entrar")
            time.sleep(5)

            # 5) Validar login: detección de ruleta y número
            x, y, w, h = self._get_region("ruleta")
            img_ruleta = self.chrome.capture_region((x,y,w,h))
            gray_ruleta = cv2.cvtColor(img_ruleta, cv2.COLOR_BGR2GRAY)
            ruleta_ok = self.ruleta_detector.detect(gray_ruleta) is not None

            x2, y2, w2, h2 = self._get_region("numero")
            img_num = self.chrome.capture_region((x2,y2,w2,h2))
            gray_num = cv2.cvtColor(img_num, cv2.COLOR_BGR2GRAY)
            numero_ok = self.numero_detector.detect(gray_num) is not None

            if not (ruleta_ok and numero_ok):
                print("⚠ Login fallido: no detecté ruleta y/o número.")
                return False

            # 6) Cargar estrategia offline
            self.strategy_manager = StrategyManager(db_manager=self.db_manager)
            self.strategy_manager.load_from_db()

            print("✅ Login exitoso y estrategia cargada.")
            return True

        except Exception as e:
            print(f"[LoginAutomation] Error durante login: {e}")
            return False
