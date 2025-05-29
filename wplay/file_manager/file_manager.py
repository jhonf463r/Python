import json
import os

class FileManager:
    """
    Gestión de archivos de configuración: regiones, credenciales, etc.
    """
    @staticmethod
    def get_region_storage_path(regions_file: str = None) -> str:
        """
        Devuelve la ruta donde se guarda/lee el JSON de regiones.
        Si se pasa regions_file, lo usa; si no, usa 'regions.json' en el CWD.
        """
        return regions_file or os.path.join(os.getcwd(), "regions.json")

    @staticmethod
    def load_regions(regions_file: str = None) -> dict:
        """
        Carga y retorna el dict de regiones desde JSON. Si no existe, retorna {}.
        """
        path = FileManager.get_region_storage_path(regions_file)
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def save_regions(regions_file: str, regions: dict) -> None:
        """
        Guarda el dict de regiones en JSON en la ruta indicada.
        """
        path = FileManager.get_region_storage_path(regions_file)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(regions, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_credentials(creds_file: str = None) -> tuple:
        """
        Carga credenciales desde JSON con campos 'username' y 'password'.
        Retorna (username, password) o (None, None).
        """
        path = creds_file or os.path.join(os.getcwd(), "credentials.json")
        if not os.path.isfile(path):
            return None, None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("username"), data.get("password")
        except Exception:
            return None, None

    @staticmethod
    def save_credentials(creds_file: str, username: str, password: str) -> None:
        """
        Guarda credenciales en JSON.
        """
        path = creds_file or os.path.join(os.getcwd(), "credentials.json")
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"username": username, "password": password}, f, indent=4)
