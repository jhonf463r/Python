#!/usr/bin/env python3
# wplay/__main__.py

import json
import time
import os
import sys

# — Ajustes de ruta para imports absolutos —
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from wplay.config import (
    DB_PATH,
    CHROME_EXECUTABLE,
    USER_DATA_DIR,
    CHROME_PROFILE,
    TARGET_URL,
    TEMPLATES_DIR
)
from wplay.auth.login import LoginAutomation
from wplay.trainer.region_trainer import RegionTrainer
from wplay.file_manager.file_manager import FileManager
from wplay.capture.chrome_handler import ChromeHandler
from wplay.detectors.region_finder import RegionFinder
from wplay.detectors.giro_detector import GiroDetector
from wplay.detectors.ruleta_detector import RuletaDetector
from wplay.detectors.numero_detector import NumeroDetector
from wplay.detectors.data_collector import DataCollector
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager
from wplay.controllers.main_engine import MainEngine
from wplay.utils.helpers import obtener_datos_actualizados, human_click


def main():
    print("1) Entrenar nuevas regiones")
    print("2) Iniciar sesión y comenzar monitoreo/apuestas")
    opcion = input("Seleccione opción (1/2): ").strip()

    if opcion == "1":
        RegionTrainer(
            regions_file=os.path.join(BASE_DIR, "regions.json"),
            images_folder=os.path.join(BASE_DIR, "region_images")
        ).train()
        print("✅ Regiones entrenadas. Se creó regions.json")
        return

    if opcion != "2":
        print("[ERROR] Opción inválida. Terminando.")
        return

    modo_real = input("¿Activar apuestas REALES? (s/N): ").lower().startswith("s")
    print(f">>> Modo de apuestas: {'REAL' if modo_real else 'SIMULACIÓN'}")

    # Asegurar carpeta de base de datos
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Pipeline offline (transformer + RL)
    print("🚀 Ejecutando pipeline offline (features y entrenamiento)…")
    try:
        strategy_manager = obtener_datos_actualizados()
    except Exception as e:
        print(f"[ERROR] Pipeline offline falló: {e}")
        return
    print("✅ Pipeline offline completado.")

    # 1) Abrir navegador con perfil
    chrome = ChromeHandler(
        executable_path=CHROME_EXECUTABLE,
        user_data_dir=USER_DATA_DIR,
        profile=CHROME_PROFILE
    )
    chrome.open_chrome(TARGET_URL)
    print("⏳ Esperando carga de página…")
    time.sleep(8)

    # 2) Cargar credenciales desde JSON
    creds_path = os.path.join(BASE_DIR, "credentials.json")
    try:
        with open(creds_path, "r", encoding="utf-8") as f:
            creds = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo leer credentials.json: {e}")
        return

    # 3) Cargar regiones entrenadas
    regions_path = os.path.join(BASE_DIR, "regions.json")
    regions = FileManager.load_regions(regions_path)
    required = {"correo", "contraseña", "boton entrar"}
    if not required.issubset(regions):
        print("[ERROR] regions.json incompleto. Ejecute la opción 1 primero.")
        return

    # 4) Configurar detectores con patrones glob (sin debug_folder)
    giro_detector = GiroDetector(
        os.path.join(TEMPLATES_DIR, "giro_*.png"),
        threshold=0.8
    )
    ruleta_detector = RuletaDetector(
        os.path.join(TEMPLATES_DIR, "ruleta_*.png"),
        threshold=0.85
    )
    numero_detector = NumeroDetector(
        os.path.join(TEMPLATES_DIR, "numero_*.png"),
        threshold=0.9
    )
    region_finder = RegionFinder([giro_detector, ruleta_detector, numero_detector])

    # 5) Inicializar DB y estadísticas
    db_manager = DBManager(db_path=DB_PATH)
    stats_helper = StatsHelper(window_size=50, epsilon=0.1, historial=[])

    # 6) Preparar DataCollector reutilizando detectores
    data_collector = DataCollector(
        ruleta_detector=ruleta_detector,
        numero_detector=numero_detector
    )

    # 7) LoginAutomation con detección de regiones
    login = LoginAutomation(
        creds=creds,
        region_finder=region_finder,
        simulate=not modo_real,
        human_click_fn=human_click
    )
    if not login.login_or_continue():
        print("[ERROR] Login no confirmado. Abortando.")
        return
    print("✅ Login exitoso. Monitoreo/apuestas activo.")

    # 8) Ejecutar motor principal
    engine = MainEngine(
        region_finder=region_finder,
        data_collector=data_collector,
        stats_helper=stats_helper,
        db_manager=db_manager,
        strategy_manager=strategy_manager,
        place_bet_fn=login.apostar_opcion,
        login_handler=login,
        login_url=TARGET_URL,
        cooldown=12.0,
        wager_value=500
    )
    engine.run()

    # 9) Limpieza final
    print("✅ Proceso finalizado. Cerrando navegador…")
    login.close_browser()


if __name__ == "__main__":
    main()
