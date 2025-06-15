# wplay/config.py

import os

# — Ruta de la base de datos SQLite —
BASE_DIR = os.path.dirname(__file__)
DB_PATH  = os.path.join(BASE_DIR, "database", "ruleta_stats.db")
DATA_DIR = os.path.join(BASE_DIR,  "wplay","data")
MODELS   = os.path.join(BASE_DIR, "models")

# — Configuración de Tesseract OCR —
TESSDATA_PREFIX = r"C:\Program Files\Tesseract-OCR\tessdata"
# templantes
TEMPLATES_DIR =  r"C:\Python\Wplay1.1\wplay\templates\region_images"
# — Chrome —
# Ruta al ejecutable de Chrome
CHROME_EXECUTABLE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# Directorio de datos de usuario (perfil) para Chrome
USER_DATA_DIR = r"C:\Users\faber\AppData\Local\Google\Chrome\User Data"
# Nombre del perfil de Chrome a usar
CHROME_PROFILE = "IA"
# URL objetivo a abrir
TARGET_URL = "https://wplay.co"
