import cv2
import os
import unicodedata
import numpy as np
import pyautogui
from glob import glob

from wplay.file_manager.file_manager import FileManager

# Default path under project for storing region images
DEFAULT_IMAGES_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates", "region_images")
)

def normalize_filename(name: str) -> str:
    """
    Convierte el nombre a una versión ASCII sin acentos ni caracteres especiales.
    Ej: "contraseña" → "contrasena".
    """
    return unicodedata.normalize('NFKD', name) \
                      .encode('ascii', 'ignore') \
                      .decode('ascii')

def get_next_filename(region_name: str, images_folder: str) -> str:
    """
    Genera un nombre incremental para la imagen de referencia de la región:
    <normalized>_1.png, <normalized>_2.png, etc.
    """
    normalized = normalize_filename(region_name)
    pattern = os.path.join(images_folder, f"{normalized}_*.png")
    existing = glob(pattern)
    if not existing:
        idx = 1
    else:
        nums = []
        for p in existing:
            name = os.path.basename(p)
            try:
                num = int(name.split("_")[-1].split(".")[0])
                nums.append(num)
            except ValueError:
                continue
        idx = max(nums) + 1 if nums else 1
    return os.path.join(images_folder, f"{normalized}_{idx}.png")

class RegionTrainer:
    """
    Permite capturar regiones de pantalla y guardarlas
    en JSON y en imágenes de referencia bajo templates/region_images.
    """

    def __init__(
        self,
        regions_file: str = "regions.json",
        images_folder: str = DEFAULT_IMAGES_FOLDER
    ):
        self.regions_file  = regions_file
        self.images_folder = os.path.abspath(images_folder)
        os.makedirs(self.images_folder, exist_ok=True)
        self.regions = FileManager.load_regions(self.regions_file)

    def capture_screen(self) -> np.ndarray:
        """
        Toma screenshot completo y lo pasa a BGR para OpenCV.
        """
        img = pyautogui.screenshot()
        arr = np.array(img)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def select_region(self, region_name: str) -> None:
        """
        Muestra pantalla, permite ROI, guarda coords en JSON y extrae imagen.
        """
        screen = self.capture_screen()
        print(f"[RegionTrainer] Selecciona región '{region_name}' y presiona ENTER.")
        x, y, w, h = cv2.selectROI(f"Región → {region_name}", screen, showCrosshair=True)
        cv2.destroyAllWindows()

        if w > 0 and h > 0:
            entry = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            # almacenar en JSON
            if region_name in self.regions:
                if not isinstance(self.regions[region_name], list):
                    self.regions[region_name] = [self.regions[region_name]]
                self.regions[region_name].append(entry)
            else:
                self.regions[region_name] = [entry]
            FileManager.save_regions(self.regions_file, self.regions)
            print(f"✔ Región '{region_name}' guardada en JSON.")

            # guardar imagen de la ROI
            filename = get_next_filename(region_name, self.images_folder)
            roi_img = screen[y:y+h, x:x+w]
            cv2.imwrite(filename, roi_img)
            print(f"✔ Imagen de plantilla guardada: {filename}")
        else:
            print(f"⚠ Selección inválida para '{region_name}'. Ningún cambio aplicado.")

    def train(self) -> None:
        """
        Bucle interactivo: solicita nombre y captura hasta 'salir'.
        """
        print("=== Entrenamiento de Regiones ===")
        while True:
            name = input("Nombre de región (o 'salir'): ").strip()
            if name.lower() == 'salir':
                break
            if not name:
                continue
            self.select_region(name)
        print("✅ Entrenamiento de regiones completado.")
