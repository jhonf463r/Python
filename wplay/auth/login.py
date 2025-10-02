 # wplay/auth/login.py


import os
import time
import cv2
import numpy as np
import pyautogui
import pyperclip
import unicodedata
import math      
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
    # —→ Nuevo: caché de coords dinámicas exitosas
        self._last_coords = {}  # e.g. {'correo': (cx, cy), …}
        self._max_deviation = 50  
        # — modo simulación vs real —
        self.simulate = simulate

        # — instancias de soporte —
        self.db_manager       = DBManager(db_path)
        self.strategy_manager = StrategyManager(db_path=db_path)
        self.ruleta_detector  = RuletaDetector(delay=0.5, debug_folder="debug_ruleta")
        self.numero_detector  = NumeroDetector(debug_folder="debug_numeros")
        
    
    def open_chrome(self, url: str):
        # 1) Abrir Chrome (sin intentar pasarle flags extras)
        chrome = ChromeHandler(
            executable_path=CHROME_EXECUTABLE,
            user_data_dir=USER_DATA_DIR,
            profile=CHROME_PROFILE
        )
        chrome.open_chrome(url)

        # 2) Pequeña espera para que aparezca la ventana
        time.sleep(2)

        # 3) Forzar foco y maximizar con PyAutoGUI
        try:
            wins = pyautogui.getWindowsWithTitle("Chrome")
            if wins:
                win = wins[0]
                win.activate()
                time.sleep(0.2)
                win.maximize()
                time.sleep(0.5)
            else:
                # si no encuentra ventana por “Chrome”, pruebo con cualquier
                all_wins = pyautogui.getAllWindows()
                if all_wins:
                    w = all_wins[0]
                    w.activate(); time.sleep(0.2); w.maximize()
        except Exception as e:
            print(f"[LOGIN] No pudo maximizar ventana: {e!r}")

        # 4) Esperar a que la página cargue bien
        time.sleep(5)


   
    def find_all_regions(self, thresholds: dict[str, float] = None) -> dict:
        """
        thresholds: dict opcional con umbrales por etiqueta, e.g. {'apostar':0.60}
        """
        import cv2, numpy as np, pyautogui, os
        from glob import glob

        if thresholds is None:
            thresholds = {}
        default_th = 0.80
        detected = {}

        # 1) ROI estática de ruleta
        roi_list = self.regions.get("ruleta", [])
        if roi_list:
            r = roi_list[0]
            detected["ruleta_coords"] = (r["x"], r["y"], r["w"], r["h"])

        # 2) Captura pantalla gris
        screen = np.array(pyautogui.screenshot())
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

        # 3) Plantillas en disco
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "region_images")

        # 4) Buscar mejor match por nombre
        for name in ["clic"] + [n for n in self.regions if n not in ("clic", "ruleta")]:
            norm = normalize_filename(name)
            best_val = 0.0
            best_info = None

            for tpl_path in glob(f"{tpl_dir}/{norm}_*.png"):
                tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                if tpl is None:
                    continue
                res = cv2.matchTemplate(screen_gray, tpl, cv2.TM_CCOEFF_NORMED)
                _, maxv, _, maxloc = cv2.minMaxLoc(res)
                if maxv > best_val:
                    best_val = maxv
                    x, y = maxloc
                    h, w = tpl.shape
                    best_info = (x, y, w, h, os.path.basename(tpl_path), maxv)

            th = 0.92 if name == "clic" else thresholds.get(name, default_th)
            if best_info and best_info[-1] >= th:
                detected[name] = best_info

        return detected


    def click_region(self, name: str) -> bool:
        """
        Clic en orden de prioridad:
          1) coords cacheadas de detección dinámica (si válidas)
          2) template matching dinámico (y actualizar caché)
          3) si falla todo, no hace clic y avisa
        """
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "region_images")
        default_th = 0.80
        th = 0.92 if name == "clic" else default_th

        # 1) Intento con coords cacheadas (validar antes)
        if name in self._last_coords:
            cx, cy, tpl_filename = self._last_coords[name]
            try:
                # Captura pantallazo gris
                screen = np.array(pyautogui.screenshot())
                screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

                # Cargo plantilla usada originalmente
                tpl_path = os.path.join(tpl_dir, tpl_filename)
                tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                h, w = tpl.shape

                # Extraigo región alrededor de las coords cacheadas
                x0 = max(cx - w//2, 0)
                y0 = max(cy - h//2, 0)
                crop = screen_gray[y0:y0+h, x0:x0+w]

                res = cv2.matchTemplate(crop, tpl, cv2.TM_CCOEFF_NORMED)
                _, maxv, _, _ = cv2.minMaxLoc(res)

                if maxv >= th:
                    # Cache válida: clic en coords guardadas
                    print(f"[DEBUG-click] etiqueta='{name}' usando coords cacheadas → ({cx},{cy}) (match={maxv:.2f})")
                    human_click(cx, cy)
                    return True
                else:
                    # Cache inválida: la plantilla ya no está ahí
                    print(f"[DEBUG-click] cache inválida para '{name}' (match={maxv:.2f} < {th}); descartando cache")
                    del self._last_coords[name]
            except Exception as e:
                # Si algo falla validando, descartamos cache y seguimos
                print(f"[DEBUG-click] error validando cache para '{name}': {e}; descartando cache")
                self._last_coords.pop(name, None)

        # 2) Template matching dinámico
        det = self.find_all_regions()
        info = det.get(name)
        if info:
            x, y, w, h, tplfname, match = info
            cx, cy = x + w//2, y + h//2

            # Cacheo la nueva posición junto con el nombre de plantilla
            self._last_coords[name] = (cx, cy, tplfname)
            print(f"[DEBUG-click] etiqueta='{name}' plantilla='{tplfname}' match={match:.2f} → ({cx},{cy}) [cacheada]")
            human_click(cx, cy)
            return True

        # 3) Fallback: no encontrado
        print(f"⚠ No pude encontrar región '{name}' (dinámico); clic omitido.")
        return False

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
        Monitoreo/apuestas con flujo correcto:
        - Detecta 'apostar'
        - Lee número
        - Calcula ganancia anterior
        - Registra TODO
        - Apuesta y muestra TODO
        """
        COOLDOWN = 10.0
        last_time = 0.0
        apuesta_en_curso = False
        last_cat = last_strat = None
        last_amt = 0
        self.saldo = 0.0

        print("✅ Modo monitoreo/apuestas activo. Ctrl+C para salir.")

        while True:
            det = self.find_all_regions()
            now = time.time()

            if "apostar" not in det or (now - last_time) < COOLDOWN:
                time.sleep(0.2)
                continue

            last_time = now

            # 1) OCR número
            numero, jugadores = self.numero_detector.detectar_numero()
            if numero is None:
                continue

            print(f"OCR número (raw): '{numero}'")

            # 2) Procesar resultado previo
            if apuesta_en_curso:
                win, gain = self.calcular_ganancia(numero, last_cat, last_amt)
                print(f"[DEBUG] Resultado previo: win={win} gain={gain}")
                self.strategy_manager.update_q(last_strat, gain)
            else:
                win, gain = False, 0.0
                print(f"[DEBUG] Resultado previo: win=False, gain=0")

            # 3) Calcular nueva apuesta
            strat = self.strategy_manager.choose()
            amt = self.strategy_manager.bet_amount(strat, win)

            # 4) Guardar registro COMPLETO
            saldo_prev = self.saldo
            self.saldo = saldo_prev + gain
            registro = {
                "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "numero": numero,
                "jugadores_presentes": jugadores,
                "velocity": 0.0,   # pon tu cálculo real aquí si quieres
                "direction": "",   # idem
                "numero_hist": [],
                "ganancia": gain,
                "saldo_anterior": saldo_prev,
                "strategy": strat,
                "fichas": amt,
                "saldo": self.saldo,
                "opcion_apuesta": strat
            }
            self.db_manager.guardar_registro(registro)
            print(f">> Registro guardado: {registro}")

            # 5) Apuesta (simulada o real)
            etiqueta = "[SIM]" if self.simulate else "[REAL]"
            print(f"{etiqueta} Apostando {amt * self.strategy_manager.wager_value} ({amt}) ficha(s) a '{strat}'")

            apuesta_en_curso = True
            last_cat = strat
            last_strat = strat
            last_amt = amt


    def apostar_opcion(self, categoria: str, total_amount: int):
        """
        Ejecuta los clics reales sobre la mesa para apostar 'total_amount' en 'categoria'.
        Calcula el valor de ficha (500 o 5000) y repite human_click por cada ficha.
        """
        coords_map = {
            "rojo":   (952, 894, 61, 21),
            "negro":  (1036, 897, 56, 17),
            "1-18":   (811, 895, 43, 19),
            "19-36":  (1188, 897, 46, 16),
            "par":    (880, 896, 45, 18),
            "impar":  (1107, 896, 57, 19),
        }
        if categoria not in coords_map:
            print(f"⚠ Opción desconocida: {categoria}")
            return

        # Determinar valor de ficha y cantidad de fichas
        chip_value = 5000 if total_amount % 5000 == 0 else 500
        n_fichas = total_amount // chip_value

        x, y, w, h = coords_map[categoria]
        cx, cy = x + w // 2, y + h // 2

        # Seleccionar ficha correspondiente
        self.seleccionar_ficha(chip_value)

        # Ejecutar n_fichas clics reales
        for i in range(n_fichas):
            human_click(cx, cy)
            time.sleep(0.2)  # pequeña pausa entre clics
       # print(f"[REAL] Ejecutados {n_fichas} clic(s) de valor {chip_value} en '{categoria}'")
    def seleccionar_ficha(self, amt: int) -> bool:
            """
            Selecciona la ficha correcta (500 o 5000) buscando la mejor coincidencia
            en varias escalas. Devuelve True si se hizo “clic” simuladamente.
            """
            name = "5000" if amt >= 5000 else "500"

            if name not in self.regions:
                print(f"⚠️ self.regions no contiene la clave '{name}'. "
                    f"Agrega '5000' al dict de regiones.")
                return False

            tpl_dir = os.path.join(
                os.path.dirname(__file__),
                "..", "templates", "region_images"
            )
            tpl_paths = glob(f"{tpl_dir}/{name}_*.png")
            if not tpl_paths:
                print(f"⚠️ No encontré archivos {name}_*.png en {tpl_dir}")
                return False

            screen = cv2.cvtColor(
                np.array(pyautogui.screenshot()),
                cv2.COLOR_RGB2GRAY
            )

            best = {"val": 0.0, "loc": None, "w": 0, "h": 0, "tpl": None, "scale": 1.0}
            for tpl_path in tpl_paths:
                tpl_orig = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                if tpl_orig is None:
                    continue
                h0, w0 = tpl_orig.shape

                for scale in np.linspace(0.7, 1.3, 13):
                    w, h = int(w0 * scale), int(h0 * scale)
                    if w < 10 or h < 10:
                        continue
                    tpl = cv2.resize(tpl_orig, (w, h), interpolation=cv2.INTER_AREA)
                    res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
                    _, maxv, _, maxloc = cv2.minMaxLoc(res)
                    if maxv > best["val"]:
                        best.update({
                            "val": maxv,
                            "loc": maxloc,
                            "w": w,
                            "h": h,
                            "tpl": tpl_path,
                            "scale": scale
                        })

            umbral = 0.8
            if best["val"] >= umbral:
                x, y = best["loc"]
                cx = x + best["w"] // 2
                cy = y + best["h"] // 2

                # depuración de ficha
                print(f"[DEBUG-ficha] etiqueta='{name}' "
                    f"plantilla='{os.path.basename(best['tpl'])}' "
                    f"scale={best['scale']:.2f} match={best['val']:.2f} → coords=({cx},{cy})")

                human_click(cx, cy)
                time.sleep(0.2)
                return True

            print(f"⚠ No detecté ficha '{name}' (mejor match={best['val']:.2f})")
            return False
