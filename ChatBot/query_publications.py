import sqlite3
import re

# Conexión a la base de datos SQLite
def conectar_base_datos():
    try:
        conexion = sqlite3.connect(r'C:\Users\faber\Documents\Python\ChatBot\publicaciones_tienda.db')
        return conexion
    except sqlite3.Error as e:
        print("Error al conectar con la base de datos:", e)
        return None

# Función para buscar información sobre un producto
def buscar_producto(pregunta):
    conexion = conectar_base_datos()
    if not conexion:
        return "No se pudo conectar a la base de datos."

    cursor = conexion.cursor()

    try:
        # Limpiar la pregunta y extraer palabras clave
        palabras_clave = re.findall(r'\b\w+\b', pregunta.lower())

        # Consulta básica para buscar coincidencias en el título o descripción
        consulta = """
        SELECT * FROM publicaciones
        WHERE """

        # Agregar condiciones dinámicas basadas en palabras clave
        condiciones = []
        for palabra in palabras_clave:
            condiciones.append(f"titulo LIKE '%{palabra}%' OR descripcion LIKE '%{palabra}%'")
        consulta += " OR ".join(condiciones)  # Combinar condiciones con OR

        cursor.execute(consulta)
        resultados = cursor.fetchall()

        if resultados:
            respuesta = ""  # Crear respuesta detallada
            for resultado in resultados:
                respuesta += f"Producto: {resultado[1]}\nDescripción: {resultado[2]}\nPrecio: {resultado[3]}\nLink: {resultado[4]}\n\n"
            return respuesta
        else:
            return "Lo siento, no encontré un producto relacionado con tu pregunta."

    except sqlite3.Error as e:
        return f"Ocurrió un error al buscar en la base de datos: {e}"

    finally:
        conexion.close()

# Ejemplo de uso
def main():
    print("IA de soporte para publicaciones")
    while True:
        pregunta = input("Haz tu pregunta (o escribe 'salir' para terminar): ")
        if pregunta.lower() == 'salir':
            print("Gracias por usar la IA de soporte. ¡Hasta luego!")
            break
        respuesta = buscar_producto(pregunta)
        print("\nRespuesta:\n", respuesta)

if __name__ == "__main__":
    main()
