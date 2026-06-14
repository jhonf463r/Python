"""Script para verificar el dump del estado del chat en tiempo real.

Este script permite:
- Listar todos los snapshots de chat disponibles
- Ver el snapshot más reciente
- Ver un snapshot específico por ID
- Monitorear en tiempo real los nuevos snapshots

Uso:
    python scripts/verificar_chat_dump.py                    # Ver el snapshot más reciente
    python scripts/verificar_chat_dump.py --list               # Listar todos los snapshots
    python scripts/verificar_chat_dump.py --id 20260614T163045 # Ver snapshot específico
    python scripts/verificar_chat_dump.py --watch             # Monitorear en tiempo real
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def get_dump_dir() -> Path:
    """Retorna el directorio donde se guardan los dumps del chat."""
    workspace = Path(__file__).parent.parent
    return workspace / "data" / "chat_state_dumps"


def list_snapshots() -> list[dict[str, Any]]:
    """Lista todos los snapshots disponibles."""
    dump_dir = get_dump_dir()
    if not dump_dir.exists():
        print(f"Directorio de dumps no existe: {dump_dir}")
        return []
    
    snapshots = []
    for filepath in sorted(dump_dir.glob("chat_state_*.json")):
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
            print(f"Error leyendo {filepath}: {e}")
    
    return snapshots


def get_latest_snapshot() -> dict[str, Any] | None:
    """Retorna el snapshot más reciente."""
    snapshots = list_snapshots()
    if not snapshots:
        return None
    return snapshots[-1]


def load_snapshot(snapshot_id: str) -> dict[str, Any] | None:
    """Carga un snapshot específico por ID."""
    dump_dir = get_dump_dir()
    filepath = dump_dir / f"chat_state_{snapshot_id}.json"
    
    if not filepath.exists():
        print(f"Snapshot no encontrado: {filepath}")
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando snapshot: {e}")
        return None


def print_snapshot(snapshot: dict[str, Any]) -> None:
    """Imprime el contenido de un snapshot de forma legible."""
    print("=" * 80)
    print(f"Snapshot ID: {snapshot.get('snapshot_id')}")
    print(f"Timestamp: {snapshot.get('timestamp')}")
    print(f"Chat Session ID: {snapshot.get('chat_session_id')}")
    print(f"Message Count: {snapshot.get('message_count')}")
    print("=" * 80)
    
    metadata = snapshot.get("metadata", {})
    if metadata:
        print("\nMetadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    
    messages = snapshot.get("chat_messages", [])
    if messages:
        print(f"\nMensajes ({len(messages)}):")
        print("-" * 80)
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            speaker = msg.get("speaker", "unknown")
            text = msg.get("text", "")[:200]  # Truncar para legibilidad
            timestamp = msg.get("timestamp", "")
            reasoning_path = msg.get("reasoningPath", "")
            
            print(f"\n[{i}] {role.upper()} - {speaker} ({timestamp})")
            if reasoning_path:
                print(f"    Reasoning Path: {reasoning_path}")
            print(f"    Text: {text}{'...' if len(msg.get('text', '')) > 200 else ''}")
    else:
        print("\nNo hay mensajes en este snapshot.")


def watch_snapshots() -> None:
    """Monitorea en tiempo real los nuevos snapshots."""
    import time
    from datetime import datetime
    
    dump_dir = get_dump_dir()
    if not dump_dir.exists():
        print(f"Directorio de dumps no existe: {dump_dir}")
        return
    
    print("Monitoreando snapshots nuevos (Ctrl+C para salir)...")
    print(f"Directorio: {dump_dir}")
    print("=" * 80)
    
    last_snapshot_id = None
    
    try:
        while True:
            snapshots = list_snapshots()
            if snapshots:
                latest = snapshots[-1]
                latest_id = latest["snapshot_id"]
                
                if latest_id != last_snapshot_id:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Nuevo snapshot detectado:")
                    print(f"  ID: {latest_id}")
                    print(f"  Timestamp: {latest['timestamp']}")
                    print(f"  Mensajes: {latest['message_count']}")
                    
                    # Cargar y mostrar el snapshot
                    snapshot = load_snapshot(latest_id)
                    if snapshot:
                        print_snapshot(snapshot)
                    
                    last_snapshot_id = latest_id
            
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verificar dumps del estado del chat en tiempo real"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Listar todos los snapshots disponibles"
    )
    parser.add_argument(
        "--id",
        type=str,
        help="Ver un snapshot específico por ID (formato: YYYYMMDDTHHMMSS)"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Monitorear en tiempo real los nuevos snapshots"
    )
    
    args = parser.parse_args()
    
    if args.list:
        snapshots = list_snapshots()
        if not snapshots:
            print("No hay snapshots disponibles.")
            return 0
        
        print(f"Snapshots disponibles ({len(snapshots)}):")
        print("-" * 80)
        for snap in snapshots:
            print(f"  ID: {snap['snapshot_id']}")
            print(f"  Timestamp: {snap['timestamp']}")
            print(f"  Session: {snap['chat_session_id']}")
            print(f"  Mensajes: {snap['message_count']}")
            print(f"  Archivo: {snap['filepath']}")
            print("-" * 80)
        
        return 0
    
    if args.watch:
        watch_snapshots()
        return 0
    
    if args.id:
        snapshot = load_snapshot(args.id)
        if snapshot:
            print_snapshot(snapshot)
            return 0
        return 1
    
    # Por defecto, ver el snapshot más reciente
    latest = get_latest_snapshot()
    if latest:
        print(f"Snapshot más reciente: {latest['snapshot_id']}")
        snapshot = load_snapshot(latest["snapshot_id"])
        if snapshot:
            print_snapshot(snapshot)
            return 0
    else:
        print("No hay snapshots disponibles.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
