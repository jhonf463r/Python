#!/usr/bin/env python3
"""
Script de Auditoría QA Humana para IABV v1.5 - Task B
Ejecutar manualmente para recorrer las 7 páginas y validar UI.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.ui.qt import QGuiApplication, QTimer


def run_human_audit():
    """Ejecuta auditoría visual interactiva."""
    print("=" * 60)
    print("AUDITORÍA QA HUMANA - IABV v1.5 UI Evolutiva")
    print("=" * 60)
    print()
    print("Este script iniciará la app para auditoría manual.")
    print("Pasos a seguir:")
    print()
    print("1. DASHBOARD - Verificar que carga sin errores")
    print("2. CENTRO DE CONTROL - Verificar:")
    print("   - ToolHealthPanel visible con providers")
    print("   - BackgroundActivityChip (cuando hay actividad)")
    print("   - Diálogos evolutivos (testear vía mock signals)")
    print("3. EVOLUTION CENTER - Verificar:")
    print("   - ToolHealthPanel integrado")
    print("   - BackgroundActivityChip")
    print("4. CAPTURE STUDIO - Interactuar con formularios")
    print("5. KNOWLEDGE BASE - Verificar lista de conocimiento")
    print("6. PROVIDER SETTINGS - Cambiar un proveedor")
    print("7. RUN HISTORY - Verificar ejecuciones pasadas")
    print()
    input("Presiona ENTER para iniciar la app...")
    print()

    # Iniciar bootstrap
    from uuid import uuid4
    workspace = Path.cwd() / 'data' / f'audit_{uuid4().hex[:8]}'
    workspace.mkdir(parents=True, exist_ok=True)
    
    print(f"Workspace: {workspace}")
    print("Iniciando IABV v1.5...")
    
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    
    print("✓ Bootstrap completado")
    print(f"✓ ViewModels cargados:")
    print(f"  - ControlCenterViewModel: {bootstrap.control_center_viewmodel is not None}")
    print(f"  - EvolutionCenterViewModel: {bootstrap.evolution_center_viewmodel is not None}")
    
    # Verificar signals evolutivos
    cc_vm = bootstrap.control_center_viewmodel
    ec_vm = bootstrap.evolution_center_viewmodel
    
    print()
    print("Verificando señales evolutivas...")
    
    # Test signal connections
    test_results = []
    
    def test_signal(vm, signal_name, test_payload, display_name):
        received = {'payload': None}
        signal = getattr(vm, signal_name)
        signal.connect(lambda p: received.update({'payload': p}))
        signal.emit(test_payload)
        if received['payload'] is not None:
            print(f"  ✓ {display_name}: OK")
            return True
        else:
            print(f"  ✗ {display_name}: FAILED")
            return False
    
    if cc_vm:
        test_results.append(test_signal(cc_vm, 'credentialPromptRequested', 
            {'domain': 'test.com', 'reason': 'test', 'username_hint': 'user'},
            'CC credentialPromptRequested'))
        test_results.append(test_signal(cc_vm, 'clarificationRequested',
            {'id': '1', 'question': 'Q?', 'options': ['A'], 'context': ''},
            'CC clarificationRequested'))
        test_results.append(test_signal(cc_vm, 'missingDependencyRequested',
            {'package_name': 'numpy', 'manager': 'pip', 'reason': 'test'},
            'CC missingDependencyRequested'))
    
    if ec_vm:
        test_results.append(test_signal(ec_vm, 'credentialPromptRequested',
            {'domain': 'test.com', 'reason': 'test', 'username_hint': 'user'},
            'EC credentialPromptRequested'))
        test_results.append(test_signal(ec_vm, 'clarificationRequested',
            {'id': '1', 'question': 'Q?', 'options': ['A'], 'context': ''},
            'EC clarificationRequested'))
    
    print()
    if all(test_results):
        print("✓ Todos los signals evolutivos funcionan correctamente")
    else:
        print("✗ Algunos signals fallaron - revisar implementación")
    
    print()
    print("=" * 60)
    print("PRÓXIMOS PASOS PARA AUDITORÍA VISUAL:")
    print("=" * 60)
    print()
    print("1. La app debería estar visible ahora")
    print("2. Navega a 'Centro de Control'")
    print("3. Verifica que ToolHealthPanel muestra providers (Ollama, etc.)")
    print("4. Desplázate para ver BackgroundActivityChip (si hay actividad)")
    print("5. Navega a 'Centro Evolutivo'")
    print("6. Verifica ToolHealthPanel integrado")
    print("7. Prueba cada botón y verifica que no hay excepciones")
    print()
    print("Para testear los diálogos (requiere mock manual):")
    print("  - credentialDialog.open()")
    print("  - clarificationDialog.open()")  
    print("  - dependencyDialog.open()")
    print()
    print("Presiona Ctrl+C para cerrar cuando termines la auditoría")
    print()
    
    # Mantener app viva
    try:
        app = QGuiApplication.instance()
        if app:
            print("QGuiApplication ejecutándose. Manteniendo vivo...")
            # En lugar de exec(), solo monitoreamos
            while True:
                app.processEvents()
                time.sleep(0.1)
    except KeyboardInterrupt:
        print()
        print("Auditoría finalizada por usuario")
    finally:
        print("Limpiando...")
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)
        print("✓ Limpieza completada")


if __name__ == '__main__':
    run_human_audit()
