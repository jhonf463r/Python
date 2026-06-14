"""Chat State Dumper - Servicio para dump de estado del chat en tiempo real.

Este servicio permite acceder al estado actual del chat desde fuera del programa
para auditoría en tiempo real. Guarda snapshots del estado del chat en archivos JSON
que pueden ser consultados externamente.

Funcionalidades:
- Dump automático del estado del chat con cada mensaje
- Captura de reasoning paths completos
- Metadata de interacciones y decisiones
- Historial de snapshots para replay/simulación
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ChatStateDumper:
    """Servicio para dump de estado del chat en tiempo real.
    
    Este servicio captura el estado completo del chat incluyendo:
    - Todos los mensajes en memoria
    - Session ID
    - Reasoning paths
    - Metadata de interacciones
    - Timestamps
    
    Los dumps se guardan en archivos JSON que pueden ser consultados externamente.
    """
    
    def __init__(
        self,
        *,
        workspace_root: str,
        dump_dir: str | None = None,
        max_snapshots: int = 100,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        
        if dump_dir is None:
            dump_dir = self.workspace_root / "data" / "chat_state_dumps"
        self.dump_dir = Path(dump_dir)
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_snapshots = max_snapshots
        self._lock = threading.RLock()
        self._latest_snapshot: dict[str, Any] | None = None
        self._snapshot_history: list[dict[str, Any]] = []
        
        logger.info(f"Chat State Dumper initialized - dump_dir={self.dump_dir}")
    
    def dump_chat_state(
        self,
        *,
        chat_messages: list[dict[str, Any]],
        chat_session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Realiza un dump del estado actual del chat.
        
        Args:
            chat_messages: Lista de mensajes del chat en memoria
            chat_session_id: ID de la sesión de chat actual
            metadata: Metadata adicional (opcional)
            
        Returns:
            Ruta del archivo JSON donde se guardó el dump
        """
        with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            
            snapshot = {
                "snapshot_id": snapshot_id,
                "timestamp": timestamp,
                "chat_session_id": chat_session_id,
                "message_count": len(chat_messages),
                "chat_messages": chat_messages,
                "metadata": metadata or {},
            }
            
            # Guardar snapshot en archivo
            filename = f"chat_state_{snapshot_id}.json"
            filepath = self.dump_dir / filename
            
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, indent=2, ensure_ascii=False)
                
                # Actualizar latest snapshot
                self._latest_snapshot = snapshot
                
                # Agregar al historial
                self._snapshot_history.append(snapshot)
                if len(self._snapshot_history) > self.max_snapshots:
                    self._snapshot_history.pop(0)
                
                # Limpiar archivos antiguos
                self._cleanup_old_snapshots()
                
                logger.info(f"Chat state dumped to {filepath} ({len(chat_messages)} messages)")
                return str(filepath)
                
            except Exception as e:
                logger.error(f"Failed to dump chat state: {e}", exc_info=True)
                return ""
    
    def get_latest_snapshot(self) -> dict[str, Any] | None:
        """Retorna el snapshot más reciente del chat."""
        with self._lock:
            return self._latest_snapshot
    
    def get_snapshot_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna el historial de snapshots."""
        with self._lock:
            return list(self._snapshot_history[-limit:])
    
    def load_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """Carga un snapshot específico desde archivo.
        
        Args:
            snapshot_id: ID del snapshot a cargar (formato YYYYMMDDTHHMMSS)
            
        Returns:
            El snapshot cargado o None si no se encuentra
        """
        filepath = self.dump_dir / f"chat_state_{snapshot_id}.json"
        
        if not filepath.exists():
            logger.warning(f"Snapshot not found: {filepath}")
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            logger.info(f"Snapshot loaded from {filepath}")
            return snapshot
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}", exc_info=True)
            return None
    
    def list_snapshots(self) -> list[dict[str, Any]]:
        """Lista todos los snapshots disponibles."""
        snapshots = []
        
        try:
            for filepath in sorted(self.dump_dir.glob("chat_state_*.json")):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        snapshot = json.load(f)
                    snapshots.append({
                        "snapshot_id": snapshot.get("snapshot_id"),
                        "timestamp": snapshot.get("timestamp"),
                        "chat_session_id": snapshot.get("chat_session_id"),
                        "message_count": snapshot.get("message_count"),
                        "filepath": str(filepath),
                    })
                except Exception as e:
                    logger.warning(f"Failed to read snapshot {filepath}: {e}")
        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}", exc_info=True)
        
        return snapshots
    
    def _cleanup_old_snapshots(self) -> None:
        """Limpia snapshots antiguos para mantener el número máximo."""
        try:
            snapshots = list(self.dump_dir.glob("chat_state_*.json"))
            if len(snapshots) > self.max_snapshots:
                # Ordenar por fecha de modificación y eliminar los más antiguos
                snapshots.sort(key=lambda p: p.stat().st_mtime)
                for old_snapshot in snapshots[:len(snapshots) - self.max_snapshots]:
                    try:
                        old_snapshot.unlink()
                        logger.debug(f"Deleted old snapshot: {old_snapshot}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old snapshot {old_snapshot}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old snapshots: {e}")


# Singleton global para acceso desde cualquier parte del código
_chat_state_dumper: ChatStateDumper | None = None
_dumper_lock = threading.Lock()


def get_chat_state_dumper(
    *,
    workspace_root: str,
    dump_dir: str | None = None,
) -> ChatStateDumper:
    """Retorna el singleton ChatStateDumper."""
    global _chat_state_dumper
    
    with _dumper_lock:
        if _chat_state_dumper is None:
            _chat_state_dumper = ChatStateDumper(
                workspace_root=workspace_root,
                dump_dir=dump_dir,
            )
        return _chat_state_dumper


def reset_chat_state_dumper() -> None:
    """Resetea el singleton (útil para tests)."""
    global _chat_state_dumper
    with _dumper_lock:
        _chat_state_dumper = None
