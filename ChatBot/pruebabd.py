import json
import time
import sqlite3
import unicodedata
import re
import threading
import queue
import torch
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ================================
# CONFIGURACIÓN DEL MODELO MISTRAL
# ================================
model_id = "mistralai/Mistral-7B-Instruct-v0.3"
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained(model_id)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
print("Modelo cargado con éxito.", flush=True)

# =====================================
# CONFIGURACIÓN DE LA BASE DE DATOS (Productos y variantes)
# =====================================
DB_PATH = r"C:\Users\faber\Documents\Python\ChatBot\publicaciones_tienda.db"

def obtener_id_por_titulo(titulo):
    # Se usa rowid en lugar de "id"
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT rowid FROM publicaciones WHERE titulo LIKE ? LIMIT 1", ('%' + titulo + '%',))
    row = cursor.fetchone()
    conexion.close()
    return row[0] if row else None

def obtener_variantes(publicacion_id):
    try:
        conexion = sqlite3.connect(DB_PATH)
        cursor = conexion.cursor()
        cursor.execute("SELECT variante FROM variante WHERE publicacion_id = ?", (publicacion_id,))
        rows = cursor.fetchall()
        conexion.close()
        return [row[0].lower() for row in rows] if rows else []
    except sqlite3.OperationalError as e:
        print("Error al obtener variantes:", e)
        return []

# =============================================
# FUNCIONES DE PROCESAMIENTO DE TEXTO
# =============================================
def limpiar_texto(texto):
    if texto is None:
        return ""
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').strip()

def extraer_palabras_clave(texto):
    return re.findall(r'\b\w+\b', limpiar_texto(texto))

def buscar_con_palabras_clave(palabras, limite=3):
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    resultados = []
    if palabras:
        condiciones = " OR ".join(["(titulo LIKE ? OR descripcion LIKE ?)"] * len(palabras))
        consulta = f"""
        SELECT rowid, titulo, descripcion, precio_base, moneda, cantidad_total
        FROM publicaciones
        WHERE {condiciones}
        """
        valores = []
        for palabra in palabras:
            valores.extend([f"%{palabra}%", f"%{palabra}%"])
        cursor.execute(consulta, valores)
        resultados = cursor.fetchall()[:limite]
    conexion.close()
    return resultados

def construir_prompt(mensaje, producto_info=None):
    mensaje_limpio = limpiar_texto(mensaje)
    if producto_info and producto_info.strip():
        info_productos = producto_info
    else:
        palabras_clave = extraer_palabras_clave(mensaje_limpio)
        productos = buscar_con_palabras_clave(palabras_clave, limite=3)
        if productos:
            info_productos = "\n".join([
                f"- {titulo if titulo else 'Sin título'}: {(descripcion[:100] if descripcion else 'Sin descripción')}... Precio: {precio if precio is not None else 'N/A'} {moneda if moneda else ''} Stock: {cantidad if cantidad is not None else 'N/A'}"
                for _, titulo, descripcion, precio, moneda, cantidad in productos
            ])
        else:
            info_productos = "No se encontraron productos relevantes en la base de datos."
    contexto = (
        "<<SYS>> Eres un asistente de atención al cliente especializado en ventas. "
        "Responde de forma lógica, coherente, breve y concisa en español. "
        "Utiliza la información de la tienda solo si es relevante para la consulta del usuario. "
        "<<SYS>>\n\n"
    )
    prompt = contexto + f"Usuario: {mensaje_limpio}\nInformación de la tienda:\n{info_productos}\n\nIA:"
    return prompt

def generar_respuesta(prompt):
    inputs_model = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        output = model.generate(
            **inputs_model,
            max_new_tokens=200,
            temperature=0.7,
            top_p=0.7,
            do_sample=True,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id
        )
    respuesta_completa = tokenizer.decode(output[0], skip_special_tokens=True).strip()
    if "IA:" in respuesta_completa:
        respuesta_final = respuesta_completa.split("IA:")[-1].strip()
    else:
        respuesta_final = respuesta_completa
    if not respuesta_final.strip():
        respuesta_final = "Lo siento, no pude generar una respuesta en este momento."
    return respuesta_final

# =============================================
# VARIABLES GLOBALES PARA ADMIN WHATSAPP
# =============================================
admin_request_pending = False
admin_response = None
admin_lock = threading.Lock()
admin_event = threading.Event()  # Para sincronizar la respuesta del admin
admin_request_queue = queue.Queue()
whatsapp_admin_page = None  # Se asignará en la sesión del admin

