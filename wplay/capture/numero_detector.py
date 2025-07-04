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
        # 1) Captura y guardado
        frame = self._capturar()
        self._guardar_imagen(frame, "numero_raw.png")

        # 2) Escala y conversión a gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        self._guardar_imagen(gray, "numero_upscaled.png")

        # 3) Binarización con Otsu
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self._guardar_imagen(bw, "numero_thresh.png")

        # 4) Morphology close para limpiar artefactos
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
        self._guardar_imagen(bw, "numero_morph.png")

        # 5) OCR estándar (modo línea)
        cfg7 = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(bw, config=cfg7).strip()
        if len(text) > 2:
            text = text[-2:]
        try:
            return int(text)
        except (ValueError, TypeError):
            # Si falla, aplicamos fallback específico para el cero
            pass

        # ----- Fallback para '0' -----
        # 6) Convertir a HSV y segmentar blancos sobre verde claro
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 0, 200], dtype=np.uint8)
        upper = np.array([180, 50, 255], dtype=np.uint8)
        mask_white = cv2.inRange(hsv, lower, upper)
        self._guardar_imagen(mask_white, "mask_white.png")

        # 7) Morfología para reforzar contorno
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask_white, cv2.MORPH_CLOSE, kern, iterations=2)
        mask = cv2.dilate(mask, kern, iterations=1)
        self._guardar_imagen(mask, "mask_refined.png")

        # 8) Extraer contorno principal y ROI
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        roi = mask[y:y+h, x:x+w]
        roi = cv2.copyMakeBorder(roi, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=0)
        self._guardar_imagen(roi, "roi_color.png")

        # 9) OCR en modo un solo carácter
        cfg10 = "--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789"
        text2 = pytesseract.image_to_string(roi, config=cfg10).strip()

        # 10) Nuevo fallback: si hay blob (pixeles blancos) y OCR falla, asumimos 0
        if not text2 and cv2.countNonZero(roi) > 0:
            return 0

        try:
            if len(text2) > 2:
                text2 = text2[-2:]
            return int(text2)
        except (ValueError, TypeError):
            return None
