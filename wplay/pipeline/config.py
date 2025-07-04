# pipeline/config.py
"""
ConfigManager: clase para cargar y validar configuración desde un archivo YAML,
proporciona atributos de configuración organizados por secciones.
"""
import os
import yaml

class ConfigManager:
    """
    Gestiona la carga y validación de la configuración del experimento.
    """
    REQUIRED_SECTIONS = [
        'auth', 'chrome', 'data', 'feature', 'env',
        'strategy', 'trainer', 'log_dir', 'checkpoint_dir',
        'eval_episodes', 'visualization'
    ]

    def __init__(self, config_path: str):
        """
        Args:
            config_path (str): ruta al archivo YAML de configuración.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
        self._validate()
        self._set_attributes()

    def _validate(self):
        """
        Verifica que todas las secciones requeridas estén presentes en la configuración.
        """
        missing = [sec for sec in self.REQUIRED_SECTIONS if sec not in self._config]
        if missing:
            raise KeyError(f"Missing configuration sections: {missing}")

    def _set_attributes(self):
        """
        Asigna cada sección del config como atributo del objeto.
        """
        for key, value in self._config.items():
            setattr(self, key, value)

    def get(self, section: str, default=None):
        """
        Obtiene una sección específica de la configuración.

        Args:
            section (str): nombre de la sección.
            default: valor por defecto si no existe.
        """
        return self._config.get(section, default)

    def save(self, output_path: str):
        """
        Guarda la configuración actual en un archivo YAML.

        Args:
            output_path (str): ruta de salida para el YAML.
        """
        with open(output_path, 'w') as f:
            yaml.safe_dump(self._config, f)

# Ejemplo de uso:
# from pipeline.config import ConfigManager
# cfg = ConfigManager('config.yaml')
# print(cfg.strategy)

