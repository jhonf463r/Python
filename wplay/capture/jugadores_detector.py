import cv2
import numpy as np
import pyautogui
import pytesseract
import os
from typing import Optional

class JugadoresDetector:
    def __init__(self, debug_folder="debug_jugadores", coords=(268, 83, 27, 20)):
        """
        :param debug_folder: Carpeta para guardar capturas y depurar la lectura.
        :param coords: Región (x, y, w, h) donde aparece el número de jugadores.
        """
        self.debug_folder = debug_folder
        os.makedirs(self.debug_folder, exist_ok=True)
        self.coords = coords

    def _guardar_imagen(self, img, name):
        path = os.path.join(self.debug_folder, name)
        cv2.imwrite(path, img)

    def detectar_jugadores(self) -> Optional[int]:
        x, y, w, h = self.coords
        pad = 5
        x0, y0 = max(0, x - pad), max(0, y - pad)
        shot = pyautogui.screenshot(region=(x0, y0, w + 2 * pad, h + 2 * pad))
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
        print(f"OCR jugadores (raw): '{txt}'")

        try:
            return int(txt)
        except ValueError:
            return None
