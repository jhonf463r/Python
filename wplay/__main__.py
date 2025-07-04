# File: wplay/__main__.py

import logging
# ─── Forzar DEBUG global ───
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

import json
import time
import os
import inspect
import tensorflow as tf
import json
from wplay.wplay_config.hyperparams import HyperParams
from wplay.strategy.betting_engine import BettingEngine
from wplay.config import DB_PATH, CHROME_EXECUTABLE, USER_DATA_DIR, CHROME_PROFILE, TARGET_URL
from wplay.auth.login import LoginAutomation
from wplay.trainer.region_trainer import RegionTrainer
from wplay.file_manager.file_manager import FileManager
from wplay.capture.chrome_handler import ChromeHandler
from wplay.capture.data_collector import DataCollector
from wplay.strategy.stats_helper import StatsHelper
from wplay.data.db_manager import DBManager
from wplay.strategy.dqn_agent import DQNAgent
from wplay.strategy.ppo_agent import PPOAgent

# Importa tu helper modificado
from wplay.utils.helpers import obtener_datos_actualizados

# ─── TensorFlow GPU settings ───
tf.config.run_functions_eagerly(False)
for gpu in tf.config.list_physical_devices('GPU'):
    tf.config.experimental.set_memory_growth(gpu, True)
print("GPUs disponibles:", tf.config.list_physical_devices('GPU'))


def main():

    import inspect

    # 0) Cargar mejores hiperparámetros si existen
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    hp_file = os.path.join(root, "best_hyperparams.json")

    if os.path.exists(hp_file):
        with open(hp_file, "r") as f:
            data = json.load(f)

        # Obtener las claves válidas directamente desde la firma del constructor
        valid_keys = set(inspect.signature(HyperParams.__init__).parameters.keys()) - {"self"}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        rejected = {k: v for k, v in data.items() if k not in valid_keys}

        print("✅ Hiperparámetros cargados desde best_hyperparams.json:\n")
        for k, v in filtered.items():
            print(f"  ✔️ {k}: {v}")
        if rejected:
            print("\n⚠️  Claves ignoradas (no están en HyperParams):")
            for k, v in rejected.items():
                print(f"  ❌ {k}: {v}")

        hp = HyperParams(**filtered)

        # (Opcional) Guardar versión limpia
        cleaned_path = os.path.join(root, "best_hyperparams_cleaned.json")
        with open(cleaned_path, "w") as f:
            json.dump(filtered, f, indent=2)
        print(f"\n🧼 best_hyperparams_cleaned.json guardado en {cleaned_path}")
    else:
        hp = HyperParams()
        print("⚡ Usando hiperparámetros por defecto:")
        for k, v in hp.__dict__.items():
            print(f"  ✔️ {k}: {v}")



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
    try:
        # Ahora pasamos el hp cargado a tu helper
        strategy_manager = obtener_datos_actualizados(
            hp                = hp,
            dqn_agent_cls     = DQNAgent,
            ppo_agent_cls     = PPOAgent,
            dqn_kwargs        = {},
            ppo_kwargs        = {}
        )
    except Exception as e:
        print(f"[ERROR] No se pudo completar el pipeline offline: {e}")
        return

    print("✅ Pipeline offline completado.")

    # ——— Preparar resto de componentes ———
    chrome = ChromeHandler(
        executable_path=CHROME_EXECUTABLE,
        user_data_dir=USER_DATA_DIR,
        profile=CHROME_PROFILE
    )
    chrome.open_chrome(TARGET_URL)
    print("Esperando a que la página se cargue…")
    time.sleep(10)

    creds_path = os.path.join(os.getcwd(), "credentials.json")
    try:
        with open(creds_path, "r") as f:
            creds = json.load(f)
    except Exception as e:
        print(f"Error al cargar credenciales: {e}")
        return

    regions = FileManager.load_regions("regions.json")
    if not all(k in regions for k in ("correo","contraseña","boton entrar")):
        print("Regiones incompletas. Entrena regiones primero.")
        return

    db_manager   = DBManager(db_path=DB_PATH)
    stats_helper = StatsHelper(window_size=50, epsilon=0.1, historial=[])

    data_collector = DataCollector(
        ruleta_detector=chrome.ruleta_detector,
        numero_detector=chrome.numero_detector,
        regions=regions
    )

    login = LoginAutomation(
        creds=creds,
        regions=regions,
        db_path=DB_PATH
    )
    login.set_simulation(not modo_real)
    if not login.login_or_continue():
        print("⚠️ No se confirmó el login; continuando en modo monitoreo.")

    print("✅ Modo monitoreo/apuestas activo. Ctrl+C para salir.")
    print("🎲 Iniciando BettingEngine...")

    # 7) Finalmente, arrancar BettingEngine
    BettingEngine(
        region_finder    = login,
        data_collector   = data_collector,
        stats_helper     = stats_helper,
        db_manager       = db_manager,
        place_bet_fn     = login.apostar_opcion,
        strategy_manager = strategy_manager,
        login_handler    = login,
        login_url        = TARGET_URL,
        cooldown         = hp.cooldown,      # ahora usa hp
        wager_value      = hp.wager_value    # y aquí también
    ).run()


if __name__ == "__main__":
    main()
