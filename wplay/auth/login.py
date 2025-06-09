# wplay/auth/login.py

import os
import time
import cv2
import numpy as np
import pyautogui
import pyperclip
import unicodedata
from wplay.config import CHROME_EXECUTABLE, USER_DATA_DIR, CHROME_PROFILE
from wplay.capture.chrome_handler import ChromeHandler
from glob import glob
from wplay.data.db_manager import DBManager
from wplay.strategy.manager import StrategyManager
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.capture.numero_detector import NumeroDetector
from wplay.data.data_processor import DataProcessor

pyautogui.FAILSAFE = False

def normalize_filename(name: str) -> str:
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')

def paste_text(text: str):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.2)

def human_click(x: int, y: int, hold_time: float = 0.05, move_duration: float = 0.1):
    """
    Trae la ventana de Chrome al frente y hace click en (x, y).
    """
    try:
        # Ajusta el título si tu ventana no se llama "Chrome"
        win = pyautogui.getWindowsWithTitle("Chrome")[0]
        if not win.isActive:
            win.activate()
            time.sleep(0.1)
    except Exception:
        pass  # si no encuentra la ventana, seguimos igualmente

    pyautogui.moveTo(x, y, duration=move_duration)
    pyautogui.mouseDown()
    time.sleep(hold_time)
    pyautogui.mouseUp()

