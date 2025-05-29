import cv2
import numpy as np
import pyautogui
import pytesseract
import os
from typing import Optional

class NumeroDetector:
    def __init__(self, debug_folder="debug_numeros", coords=(1323, 899, 26, 27)):
        """
        :param debug_folder: Carpeta para guardar capturas y depurar la lectura.
        :param coords: Región (x, y, w, h) donde aparece el número.
        """
        self.debug_folder = debug_folder
        os.makedirs(self.debug_folder, exist_ok=True)
        self.coords = coords

    def _guardar_imagen(self, img, name):
        path = os.path.join(self.debug_folder, name)
        cv2.imwrite(path, img)

    def _capturar(self) -> np.ndarray:
        x, y, w, h = self.coords
        shot = pyautogui.screenshot(region=(x, y, w, h))
        return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    def detectar_numero(self) -> Optional[int]:
        frame = self._capturar()
        self._guardar_imagen(frame, "numero_raw.png")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        self._guardar_imagen(gray, "numero_upscaled.png")

        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self._guardar_imagen(bw, "numero_thresh.png")

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
        self._guardar_imagen(bw, "numero_morph.png")

        cfg = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(bw, config=cfg).strip()
        print(f"OCR número (raw): '{text}'")

        if len(text) > 2:
            text = text[-2:]
        try:
            return int(text)
        except ValueError:
            return None
