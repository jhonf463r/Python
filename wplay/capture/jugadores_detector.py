import cv2
import numpy as np
import pyautogui
import pytesseract
import os
import json
from typing import Optional, Tuple

class JugadoresDetector:
    def __init__(self, debug_folder="debug_jugadores", coords: Optional[Tuple[int, int, int, int]] = None, regions_json_path="regions.json"):
        """
        :param debug_folder: Carpeta para guardar capturas y depurar la lectura.
        :param coords: Región (x, y, w, h) donde aparece el número de jugadores. Si es None, se lee del JSON.
        :param regions_json_path: Ruta al archivo regions.json.
        """
        self.debug_folder = debug_folder
        os.makedirs(self.debug_folder, exist_ok=True)

        if coords is not None:
            self.coords = coords
        else:
            # Leer coordenadas de la región "jugadores" del JSON
            try:
                with open(regions_json_path, "r", encoding="utf-8") as f:
                    regions = json.load(f)
                # Toma la primera región de "jugadores"
                jug_coords = regions.get("jugadores", [])
                if jug_coords:
                    j = jug_coords[0]
                    self.coords = (j["x"], j["y"], j["w"], j["h"])
                  #  print(f"[DEBUG] Coordenadas de jugadores tomadas del JSON: {self.coords}")
                else:
                    raise ValueError("No se encontró la región 'jugadores' en el JSON.")
            except Exception as e:
                print(f"[ERROR] No se pudo leer regions.json: {e}")
                # Usa valores por defecto si falla
                self.coords = (268, 83, 27, 20)
             #   print(f"[DEBUG] Usando coordenadas por defecto: {self.coords}")

      #  print(f"[DEBUG] Carpeta debug jugadores: {os.path.abspath(self.debug_folder)}")

    def _guardar_imagen(self, img, name):
        path = os.path.join(self.debug_folder, name)
       # print(f"[DEBUG] Guardando imagen en: {path}")
        cv2.imwrite(path, img)

    def detectar_jugadores(self) -> Optional[int]:
        print("[DEBUG] Ejecutando detectar_jugadores")
        x, y, w, h = self.coords
        pad = 5
        x0, y0 = max(0, x - pad), max(0, y - pad)
        #print(f"[DEBUG] Capturando región: x={x0}, y={y0}, w={w + 2 * pad}, h={h + 2 * pad}")
        try:
            shot = pyautogui.screenshot(region=(x0, y0, w + 2 * pad, h + 2 * pad))
        except Exception as e:
            print(f"[ERROR] Error al capturar pantalla: {e}")
            return None
        img = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
        self._guardar_imagen(img, "jugadores_raw.png")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        self._guardar_imagen(gray, "jugadores_upscaled.png")

        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
        self._guardar_imagen(bw, "jugadores_morph.png")

        cfg = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
        txt = pytesseract.image_to_string(bw, config=cfg).strip()
      #  print(f"[DEBUG] OCR jugadores (raw): '{txt}'")


        try:
            valor = int(txt)
            print(f"[DEBUG] Valor detectado: {valor}")
            return valor
        except ValueError:
            print("[DEBUG] No se pudo convertir el texto a entero.")
            return None