import os
import time
import json
import re
import numpy as np
import pyautogui
import cv2
import pytesseract
import pygetwindow as gw
import mss
import mss.tools
from difflib import SequenceMatcher

# Configurar la variable de entorno para Tesseract (asegúrate de que la carpeta tessdata esté en esta ruta)
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
# (Opcional) Si Tesseract no está en el PATH, descomenta la siguiente línea:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def similar(a, b):
    """Devuelve la similitud entre dos cadenas (valor entre 0 y 1)."""
    return SequenceMatcher(None, a, b).ratio()

def clean_text(text):
    """Elimina caracteres no alfanuméricos y convierte a minúsculas."""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def open_chrome():
    """Abre Chrome con el perfil 'IA' y la URL de wplay.co."""
    chrome_executable = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    user_data_dir = r'C:\Users\faber\AppData\Local\Google\Chrome\User Data'
    command = f'start "" "{chrome_executable}" --user-data-dir="{user_data_dir}" --profile-directory="IA" "https://wplay.co"'
    os.system(command)

def capture_chrome_window_mss():
    """
    Busca la ventana de Chrome que contenga "wplay" en el título y captura su región usando mss.
    Retorna la imagen capturada y la posición (left, top) de la ventana.
    """
    chrome_windows = gw.getWindowsWithTitle("wplay")
    if not chrome_windows:
        print("No se encontró la ventana de Chrome con 'wplay' en el título.")
        return None, None
    chrome_window = chrome_windows[0]
    win_left, win_top = chrome_window.left, chrome_window.top
    win_width, win_height = chrome_window.width, chrome_window.height

    with mss.mss() as sct:
        monitor = {"top": win_top, "left": win_left, "width": win_width, "height": win_height}
        sct_img = sct.grab(monitor)
        # Guardar la captura original para depuración
        mss.tools.to_png(sct_img.rgb, sct_img.size, output="chrome_window.png")
        return sct_img, (win_left, win_top)