def limpiar_respuesta_admin(text):
    cleaned = re.sub(r'\d{1,2}:\d{2}\s*[ap]\.?m\.?', '', text, flags=re.IGNORECASE)
    cleaned = cleaned.replace("tail-in", "")
    return cleaned.strip()

def wait_for_admin_approval(question, generated_answer, timeout=1800):
    global admin_request_pending, admin_response
    with admin_lock:
        admin_request_pending = True
        admin_response = None
        admin_event.clear()
    send_admin_request(question, generated_answer)
    print("DEBUG: Solicitud de aprobación enviada al admin.", flush=True)
    # Espera hasta que admin responda antes de continuar
    admin_event.wait(timeout)
    with admin_lock:
        resp = admin_response
        admin_response = None
        admin_request_pending = False
        admin_event.clear()
    if resp:
        print(f"DEBUG: Se recibió respuesta del admin: {resp}", flush=True)
        resp_limpia = limpiar_respuesta_admin(resp)
        if "aprobar" in resp_limpia.lower():
            print("DEBUG: Admin aprobó la respuesta, usando respuesta generada.", flush=True)
            return generated_answer
        else:
            print("DEBUG: Admin envió respuesta alternativa.", flush=True)
            return resp_limpia
    else:
        print("DEBUG: No se recibió respuesta del admin; se usará la respuesta generada.", flush=True)
        return generated_answer

def send_admin_request(question, generated_answer):
    admin_request_queue.put((question, generated_answer))
    print("DEBUG: Solicitud de aprobación colocada en la cola.", flush=True)

