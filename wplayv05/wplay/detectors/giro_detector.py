import os
import glob
import cv2

class GiroDetector:
    """
    Detector de giro de ruleta basado en plantillas múltiples.

    Parámetros:
    - pattern (str): Ruta glob a las plantillas, por ejemplo:
        os.path.join(TEMPLATES_DIR, 'giro_*.png')
    - threshold (float): Umbral de similitud (0 < threshold < 1).
    """
    def __init__(self, pattern, threshold=0.8):
        # Resolución de patrón de plantillas
        # pattern puede ser un glob (giro_*.png) o ruta simple
        self.pattern = pattern
        self.threshold = threshold

        # Carga todas las plantillas que cumplan el patrón
        if '*' in pattern or '?' in pattern or '[' in pattern:
            self.template_paths = glob.glob(pattern)
        else:
            # Ruta directa a un archivo
            self.template_paths = [pattern]

        if not self.template_paths:
            raise FileNotFoundError(f"No se encontraron plantillas con patrón: {pattern}")

        # Pre-carga de imágenes de plantilla en escala de grises
        self.templates = []
        for tpl_path in self.template_paths:
            img = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"La plantilla no se pudo leer: {tpl_path}")
            self.templates.append(img)

    def detect(self, frame_gray):
        """
        Busca en frame_gray la plantilla con mayor similitud.

        Args:
            frame_gray (ndarray): Imagen de entrada en escala de grises.

        Returns:
            tuple: (max_val, max_loc, template_size)
                - max_val (float): Valor máximo de correlación.
                - max_loc (tuple): Coordenadas (x, y) de la mejor coincidencia.
                - template_size (tuple): (w, h) del template coincidente.
        """
        best_val = 0
        best_loc = None
        best_size = None

        # Iterar sobre todas las plantillas
        for tpl in self.templates:
            res = cv2.matchTemplate(frame_gray, tpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_size = (tpl.shape[1], tpl.shape[0])  # w, h

        if best_val >= self.threshold:
            return best_val, best_loc, best_size
        return None  # No match suficientemente fuerte
