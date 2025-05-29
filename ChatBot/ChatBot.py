import json
import time
import sqlite3
import unicodedata
import re
import torch
from playwright.sync_api import sync_playwright
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Intentar importar Voyager (opcional, para IA adaptable)
try:
    import voyager
except ImportError:
    print("⚠️ Advertencia: Voyager no está instalado o no tiene el módulo 'Agent'.")

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

print("Modelo cargado con éxito.")

# =====================================
# CONFIGURACIÓN DE LA BASE DE DATOS (Productos)
# =====================================

DB_PATH = r"C:\Users\faber\Documents\Python\ChatBot\publicaciones_tienda.db"

# ================================
# HISTORIAL DE CONVERSACIONES
# ================================

def init_conversation_db():
    conn = sqlite3.connect("conversaciones.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversaciones (
            contact_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            mensaje_usuario TEXT,
            respuesta_ia TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_conversacion(contact_name, mensaje_usuario, respuesta_ia):
    conn = sqlite3.connect("conversaciones.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversaciones (contact_name, mensaje_usuario, respuesta_ia) VALUES (?, ?, ?)",
        (contact_name, mensaje_usuario, respuesta_ia)
    )
    conn.commit()
    conn.close()

def obtener_historial(contact_name, limite=5):
    conn = sqlite3.connect("conversaciones.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT mensaje_usuario, respuesta_ia FROM conversaciones WHERE contact_name=? ORDER BY timestamp DESC LIMIT ?",
        (contact_name, limite)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]  # Orden cronológico (las interacciones antiguas primero)

init_conversation_db()

# =====================================
# FUNCIONES DE PROCESAMIENTO DE TEXTO
# =====================================

def limpiar_texto(texto):
    if texto is None:
        return ""
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.strip()

# Lista básica de stopwords para español
STOPWORDS = set([
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "de", "del", "al", "a", "en", "que", "por", "con"
])

def extraer_palabras_clave(texto):
    """
    Extrae palabras clave usando expresiones regulares y filtra stopwords.
    """
    texto = limpiar_texto(texto)
    tokens = re.findall(r'\b\w+\b', texto)
    tokens_filtrados = [token for token in tokens if token not in STOPWORDS]
    return tokens_filtrados

# ===============================================
# ANÁLISIS DE LA CONSULTA CON LA IA (ENFOQUE HÍBRIDO)
# ===============================================

def analizar_consulta_con_ia(mensaje):
    prompt = (
        "Analiza el siguiente mensaje y responde en formato JSON con las siguientes claves:\n"
        '"consultar_bd": (true o false) indicando si se debe consultar la base de datos,\n'
        '"palabras_clave": una lista de palabras clave relevantes para la búsqueda.\n'
        "Solo responde en formato JSON.\n\n"
        f"Mensaje: \"{mensaje}\""
    )
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=100,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    respuesta = tokenizer.decode(output[0], skip_special_tokens=True).strip()
    print("DEBUG: Respuesta del modelo para análisis:", respuesta)
    try:
        data = json.loads(respuesta)
        return data
    except Exception as e:
        print("❌ Error al parsear JSON de análisis:", e)
        fallback_keywords = extraer_palabras_clave(mensaje)
        print("DEBUG: Palabras clave extraídas por fallback:", fallback_keywords)
        return {"consultar_bd": True, "palabras_clave": fallback_keywords}

# ==============================================
# CONSULTA A LA BASE DE DATOS DE PRODUCTOS
# ==============================================

def buscar_con_palabras_clave(palabras, limite=3):
    """
    Realiza una consulta a la base de datos utilizando las palabras clave.
    Se busca en 'titulo' y 'descripcion' usando condiciones OR para obtener
    todos los candidatos. Luego, se calcula un puntaje de relevancia basado en
    la cantidad de ocurrencias de cada palabra en el título y la descripción.
    Se retornan los productos mejor puntuados (hasta el límite indicado).
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    resultados = []
    if palabras:
        # Condiciones usando OR para obtener un conjunto amplio de candidatos
        condiciones = " OR ".join(["(titulo LIKE ? OR descripcion LIKE ?)"] * len(palabras))
        consulta = f"""
        SELECT titulo, descripcion, precio_base, moneda, cantidad_total
        FROM publicaciones
        WHERE {condiciones}
        """
        valores = []
        for palabra in palabras:
            valores.extend([f"%{palabra}%", f"%{palabra}%"])
        print("DEBUG: Consulta SQL:", consulta)
        print("DEBUG: Parámetros:", valores)
        cursor.execute(consulta, valores)
        rows = cursor.fetchall()
        
        # Función de scoring: cuenta las apariciones de cada palabra clave en el título y descripción
        def score(row):
            titulo, descripcion, _, _, _ = row
            texto = f"{titulo} {descripcion}".lower()
            puntaje = 0
            for palabra in palabras:
                puntaje += texto.count(palabra.lower())
            return puntaje
        
        # Ordenar por puntaje descendente y seleccionar los primeros resultados
        rows_ordenados = sorted(rows, key=score, reverse=True)
        resultados = rows_ordenados[:limite]
    conexion.close()
    return resultados

# ==============================================
# CONSTRUCCIÓN DEL PROMPT INCLUYENDO HISTORIAL
# ==============================================

SALUDOS = ["hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás"]

def construir_prompt(mensaje, contact_name):
    mensaje_limpio = limpiar_texto(mensaje)
    
    # Si el mensaje es un saludo
    if mensaje_limpio in [s.lower() for s in SALUDOS]:
        contexto = (
            "<<SYS>> Eres un asistente de atención al cliente especializado en ventas. "
            "Si el mensaje del usuario es únicamente un saludo, responde con un saludo y pregunta en qué puedes ayudar, sin usar información adicional. "
            "<<SYS>>\n\n"
        )
        return contexto + f"Usuario: {mensaje_limpio}\nIA:"
    
    # Análisis híbrido: consulta a la IA y búsqueda en la base de datos
    analisis = analizar_consulta_con_ia(mensaje_limpio)
    info_productos = ""
    if analisis.get("consultar_bd"):
        keywords = analisis.get("palabras_clave", [])
        productos = buscar_con_palabras_clave(keywords, limite=3)
        if productos:
            info_productos = "\n".join([
                # Se muestra el precio tal cual (sin conversión) ya que se asume que está en la unidad correcta
                f"- {titulo if titulo else 'Sin título'}: {(descripcion[:100] if descripcion else 'Sin descripción')}... "
                f"Precio: {precio if precio is not None else 'N/A'} {moneda if moneda else ''} "
                f"Stock: {cantidad if cantidad is not None else 'N/A'}"
                for titulo, descripcion, precio, moneda, cantidad in productos
            ])
        else:
            info_productos = "No se encontraron productos relevantes en la base de datos."
    
    # Obtener historial de conversaciones
    historial = obtener_historial(contact_name, limite=5)
    historial_str = ""
    if historial:
        for user_msg, ia_resp in historial:
            historial_str += f"Usuario: {user_msg}\nIA: {ia_resp}\n"
    
    contexto = (
        "<<SYS>> Eres un asistente de atención al cliente especializado en ventas. "
        "Responde de forma lógica, coherente, breve y concisa en español. "
        "Utiliza la información de la base de datos solo si es relevante para la consulta del usuario. "
        "Considera el historial de conversaciones para mantener el contexto. "
        "<<SYS>>\n\n"
    )
    if historial_str:
        contexto += f"Historial de conversación:\n{historial_str}\n"
    if info_productos:
        contexto += f"Información de la tienda:\n{info_productos}\n\n"
    return contexto + f"Usuario: {mensaje_limpio}\nIA:"

# ==============================================
# VARIABLES GLOBALES PARA EVITAR REPETICIÓN
# ==============================================

processed_messages = {}

# ==============================================
# AUTOMATIZACIÓN CON PLAYWRIGHT PARA WHATSAPP
# ==============================================

def iniciar_whatsapp():
    with sync_playwright() as p:
        print("🔄 Iniciando Playwright...")
        browser = p.chromium.launch_persistent_context("whatsapp_session", headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com/")
        print("📌 Escanea el código QR si es la primera vez.")
        time.sleep(15)
        
        while True:
            try:
                print("\n🔎 Buscando chats con mensajes no leídos...")
                chats = page.locator('div[aria-label="Lista de chats"] div[role="listitem"]').all()
                if not chats:
                    print("⚠️ No se detectaron chats en la lista.")
                    time.sleep(10)
                    continue
                else:
                    print(f"📋 Se encontraron {len(chats)} chats.")
                
                for idx, chat in enumerate(chats):
                    unread_indicator = chat.locator('span[aria-label*="mensaje no leído"]')
                    if unread_indicator.count() > 0:
                        # Obtener nombre del contacto
                        contact_name = chat.locator('span[dir="auto"]').text_content()
                        contact_name = contact_name.strip() if contact_name else f"Chat {idx+1}"
                        print(f"\n🔹 Chat {idx + 1}: {contact_name}")
                        
                        chat.click()
                        time.sleep(2)
                        
                        # Espera a que el campo de mensaje sea visible
                        message_input = page.locator('div[aria-label="Escribe un mensaje"][contenteditable="true"]')
                        message_input.wait_for(state="visible", timeout=90000)
                        
                        # Extraer el último mensaje entrante
                        message_elements = page.locator('div[class*="message-in"] span[dir="ltr"]').all()
                        if message_elements and len(message_elements) > 0:
                            last_message = message_elements[-1].text_content()
                            if last_message is None:
                                print("⚠️ No se pudo leer el último mensaje.")
                                continue
                            last_message = last_message.strip()
                        else:
                            print("⚠️ No se encontraron mensajes entrantes.")
                            continue
                        
                        # Evitar reprocesar mensajes ya atendidos
                        if contact_name in processed_messages and processed_messages[contact_name] == last_message:
                            print(f"🔄 El mensaje ya fue procesado para {contact_name}. Saltando este chat.")
                            continue

                        print(f"📩 Último mensaje recibido: {last_message}")
                        
                        # Construir el prompt con historial
                        prompt = construir_prompt(last_message, contact_name)
                        print(f"✍️ Prompt construido:\n{prompt}\n")
                        
                        # Generar respuesta con el modelo
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
                        
                        print(f"✍️ Respuesta generada: {respuesta_final}")
                        
                        # Enviar la respuesta por WhatsApp
                        message_input.fill(respuesta_final)
                        send_button = page.locator('span[aria-hidden="true"][data-icon="send"]')
                        send_button.wait_for(state="visible", timeout=10000)
                        send_button.click()
                        print("✅ Mensaje enviado.")
                        
                        # Guardar interacción para evitar duplicados y en el historial
                        processed_messages[contact_name] = last_message
                        guardar_conversacion(contact_name, last_message, respuesta_final)
                        time.sleep(2)
            except Exception as e:
                print(f"❌ Error detectado: {e}")
                time.sleep(5)

# ========================
# EJECUTAR EL BOT
# ========================

iniciar_whatsapp()