# =============================================
# SESIÓN DE WHATSAPP ADMIN (N° +57 302 8571029)
# =============================================
def iniciar_whatsapp_admin():
    global whatsapp_admin_page, admin_response, admin_request_pending
    with sync_playwright() as p:
        print("DEBUG: Iniciando sesión de WhatsApp para el admin...", flush=True)
        browser = p.chromium.launch_persistent_context("whatsapp_admin_session", headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com/")
        print("DEBUG: Escanea el código QR si es la primera vez para el admin.", flush=True)
        time.sleep(20)
        try:
            admin_chat = page.locator('span[title*="+57 302 8571029"]').first
            admin_chat.wait_for(state="visible", timeout=60000)
            admin_chat.click()
            print("DEBUG: Chat del admin abierto.", flush=True)
        except Exception as e:
            print("❌ Error al abrir el chat del admin:", e, flush=True)
        whatsapp_admin_page = page
        last_message = ""
        while True:
            try:
                try:
                    req_question, req_generated = admin_request_queue.get_nowait()
                    message = (
                        f"Solicitud de aprobación:\n"
                        f"Pregunta: {req_question}\n"
                        f"Respuesta generada: {req_generated}\n\n"
                        "Responde con 'Aprobar' o envía una respuesta alternativa."
                    )
                    msg_input = page.locator('div[aria-label="Escribe un mensaje"][contenteditable="true"]')
                    msg_input.wait_for(state="visible", timeout=10000)
                    msg_input.fill(message)
                    send_btn = page.locator('span[aria-hidden="true"][data-icon="send"]')
                    send_btn.wait_for(state="visible", timeout=10000)
                    send_btn.click()
                    print("DEBUG: Solicitud enviada al admin vía WhatsApp.", flush=True)
                except queue.Empty:
                    pass

                try:
                    messages = page.locator("div.message-in").all()
                    if messages:
                        current_last = messages[-1].text_content(timeout=5000).strip()
                        if current_last and current_last != last_message:
                            last_message = current_last
                            with admin_lock:
                                if admin_request_pending and admin_response is None:
                                    admin_response = last_message
                                    admin_event.set()
                                    print("DEBUG: Mensaje del admin detectado:", admin_response, flush=True)
                except Exception as e:
                    print("❌ Error al monitorear mensajes del admin:", e, flush=True)
                time.sleep(1)
            except Exception as e:
                print("❌ Error en el ciclo del admin:", e, flush=True)
                time.sleep(5)

# =============================================
# SESIÓN DE WHATSAPP USUARIO (Procesa mensajes entrantes de clientes)
# =============================================
def iniciar_whatsapp_usuario():
    with sync_playwright() as p:
        print("DEBUG: Iniciando sesión de WhatsApp para usuarios...", flush=True)
        browser = p.chromium.launch_persistent_context("whatsapp_usuario_session", headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com/")
        print("DEBUG: Escanea el código QR si es la primera vez para usuarios.", flush=True)
        time.sleep(20)
        while True:
            try:
                print("DEBUG: Buscando chats con mensajes no leídos en WhatsApp (usuarios)...", flush=True)
                chats = page.locator('div[aria-label="Lista de chats"] div[role="listitem"]').all()
                if not chats:
                    print("DEBUG: No se detectaron chats.", flush=True)
                    time.sleep(10)
                    continue
                for idx, chat in enumerate(chats):
                    unread = chat.locator('span[aria-label*="mensaje no leído"]')
                    if unread.count() > 0:
                        contact_name = chat.locator('span[dir="auto"]').text_content().strip() or f"Chat {idx+1}"
                        print(f"DEBUG: Chat detectado: {contact_name}", flush=True)
                        chat.click()
                        time.sleep(2)
                        message_input = page.locator('div[aria-label="Escribe un mensaje"][contenteditable="true"]')
                        message_input.wait_for(state="visible", timeout=90000)
                        messages = page.locator('div[class*="message-in"] span[dir="ltr"]').all()
                        if messages:
                            last_message = messages[-1].text_content().strip()
                        else:
                            print("DEBUG: No se encontraron mensajes entrantes.", flush=True)
                            continue
                        print(f"DEBUG: Mensaje recibido: {last_message}", flush=True)
                        prompt = construir_prompt(last_message)
                        print(f"DEBUG: Prompt construido:\n{prompt}", flush=True)
                        generated_answer = generar_respuesta(prompt)
                        print(f"DEBUG: Respuesta generada: {generated_answer}", flush=True)
                        # Si se detectan palabras clave técnicas, se usa la info del producto (se ignora la lógica de variantes)
                        if "altura" in last_message.lower() or "distancia" in last_message.lower():
                            prompt = construir_prompt(last_message, producto_info=None)
                        final_answer = wait_for_admin_approval(last_message, generated_answer, timeout=1800)
                        print(f"DEBUG: Respuesta final aprobada: {final_answer}", flush=True)
                        message_input.fill(final_answer)
                        send_btn = page.locator('span[aria-hidden="true"][data-icon="send"]')
                        send_btn.wait_for(state="visible", timeout=10000)
                        send_btn.click()
                        print("DEBUG: Mensaje enviado por WhatsApp (usuario).", flush=True)
                        time.sleep(2)
            except Exception as e:
                print("❌ Error en WhatsApp usuario:", e, flush=True)
                time.sleep(5)

# =============================================
# SESIÓN DE MERCADOLIBRE RESPONDER CON APROBACIÓN ADMIN
# =============================================
CHROME_PROFILE_PATH = r"C:\Users\faber\Documents\Python\chrome_profile_mercadolibre"

def procesar_preguntas_vendedor(page):
    print("DEBUG: Procesando preguntas en Preguntas Vendedor...", flush=True)
    page.goto("https://www.mercadolibre.com.co/preguntas/vendedor")
    page.wait_for_load_state("networkidle")
    time.sleep(5)
    try:
        preguntas = page.locator("ul.andes-list.sc-questions li.andes-list__item.sc-question").all()
    except Exception as e:
        print("❌ Error al localizar la lista de preguntas:", e, flush=True)
        return

    if not preguntas:
        print("DEBUG: No se encontraron preguntas en Preguntas Vendedor.", flush=True)
        return

    # Para evitar reprocesar la misma pregunta
    global _processed_questions
    try:
        _processed_questions
    except NameError:
        _processed_questions = set()

    for li in preguntas:
        try:
            texto = li.locator("span.sc-question-detail__question--text").text_content().strip()
        except Exception as e:
            print("❌ Error al extraer el texto de la pregunta:", e, flush=True)
            continue

        if texto in _processed_questions:
            continue
        _processed_questions.add(texto)

        print(f"DEBUG: Pregunta detectada: {texto}", flush=True)
        try:
            usuario = li.locator("div.sc-personal-information div.sc-label-null__default").first.text_content().strip()
        except Exception as e:
            usuario = "Usuario desconocido"
            print("❌ Error al extraer el usuario:", e, flush=True)
        print(f"DEBUG: Usuario: {usuario}", flush=True)
        try:
            producto_info = li.evaluate('''(node) => {
                let card = node.closest('.sc-item');
                if(card){
                    let header = card.querySelector('.sc-item__header .sc-item-header__content');
                    return header ? header.innerText.trim() : "";
                }
                return "";
            }''')
        except Exception as e:
            producto_info = ""
            print("❌ Error al extraer la información del producto:", e, flush=True)
        print(f"DEBUG: Producto: {producto_info}", flush=True)
        if not producto_info:
            print("DEBUG: No se identificó el producto; omitiendo esta pregunta.", flush=True)
            continue
        product_title = producto_info.split('\n')[0].strip()
        pub_id = obtener_id_por_titulo(product_title)
        if not pub_id:
            print("DEBUG: No se encontró publicación en BD para el producto.", flush=True)
            variants_available = []
        else:
            variants_available = obtener_variantes(pub_id)
        print("DEBUG: Variantes disponibles:", variants_available, flush=True)
        
        requested_variant = texto.split()[-1].strip().lower()
        if "altura" in texto.lower() or "distancia" in texto.lower():
            prompt = construir_prompt(texto, producto_info)
        else:
            if requested_variant not in variants_available:
                print(f"DEBUG: La variante solicitada '{requested_variant}' no está disponible. Variantes disponibles: {variants_available}", flush=True)
                prompt = (
                    "<<SYS>> Eres un asistente de atención al cliente especializado en ventas. "
                    "El cliente pregunta si está disponible la variante '{variant}' del producto '{product_title}'. "
                    "Indica que actualmente no contamos con esa variante, pero ofrece las variantes disponibles: {available}. "
                    "Responde de forma lógica, coherente, breve y concisa en español. "
                    "<<SYS>>\n\nUsuario: {mensaje}\nIA:".format(
                        variant=requested_variant,
                        product_title=product_title,
                        available=", ".join(variants_available) if variants_available else "Ninguna",
                        mensaje=limpiar_texto(texto)
                    )
                )
            else:
                prompt = construir_prompt(texto, producto_info)
        print(f"DEBUG: Prompt construido:\n{prompt}", flush=True)
        generated_answer = generar_respuesta(prompt)
        print(f"DEBUG: Respuesta generada: {generated_answer}", flush=True)
        final_answer = wait_for_admin_approval(texto, generated_answer, timeout=1800)
        print(f"DEBUG: Respuesta final aprobada: {final_answer}", flush=True)
        try:
            boton_responder = li.locator('button[title="Responder"]')
            if boton_responder.count() > 0:
                boton_responder.click()
                time.sleep(2)
            else:
                print("DEBUG: No se encontró botón 'Responder'; se asume que el campo ya está abierto.", flush=True)
        except Exception as e:
            print("❌ Error al intentar abrir el campo de respuesta:", e, flush=True)
        try:
            campo_respuesta = li.locator("textarea[data-testid='textfield-reply']")
            if campo_respuesta.count() > 0:
                campo_respuesta.fill(final_answer)
                print("DEBUG: La respuesta se ha escrito en el campo de texto.", flush=True)
            else:
                print("DEBUG: No se encontró el campo de respuesta en este contenedor.", flush=True)
        except Exception as e:
            print("❌ Error al rellenar el campo de respuesta:", e, flush=True)
        time.sleep(5)

def iniciar_mercadolibre_respuestas():
    with sync_playwright() as p:
        print("DEBUG: Iniciando Playwright con perfil de usuario de MercadoLibre...", flush=True)
        browser = p.chromium.launch_persistent_context(CHROME_PROFILE_PATH, headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://www.mercadolibre.com.co/")
        time.sleep(10)
        if "ingresar" in page.url.lower():
            print("DEBUG: No se detectó sesión iniciada. Inicia sesión manualmente y reinicia el bot.", flush=True)
            return
        print("DEBUG: Sesión de MercadoLibre detectada correctamente.", flush=True)
        # Antes de buscar nuevas preguntas, esperamos a que no haya solicitudes pendientes al admin.
        while True:
            with admin_lock:
                pending = admin_request_pending
            if pending:
                print("DEBUG: Hay una solicitud pendiente, esperando respuesta del admin...", flush=True)
                time.sleep(10)
                continue

            try:
                procesar_preguntas_vendedor(page)
                time.sleep(30)
            except Exception as e:
                print(f"❌ Error detectado: {e}", flush=True)
                time.sleep(5)

# ========================
# EJECUTAR EL BOT
# ========================
def run_mercadolibre():
    iniciar_mercadolibre_respuestas()

def run_whatsapp_admin():
    iniciar_whatsapp_admin()

def run_whatsapp_usuario():
    iniciar_whatsapp_usuario()

if __name__ == "__main__":
    thread_ml = threading.Thread(target=run_mercadolibre)
    thread_wp_usuario = threading.Thread(target=run_whatsapp_usuario)
    thread_wp_admin = threading.Thread(target=run_whatsapp_admin)

    thread_ml.start()
    thread_wp_admin.start()
    thread_wp_usuario.start()

    thread_ml.join()
    thread_wp_admin.join()
    thread_wp_usuario.join()