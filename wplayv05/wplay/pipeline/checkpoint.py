# pipeline/checkpoint.py
import os
import json
from typing import List

class CheckpointManager:
    """
    Gestiona la creación, carga y limpieza de checkpoints de los agentes (DQN y PPO).
    Incluye metadatos de experimento y política de retención.
    """
    def __init__(self, config):
        self.checkpoint_dir = config.checkpoint_dir
        self.max_to_keep = getattr(config, 'max_checkpoints', 5)
        # metadata file to track saved checkpoints
        self.meta_file = os.path.join(self.checkpoint_dir, 'checkpoints_meta.json')
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)
        if not os.path.exists(self.meta_file):
            with open(self.meta_file, 'w') as f:
                json.dump([], f)

    def save(self, agent, step: int, metadata: dict = None) -> str:
        """
        Guarda el estado del agente en un archivo con el step y metadata opcional.
        Retorna la ruta del checkpoint.
        """
        filename = f"ckpt_{agent.__class__.__name__}_{step}.pth"
        path = os.path.join(self.checkpoint_dir, filename)
        agent.save(path)
        # actualizar metadata
        entry = {
            'path': filename,
            'agent': agent.__class__.__name__,
            'step': step,
            'metadata': metadata or {}
        }
        self._add_meta(entry)
        self._cleanup_old()
        return path

    def load(self, agent, ckpt_path: str):
        """
        Carga el checkpoint en el agente.
        """
        agent.load(ckpt_path)

    def list_checkpoints(self) -> List[str]:
        """Devuelve la lista de rutas ordenadas de checkpoints guardados."""
        with open(self.meta_file, 'r') as f:
            entries = json.load(f)
        # ordenar por step
        entries = sorted(entries, key=lambda x: x['step'])
        return [os.path.join(self.checkpoint_dir, e['path']) for e in entries]

    def _add_meta(self, entry: dict):
        """Añade una entrada al archivo metadata."""
        with open(self.meta_file, 'r+') as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

    def _cleanup_old(self):
        """Elimina checkpoints antiguos si excede max_to_keep."""
        with open(self.meta_file, 'r+') as f:
            data = json.load(f)
            if len(data) > self.max_to_keep:
                # eliminar los más antiguos
                to_remove = data[:-self.max_to_keep]
                data = data[-self.max_to_keep:]
                for entry in to_remove:
                    path = os.path.join(self.checkpoint_dir, entry['path'])
                    if os.path.exists(path):
                        os.remove(path)
                # reescribir metadata
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