def ocr_detect_fields(sct_img, debug=True, scale_factor=2, psm_mode="6"):
    """
    Realiza OCR sobre la imagen capturada para detectar todo el texto.
    
    Se escala la imagen para aumentar la resolución, se aplica CLAHE, umbralización adaptativa y una
    operación morfológica para limpiar ruido.
    
    Se recogen todos los bloques de texto, se ordenan por área y se guarda una imagen anotada ("annotated_sorted.png")
    con cada bloque numerado y su texto.
    
    Luego se utiliza fuzzy matching (con limpieza de texto) para comparar cada bloque con las keywords:
    "usuario", "correo", "email", "contraseña" y "entrar". Se usan umbrales específicos para cada una.
    Las coordenadas se convierten al tamaño original.
    """
    # Convertir la imagen mss (BGRA) a un array de numpy y luego a BGR
    img = np.array(sct_img)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    # Escalar la imagen para mejorar la detección de textos pequeños
    img_up = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    
    # Convertir a escala de grises
    gray = cv2.cvtColor(img_up, cv2.COLOR_BGR2GRAY)
    
    # Aplicar CLAHE para mejorar el contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)
    
    # Aplicar umbral adaptativo
    proc_img = cv2.adaptiveThreshold(
        gray_clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Operación morfológica para eliminar ruido
    kernel = np.ones((2,2), np.uint8)
    proc_img = cv2.morphologyEx(proc_img, cv2.MORPH_OPEN, kernel)
    
    # Guardar la imagen procesada para depuración
    if debug:
        cv2.imwrite("processed.png", proc_img)
    
    # Configuración psm_mode para Tesseract
    config = f"--psm {psm_mode}"
    data = pytesseract.image_to_data(proc_img, output_type=pytesseract.Output.DICT, lang="spa", config=config)
    
    # Recoger todos los bloques de texto y ordenarlos por área (de menor a mayor)
    boxes = []
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if text:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            area = w * h
            boxes.append((i, text, x, y, w, h, area))
    boxes_sorted = sorted(boxes, key=lambda b: b[6])
    
    # Crear imagen anotada para visualizar todos los bloques detectados
    annotated = cv2.cvtColor(proc_img, cv2.COLOR_GRAY2BGR)
    for idx, (i, text, x, y, w, h, area) in enumerate(boxes_sorted):
        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(annotated, f"{idx}:{text}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite("annotated_sorted.png", annotated)
    if debug:
        print("Imagen anotada guardada en: annotated_sorted.png")
        print("Datos OCR completos:")
        for idx, (i, text, x, y, w, h, area) in enumerate(boxes_sorted):
            print(f"{idx}: '{text}' at ({x},{y}) size ({w}x{h}), area: {area}")
    
    # Definir las keywords y sus umbrales de similitud
    keywords = ["usuario", "correo", "email", "contraseña", "entrar"]
    thresholds = {
        "usuario": 0.7,
        "correo": 0.7,
        "email": 0.7,
        "contraseña": 0.4,
        "entrar": 0.4
    }
    
    fields = {}
    for (i, text, x, y, w, h, area) in boxes_sorted:
        word = text.strip().lower()
        cleaned = clean_text(word)
        for keyword in keywords:
            sim = similar(cleaned, clean_text(keyword))
            if debug:
                print(f"Comparando '{cleaned}' con '{clean_text(keyword)}' => similitud: {sim:.2f}")
            if sim >= thresholds[keyword]:
                # Si ya existe un bloque para este keyword, conservar el de mayor similitud
                if keyword not in fields or sim > fields[keyword].get("sim", 0):
                    fields[keyword] = {
                        "x": int(x / scale_factor),
                        "y": int(y / scale_factor),
                        "w": int(w / scale_factor),
                        "h": int(h / scale_factor),
                        "sim": sim
                    }
    # Eliminar la clave "sim" de los resultados finales
    for k in fields:
        fields[k].pop("sim", None)
    
    if debug:
        print("Campos detectados (keywords):", fields)
    return fields

def save_fields(fields, filename="fields_coordinates.json"):
    """Guarda las coordenadas detectadas en un archivo JSON."""
    with open(filename, "w") as f:
        json.dump(fields, f, indent=4)

def load_fields(filename="fields_coordinates.json"):
    """Carga las coordenadas almacenadas desde un archivo JSON, si existe."""
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return None

def attempt_login(fields, win_offset, username, password):
    """
    Simula la interacción: hace clic en los campos detectados, escribe las credenciales,
    y busca el botón "entrar" para darle clic.
    Se requiere al menos el campo "contraseña" y uno de "usuario", "correo" o "email".
    Si no se detecta el botón "entrar", se retorna False para que se vuelva a ejecutar OCR.
    """
    if "contraseña" not in fields or (("usuario" not in fields) and ("correo" not in fields) and ("email" not in fields)):
        print("Campos insuficientes para iniciar sesión.")
        return False
    
    win_left, win_top = win_offset
    if "usuario" in fields:
        user_field = fields["usuario"]
    elif "correo" in fields:
        user_field = fields["correo"]
    else:
        user_field = fields["email"]
    pass_field = fields["contraseña"]
    
    user_center = (win_left + user_field["x"] + user_field["w"] // 2,
                   win_top + user_field["y"] + user_field["h"] // 2)
    pass_center = (win_left + pass_field["x"] + pass_field["w"] // 2,
                   win_top + pass_field["y"] + pass_field["h"] // 2)
    
    pyautogui.click(user_center[0], user_center[1])
    time.sleep(1)
    pyautogui.write(username, interval=0.1)
    time.sleep(1)
    pyautogui.click(pass_center[0], pass_center[1])
    time.sleep(1)
    pyautogui.write(password, interval=0.1)
    time.sleep(1)
    
    # Verificar si se detectó el botón "entrar"
    if "entrar" in fields:
        entrar_field = fields["entrar"]
        entrar_center = (win_left + entrar_field["x"] + entrar_field["w"] // 2,
                         win_top + entrar_field["y"] + entrar_field["h"] // 2)
        pyautogui.click(entrar_center[0], entrar_center[1])
        print("Se hizo clic en el botón 'entrar'.")
    else:
        print("No se detectó el botón 'entrar'; se considera fallo en la detección.")
        return False  # Retorna False para forzar re-detección
    
    time.sleep(5)
    # Aquí se debería implementar una verificación real del inicio de sesión.
    return True

def main():
    with open("credentials.json", "r") as f:
        creds = json.load(f)
    username = creds.get("username")
    password = creds.get("password")
    
    open_chrome()
    time.sleep(5)  # Esperar a que la ventana se abra y la página cargue
    
    max_attempts = 2
    attempt = 0
    login_success = False

    fields = load_fields()
    sct_img, win_offset = capture_chrome_window_mss()
    if sct_img is None or win_offset is None:
        print("No se pudo capturar la ventana de Chrome.")
        return
    
    if not fields or not (("contraseña" in fields) and (("usuario" in fields) or ("correo" in fields) or ("email" in fields))):
        fields = ocr_detect_fields(sct_img, debug=True, scale_factor=2, psm_mode="6")
        save_fields(fields)
    
    while attempt < max_attempts and not login_success:
        print(f"\nIntento de inicio de sesión: {attempt + 1}")
        login_success = attempt_login(fields, win_offset, username, password)
        if not login_success:
            print("Inicio de sesión fallido. Ejecutando detección de OCR nuevamente...")
            sct_img, win_offset = capture_chrome_window_mss()
            if sct_img is None:
                return
            fields = ocr_detect_fields(sct_img, debug=True, scale_factor=2, psm_mode="6")
            save_fields(fields)
            attempt += 1
        else:
            print("Inicio de sesión exitoso.")
            break
    
    if not login_success:
        print("No se pudo iniciar sesión después de 2 intentos.")

if __name__ == "__main__":
    main()
