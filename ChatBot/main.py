import threading
import time
from playwright.sync_api import sync_playwright
from mercadolibre import procesar_preguntas_vendedor
from whatsapp import iniciar_whatsapp_admin, iniciar_whatsapp_usuario, admin_lock, admin_request_pending
from model_config import load_model_and_tokenizer
from text_processing import construir_prompt, generar_respuesta

CHROME_PROFILE_PATH = r"C:\Users\faber\Documents\Python\chrome_profile_mercadolibre"

# Cargar el modelo y el tokenizador (globalmente para usar en otros módulos)
model, tokenizer = load_model_and_tokenizer()

def iniciar_mercadolibre_respuestas():
    from playwright.sync_api import sync_playwright
    print("DEBUG: Iniciando Playwright con perfil de usuario de MercadoLibre...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(CHROME_PROFILE_PATH, headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://www.mercadolibre.com.co/")
        time.sleep(10)
        if "ingresar" in page.url.lower():
            print("DEBUG: No se detectó sesión iniciada en MercadoLibre. Inicia sesión manualmente y reinicia el bot.")
            return
        print("DEBUG: Sesión de MercadoLibre detectada correctamente.")
        while True:
            with admin_lock:
                pending = admin_request_pending
            if pending:
                print("DEBUG: Hay una solicitud pendiente; esperando respuesta del admin...")
                time.sleep(10)
                continue
            resultados = procesar_preguntas_vendedor(page)
            if resultados:
                # Procesar cada pregunta y enviar respuesta
                for li, texto, prompt in resultados:
                    print(f"DEBUG: Prompt construido:\n{prompt}")
                    respuesta = generar_respuesta(prompt, model, tokenizer)
                    print(f"DEBUG: Respuesta generada: {respuesta}")
                    # Aquí se integraría la lógica para enviar la respuesta en MercadoLibre
                    # (por ejemplo, haciendo clic en "Responder" y llenando el campo)
                    # Para simplificar, se muestra la respuesta generada.
            time.sleep(30)

def run_mercadolibre():
    iniciar_mercadolibre_respuestas()

def run_whatsapp_admin():
    iniciar_whatsapp_admin()

def run_whatsapp_usuario():
    page = iniciar_whatsapp_usuario()
    # Aquí se puede integrar el procesamiento de mensajes de usuario si es necesario.
    while True:
        time.sleep(30)

if __name__ == "__main__":
    thread_ml = threading.Thread(target=run_mercadolibre)
    thread_wp_admin = threading.Thread(target=run_whatsapp_admin)
    thread_wp_usuario = threading.Thread(target=run_whatsapp_usuario)

    thread_ml.start()
    thread_wp_admin.start()
    thread_wp_usuario.start()

    thread_ml.join()
    thread_wp_admin.join()
    thread_wp_usuario.join()
