# wplay/__main__.py

import json
import time
import os
from wplay.strategy.betting_engine import BettingEngine

from wplay.config import DB_PATH, CHROME_EXECUTABLE, USER_DATA_DIR, CHROME_PROFILE, TARGET_URL
from wplay.auth.login import LoginAutomation
from wplay.trainer.region_trainer import RegionTrainer
from wplay.file_manager.file_manager import FileManager
from wplay.capture.chrome_handler import ChromeHandler
from wplay.capture.data_collector import DataCollector
from wplay.strategy.betting_engine import BettingEngine
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager

# Importamos la orquestación offline
from wplay.utils.helpers import obtener_datos_actualizados


def main():
    print("1. Entrenar nuevas regiones")
    print("2. Iniciar sesión y comenzar monitoreo/apuestas")
    opcion = input("Seleccione una opción (1/2): ").strip()

    if opcion == "1":
        RegionTrainer(
            regions_file="regions.json",
            images_folder="region_images"
        ).train()
        return

    if opcion != "2":
        print("Opción inválida.")
        return

    modo_real = input("¿Activar apuestas REALES? (s/N): ").lower().startswith("s")
    print(f">>> Modo de apuestas: {'REAL' if modo_real else 'SIMULACIÓN'}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # ——— Orquestación offline antes de abrir el navegador ———
    print("🚀 Iniciando pipeline de entrenamiento offline antes del monitoreo…")
    strategy_manager = obtener_datos_actualizados()
    print("✅ Pipeline offline completado.")

    # ——— Preparar resto de componentes ———
    # Chrome
    chrome = ChromeHandler(
        executable_path=CHROME_EXECUTABLE,
        user_data_dir=USER_DATA_DIR,
        profile=CHROME_PROFILE
    )
    chrome.open_chrome(TARGET_URL)
    print("Esperando a que la página se cargue…")
    time.sleep(10)

    # Credenciales
    creds_path = os.path.join(os.getcwd(), "credentials.json")
    try:
        with open(creds_path, "r") as f:
            creds = json.load(f)
    except Exception as e:
        print(f"Error al cargar credenciales: {e}")
        return

    # Regiones
    regions = FileManager.load_regions("regions.json")
    if not all(k in regions for k in ("correo", "contraseña", "boton entrar")):
        print("Regiones incompletas. Entrena regiones primero.")
        return

    # Otros managers
    db_manager     = DBManager(db_path=DB_PATH)
    stats_helper   = StatsHelper(window_size=50, epsilon=0.1, historial=[])
    data_collector = DataCollector(
        ruleta_detector  = chrome.ruleta_detector,
        numero_detector  = chrome.numero_detector,
        regions          = regions
    )

    # Login
    login = LoginAutomation(
        creds    = creds,
        regions  = regions,
        db_path  = DB_PATH
    )
    login.set_simulation(not modo_real)
    if not login.login_or_continue():
        print("⚠️ No se confirmó el login; continuando en modo monitoreo.")

    print("✅ Modo monitoreo/apuestas activo. Ctrl+C para salir.")
    print("🎲 Iniciando BettingEngine...")

    BettingEngine(
        region_finder    = login,
        data_collector   = data_collector,
        strategy_manager = strategy_manager,
        stats_helper     = stats_helper,
        db_manager       = db_manager,
        place_bet_fn     = login.apostar_opcion,
        cooldown         = 12.0,
        wager_value      = 500
    ).run()


if __name__ == "__main__":
    main()