class LoginAutomation:
    def __init__(
        self,
        creds: dict,
        regions: dict,
        db_path: str,
        simulate: bool = True
    ):
        # — credenciales y regiones —
        self.username = creds.get("username")
        self.password = creds.get("password")
        self.regions = regions

        # — modo simulación vs real —
        self.simulate = simulate

        # — instancias de soporte —
        self.db_manager       = DBManager(db_path)
        self.strategy_manager = StrategyManager(db_path=db_path)
        self.ruleta_detector  = RuletaDetector(delay=0.5, debug_folder="debug_ruleta")
        self.numero_detector  = NumeroDetector(debug_folder="debug_numeros")
    
    def open_chrome(self, url: str):
            """
            Crea un nuevo ChromeHandler con la configuración de config.py
            y abre la URL dada. Luego maximiza la ventana para asegurar
            que toda la página esté visible.
            """
            # 1) Abrir Chrome
            chrome = ChromeHandler(
                executable_path=CHROME_EXECUTABLE,
                user_data_dir=USER_DATA_DIR,
                profile=CHROME_PROFILE
            )
            chrome.open_chrome(url)

            # 2) Pequeña espera para que la ventana aparezca
            time.sleep(2)

            # 3) Maximizar la ventana (Windows: Win + Flecha arriba)
            try:
                pyautogui.hotkey("win", "up")
                time.sleep(0.5)
            except Exception as e:
                print(f"[LOGIN] No pudo maximizar ventana: {e!r}")

            # 4) Dejar unos segundos para que la página cargue completamente
            time.sleep(5)
    def find_all_regions(self, threshold: float = 0.8) -> dict:
        """
        Escanea la pantalla buscando todas las plantillas entrenadas.
        Devuelve un dict {nombre_region: (x,y,w,h)} y lo imprime en consola.
        """
        detected = {}
        screen_gray = cv2.cvtColor(
            np.array(pyautogui.screenshot()), cv2.COLOR_RGB2GRAY
        )
        tpl_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "templates", "region_images")
        )

        # Prioridad a 'clic'
        ordered = ["clic"] + [r for r in self.regions if r != "clic"]
        for name in ordered:
            if name not in self.regions:
                continue
            norm = normalize_filename(name)
            for tpl_path in glob(f"{tpl_dir}/{norm}_*.png"):
                tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                if tpl is None:
                    continue
                res = cv2.matchTemplate(screen_gray, tpl, cv2.TM_CCOEFF_NORMED)
                _, maxv, _, maxloc = cv2.minMaxLoc(res)
                th = 0.92 if name == "clic" else threshold
                if maxv >= th:
                    x, y = maxloc
                    h, w = tpl.shape
                    detected[name] = (x, y, w, h)
                    break

        if detected:
            items = ", ".join(f"'{k}':{v}" for k, v in detected.items())
           # print(f"🔍 Detecciones: {{{items}}}")
        return detected

    def click_region(self, name: str) -> bool:
        """
        Hace clic en el centro de la región detectada para 'name'.
        """
        det = self.find_all_regions()
        if name not in det:
            print(f"⚠ No detecté región '{name}' para clic.")
            return False
        x, y, w, h = det[name]
        cx, cy = x + w//2, y + h//2
        human_click(cx, cy)
        return True

    def set_simulation(self, flag: bool):
        self.simulate = flag
        modo = "REAL" if not flag else "SIMULACIÓN"
        print(f">>> Modo de apuestas: {modo}")

    def login_or_continue(self, timeout: float = 60.0) -> bool:
        """
        Flujo de login basado enteramente en etiquetas.
        Guarda cada segundo debug/screen_latest.png.
        """
        os.makedirs("debug", exist_ok=True)
        start = time.time()
        last_capture = 0

        while time.time() - start < timeout:
            now = time.time()
            # Guardar screenshot cada segundo para debug
            if now - last_capture > 1:
                img = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
                cv2.imwrite("debug/screen_latest.png", img)
                last_capture = now

            det = self.find_all_regions()

            # 1) 'clic'
            if "clic" in det:
                self.click_region("clic")
                time.sleep(0.3)
                continue

            # 2) 'correo'
            if "correo" in det:
                self.click_region("correo")
                paste_text(self.username)
                continue

            # 3) 'contraseña'
            if "contraseña" in det:
                self.click_region("contraseña")
                paste_text(self.password)
                continue

            # 4) 'boton entrar'
            if "boton entrar" in det:
                self.click_region("boton entrar")
                time.sleep(1)
                continue
            
            # 6) 'speed auto roulette'
            if "speed auto roulette" in det:
                self.click_region("speed auto roulette")
                print("✅ Juego 'speed auto roulette' seleccionado.")
                return True


            # 5) 'buscar juego'
            if "buscar juego" in det:
                self.click_region("buscar juego")
                time.sleep(0.3)
                continue

            # 7) 'casino en vivo'
            if "casino en vivo" in det:
                self.click_region("casino en vivo")
                time.sleep(0.3)
                continue

            time.sleep(0.2)

        print("⏱ Timeout en login_or_continue.")
        return False


    def calcular_ganancia(self, numero: int, categoria: str, fichas: int) -> tuple[bool, float]:
    

        """
        Calcula color/paridad/rango y devuelve (ganó?, ganancia neta en dinero real).
        Usa self.strategy_manager.wager_value como valor de ficha.
        """
        rojos    = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        color    = "rojo"   if numero in rojos else "negro"
        paridad  = "par"    if (numero != 0 and numero % 2 == 0) else "impar"
        rango    = "1-18"   if 1 <= numero <= 18 else "19-36"
        win      = categoria in {color, paridad, rango}

        # valor por ficha según el escalonado actual
        ficha_val = self.strategy_manager.wager_value

        # ganancia neta: +fichas×valor si gana, –lo mismo si pierde
        net = ficha_val * fichas
        return win, ( net if win else -net )

    
    def monitor(self):
        """
        Modo monitoreo/apuestas basado en etiqueta 'apostar'.
        Selecciona la ficha 500 o 5000 antes de apostar en real.
        """
        COOLDOWN = 12.0
        apuesta_en_curso = False
        last_cat = None
        last_strat = None
        last_amt = 0
        vel_buffer = []
        data_proc = DataProcessor()
        last_time = 0.0

        print("Entrando en modo de monitoreo...")
        while True:
            det = self.find_all_regions()
            now = time.time()

            # Esperar etiqueta 'apostar' + cooldown
            if "apostar" not in det or (now - last_time) < COOLDOWN:
                time.sleep(0.3)
                continue

            # 1) Giro
            if "giro" in det:
                spin = self.ruleta_detector.detectar_giro(det.get("ruleta_coords"), data_proc)
                if spin:
                    vel, dir_ = spin[2], spin[3]
                    vel_buffer.append(vel)
                    print(f"Giro vel={vel:.1f}, dir={dir_}")

            # 2) Leer número
            numero = self.numero_detector.detectar_numero()
            if numero is None:
                continue

            # 3) Procesar ganancia anterior
            if apuesta_en_curso:
                win, gain = self.calcular_ganancia(numero, last_cat, last_amt)
                self.strategy_manager.update_q(last_strat, gain)
            else:
                win, gain = False, 0.0

            # 4) Elegir estrategia y cantidad de fichas
            strat = self.strategy_manager.choose()
            amt   = self.strategy_manager.bet_amount(strat, win)

            # 5) Guardar en BD
            prev = getattr(self, "saldo", 0.0)
            self.saldo = prev + gain
            avg_vel = sum(vel_buffer)/len(vel_buffer) if vel_buffer else 0.0
            registro = {
                "fecha_hora":     time.strftime("%Y-%m-%d %H:%M:%S"),
                "numero":         numero,
                "ganancia":       gain,
                "saldo_anterior": prev,
                "velocity":       avg_vel,
                "direction":      dir_,
                "strategy":       last_strat,
                "fichas":         last_amt,
                "saldo":          self.saldo,
                "opcion_apuesta": last_cat
            }
            self.db_manager.guardar_registro(registro)
            print(">>", registro)

            # 6) Apostar
            etiqueta = "[SIM]" if self.simulate else "[REAL]"

            if not self.simulate:
                # 6.1) Actualizamos wager_value y seleccionamos plantilla 500_1.png o 5000_1.png
                self.strategy_manager._update_wager_value()
                self.seleccionar_ficha(self.strategy_manager.wager_value)

            print(f"{etiqueta} Apostando {amt} ficha(s) a '{strat}'")
            # 6.2) Hacer click en la mesa la cantidad de veces indicada
            self.apostar_opcion(strat, amt)

            # 7) Reset
            apuesta_en_curso = True
            last_cat     = strat
            last_strat   = strat
            last_amt     = amt
            vel_buffer.clear()
            last_time    = now



    def apostar_opcion(self, categoria: str, n_fichas: int):
        """
        Hace clic repetidamente en la sección de la mesa correspondiente.
        """
        coords_map = {
            "rojo":   (952, 894, 61, 21),
            "negro":  (1036, 897, 56, 17),
            "1-18":   (811, 895, 43, 19),
            "19-36":  (1188, 897, 46, 16),
            "par":    (880, 896, 45, 18),
            "impar":  (1107,896, 57, 19),
        }
        if categoria not in coords_map:
            print(f"⚠ Opción desconocida: {categoria}")
            return
        x, y, w, h = coords_map[categoria]
        cx, cy = x + w//2, y + h//2

        if self.simulate:
            print(f"[SIM] Apostar {n_fichas} ficha(s) a {categoria}")
        else:
            for _ in range(n_fichas):
                human_click(cx, cy)
                time.sleep(0.2)

    def seleccionar_ficha(self, amt: int):
        """
        Selecciona la ficha correcta:
         - si amt >= 5_000 → clic en plantilla '5000_1.png' (región '5000')
         - sino → clic en plantilla '500_1.png' (región '500')
        """
        # Determinamos nombre de región según amt
        if amt >= 5000:
            name = "5000"
        else:
            name = "500"

        det = self.find_all_regions()
        if name not in det:
            print(f"⚠ No detecté región '{name}' para seleccionar ficha.")
            return False

        x, y, w, h = det[name]
        cx, cy = x + w//2, y + h//2
        human_click(cx, cy)
        time.sleep(0.2)
        return True
