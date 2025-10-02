# wplay/utils/logger.py

import logging
import os
from datetime import datetime

# Carpeta para logs
LOG_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Nombre de archivo con fecha
LOG_FILE = os.path.join(LOG_DIR, f"wplay_{datetime.now():%Y%m%d}.log")

# Configuración básica
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()  # también al stdout
    ]
)

# Logger por defecto
logger = logging.getLogger("wplay")
