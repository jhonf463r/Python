import sqlite3

DB_PATH = r"C:\Users\faber\Documents\Python\ChatBot\publicaciones_tienda.db"

def obtener_id_por_titulo(titulo):
    # Se usa rowid porque la tabla no tiene una columna "id" explícita.
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
