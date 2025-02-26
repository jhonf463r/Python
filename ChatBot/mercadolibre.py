import json
import time
import sqlite3
import unicodedata
import re
import torch
from playwright.sync_api import sync_playwright
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

print("Modelo cargado con éxito.")

# =====================================
# CONFIGURACIÓN DE LA BASE DE DATOS (Productos y variantes)
# =====================================

DB_PATH = r"C:\Users\faber\Documents\Python\ChatBot\publicaciones_tienda.db"

def obtener_id_por_titulo(titulo):
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT id FROM publicaciones WHERE titulo LIKE ? LIMIT 1", ('%' + titulo + '%',))
    row = cursor.fetchone()
    conexion.close()
    return row[0] if row else None

def obtener_variantes(publicacion_id):
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT variante FROM variante WHERE publicacion_id = ?", (publicacion_id,))
    rows = cursor.fetchall()
    conexion.close()
    return [row[0].lower() for row in rows] if rows else []

# =============================================
# FUNCIONES DE PROCESAMIENTO DE TEXTO
# =============================================

def limpiar_texto(texto):
    if texto is None:
        return ""
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.strip()

def extraer_palabras_clave(texto):
    texto = limpiar_texto(texto)
    tokens = re.findall(r'\b\w+\b', texto)
    return tokens

def buscar_con_palabras_clave(palabras, limite=3):
    # Función de respaldo para buscar productos en la base de datos
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    resultados = []
    if palabras:
        condiciones = " OR ".join(["(titulo LIKE ? OR descripcion LIKE ?)"] * len(palabras))
        consulta = f"""
        SELECT id, titulo, descripcion, precio_base, moneda, cantidad_total
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
    # Si disponemos de la info del producto extraída de la página, se usa esa información
    if producto_info and producto_info.strip() != "":
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
# AUTOMATIZACIÓN CON PLAYWRIGHT PARA MERCADOLIBRE COLOMBIA
# =============================================

CHROME_PROFILE_PATH = r"C:\Users\faber\Documents\Python\chrome_profile_mercadolibre"

def procesar_preguntas_vendedor(page):
    print("Procesando preguntas en Preguntas Vendedor...")
    page.goto("https://www.mercadolibre.com.co/preguntas/vendedor")
    time.sleep(10)
    
    preguntas = page.locator("ul.andes-list.sc-questions li.andes-list__item.sc-question").all()
    if not preguntas:
        print("⚠️ No se encontraron preguntas en Preguntas Vendedor.")
        return
    
    for li in preguntas:
        try:
            texto = li.locator("span.sc-question-detail__question--text").text_content().strip()
        except Exception as e:
            print("❌ Error al extraer el texto de la pregunta:", e)
            continue
        print(f"📩 Pregunta detectada: {texto}")
        
        try:
            usuario = li.locator("div.sc-personal-information div.sc-label-null__default").first.text_content().strip()
        except Exception as e:
            usuario = "Usuario desconocido"
            print("❌ Error al extraer el usuario:", e)
        print(f"👤 Usuario: {usuario}")
        
        try:
            producto_info = li.evaluate('''(node) => {
                const card = node.closest('.sc-item');
                if(card){
                    const header = card.querySelector('.sc-item__header .sc-item-header__content');
                    return header ? header.innerText.trim() : "";
                }
                return "";
            }''')
        except Exception as e:
            producto_info = ""
            print("❌ Error al extraer la información del producto:", e)
        print(f"🛍️ Producto: {producto_info}")
        
        if not producto_info:
            print("⚠️ No se identificó el producto; no se responderá esta pregunta.")
            continue

        # Extraer el título del producto (se asume que es la primera línea)
        product_title = producto_info.split('\n')[0].strip()
        pub_id = obtener_id_por_titulo(product_title)
        if not pub_id:
            print("⚠️ No se encontró publicación en la base de datos para el producto.")
            variants_available = []
        else:
            variants_available = obtener_variantes(pub_id)
        print("Variantes disponibles:", variants_available)
        
        requested_variant = texto.split()[-1].strip().lower()
        if requested_variant not in variants_available:
            print(f"⚠️ La variante solicitada '{requested_variant}' no está disponible. Variantes disponibles: {variants_available}")
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
        print(f"✍️ Prompt construido:\n{prompt}\n")
        respuesta = generar_respuesta(prompt)
        print(f"✍️ Respuesta generada: {respuesta}")
        
        try:
            boton_responder = li.locator('button[title="Responder"]')
            if boton_responder.count() > 0:
                boton_responder.click()
                time.sleep(2)
            else:
                print("No se encontró botón 'Responder'; se asume que el campo ya está abierto.")
        except Exception as e:
            print("❌ Error al intentar abrir el campo de respuesta:", e)
        
        try:
            campo_respuesta = li.locator("textarea[data-testid='textfield-reply']")
            if campo_respuesta.count() > 0:
                campo_respuesta.fill(respuesta)
                print("✅ La respuesta se ha escrito en el campo de texto.")
            else:
                print("⚠️ No se encontró el campo de respuesta en este contenedor.")
        except Exception as e:
            print("❌ Error al rellenar el campo de respuesta:", e)
        
        # DESHABILITADO: Envío automático de la respuesta
        # Intentar hacer clic en el botón para enviar la respuesta (deshabilitado para pruebas)
        # try:
        #     boton_enviar = li.locator("button:has-text('Responder')")
        #     if boton_enviar.count() > 0:
        #         boton_enviar.click()
        #         print("✅ La respuesta se ha enviado automáticamente.")
        #     else:
        #         print("⚠️ No se encontró el botón para enviar la respuesta.")
        # except Exception as e:
        #     print("❌ Error al enviar la respuesta:", e)
        time.sleep(5)

def iniciar_mercadolibre_respuestas():
    with sync_playwright() as p:
        print("🔄 Iniciando Playwright con perfil de usuario de MercadoLibre...")
        browser = p.chromium.launch_persistent_context(CHROME_PROFILE_PATH, headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        page.goto("https://www.mercadolibre.com.co/")
        time.sleep(10)
        if "ingresar" in page.url.lower():
            print("⚠️ No se detectó sesión iniciada. Inicia sesión manualmente y reinicia el bot.")
            return
        print("✅ Sesión de MercadoLibre detectada correctamente.")
        
        while True:
            try:
                procesar_preguntas_vendedor(page)
                time.sleep(30)
            except Exception as e:
                print(f"❌ Error detectado: {e}")
                time.sleep(5)

# ========================
# EJECUTAR EL BOT
# ========================

iniciar_mercadolibre_respuestas()
