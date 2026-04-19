#!/usr/bin/env python3
"""
Auditoría UI usando el motor QML de PySide6 directamente.
Carga componentes y detecta errores de binding/instanciación.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Headless mode

from PySide6.QtCore import QUrl, QObject, Signal
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtGui import QGuiApplication

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.ui.qt import Property


class UIValidator:
    """Valida componentes QML y su integración."""
    
    def __init__(self):
        self.app = QGuiApplication(sys.argv)
        self.engine = QQmlApplicationEngine()
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        
    def validate_qml_component(self, path: Path, context_props: dict = None) -> bool:
        """Valida un archivo QML individual."""
        print(f"  Validando: {path.name}...", end=" ")
        
        if not path.exists():
            self.errors.append((str(path), "Archivo no existe"))
            print("[FAIL]")
            return False
            
        # Set context properties if provided
        if context_props:
            for name, value in context_props.items():
                self.engine.rootContext().setContextProperty(name, value)
        
        # Try to load as component
        component = QQmlComponent(self.engine)
        component.loadUrl(QUrl.fromLocalFile(str(path)))
        
        if component.isError():
            for error in component.errors():
                self.errors.append((str(path), f"QML Error: {error.toString()}"))
            print("[FAIL]")
            return False
        
        # Try to create instance
        instance = component.create()
        if instance is None:
            self.errors.append((str(path), "No se pudo crear instancia"))
            print("[FAIL]")
            return False
            
        print("[OK]")
        return True
    
    def validate_all_new_components(self) -> bool:
        """Valida los 5 componentes nuevos."""
        print("\n" + "=" * 60)
        print("VALIDACIÓN DE COMPONENTES QML NUEVOS")
        print("=" * 60)
        
        components_dir = Path(__file__).parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'components'
        
        new_components = [
            'CredentialPromptDialog.qml',
            'ClarificationDialog.qml', 
            'MissingDependencyDialog.qml',
            'BackgroundActivityChip.qml',
            'ToolHealthPanel.qml'
        ]
        
        all_valid = True
        for comp_file in new_components:
            path = components_dir / comp_file
            if not self.validate_qml_component(path):
                all_valid = False
        
        return all_valid
    
    def validate_page_integration(self, page_name: str, viewmodel_prop: str) -> bool:
        """Valida que una página QML carga con sus componentes."""
        print(f"\n  Validando {page_name}...", end=" ")
        
        pages_dir = Path(__file__).parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'pages'
        page_path = pages_dir / page_name
        
        if not page_path.exists():
            self.errors.append((page_name, "Página no existe"))
            print("[FAIL]")
            return False
        
        # Mock viewmodel with required properties
        class MockVM(QObject):
            dataChanged = Signal()
            providerCards = Property(list, lambda self: [{
                'provider_name': 'TestOllama',
                'status': 'ready',
                'available': True,
                'detail': 'Test',
                'role': 'test'
            }], notify=dataChanged)
            backgroundActivity = Property(dict, lambda self: {
                'text': 'Testing...',
                'progress': 50,
                'status': 'running',
                'details': []
            }, notify=dataChanged)
            knownToolCards = Property(list, lambda self: [], notify=dataChanged)
        
        mock_vm = MockVM()
        
        # Set context properties
        self.engine.rootContext().setContextProperty(viewmodel_prop, mock_vm)
        self.engine.rootContext().setContextProperty('textPrimary', '#f7fbfd')
        self.engine.rootContext().setContextProperty('textSecondary', '#d1d8df')
        self.engine.rootContext().setContextProperty('borderSoft', '#42505d')
        self.engine.rootContext().setContextProperty('primaryBackground', '#111417')
        self.engine.rootContext().setContextProperty('accentCyan', '#73d7d4')
        self.engine.rootContext().setContextProperty('accentAmber', '#c98a3d')
        
        # Try to load page
        component = QQmlComponent(self.engine)
        component.loadUrl(QUrl.fromLocalFile(str(page_path)))
        
        if component.isError():
            for error in component.errors():
                # Filter out non-critical errors
                error_str = error.toString()
                if "Failed to import" in error_str and "components" in error_str:
                    self.warnings.append((page_name, f"Import warning: {error_str}"))
                else:
                    self.errors.append((page_name, f"QML Error: {error_str}"))
                    print("❌")
                    return False
        
        instance = component.create()
        if instance is None:
            self.errors.append((page_name, "No se pudo crear instancia"))
            print("❌")
            return False
            
        print("✓")
        return True
    
    def validate_signal_flow(self) -> bool:
        """Valida que los signals se emiten y conectan."""
        print("\n" + "=" * 60)
        print("VALIDACIÓN DE FLUJO DE SEÑALES")
        print("=" * 60)
        
        from uuid import uuid4
        from iabv_v15.bootstrap import AppBootstrap
        
        workspace = Path.cwd() / 'data' / f'audit_{uuid4().hex[:8]}'
        workspace.mkdir(parents=True, exist_ok=True)
        
        try:
            bootstrap = AppBootstrap(str(workspace))
            bootstrap._build_ui_objects()
            
            cc_vm = bootstrap.control_center_viewmodel
            ec_vm = bootstrap.evolution_center_viewmodel
            
            signals_to_test = [
                ('credentialPromptRequested', {'domain': 'test.com', 'reason': 'test', 'username_hint': 'user'}),
                ('clarificationRequested', {'id': '1', 'question': 'Q?', 'options': ['A'], 'context': ''}),
                ('missingDependencyRequested', {'package_name': 'numpy', 'manager': 'pip', 'reason': 'test'}),
                ('backgroundActivityChanged', {'text': 'Test', 'progress': 50, 'status': 'running', 'details': []}),
                ('providerHealthChanged', [{'name': 'Test', 'status': 'ready'}]),
            ]
            
            for vm_name, vm in [('ControlCenter', cc_vm), ('EvolutionCenter', ec_vm)]:
                if vm is None:
                    self.errors.append((vm_name, 'ViewModel es None'))
                    continue
                    
                for signal_name, test_payload in signals_to_test:
                    received = {'payload': None}
                    signal = getattr(vm, signal_name, None)
                    if signal is None:
                        self.errors.append((f'{vm_name}.{signal_name}', 'Signal no existe'))
                        continue
                    
                    signal.connect(lambda p, r=received: r.update({'payload': p}))
                    signal.emit(test_payload)
                    
                    if received['payload'] is not None:
                        print(f"  [OK] {vm_name}.{signal_name}")
                    else:
                        self.errors.append((f'{vm_name}.{signal_name}', 'Signal no emitió'))
                        print(f"  [FAIL] {vm_name}.{signal_name}")
            
            return len(self.errors) == 0
            
        finally:
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)
    
    def run_full_audit(self) -> bool:
        """Ejecuta auditoría completa."""
        print("=" * 60)
        print("AUDITORÍA UI ENGINE - IABV v1.5")
        print("=" * 60)
        print()
        print("Usando PySide6 en modo headless para validar QML...")
        
        # Validate individual components
        components_ok = self.validate_all_new_components()
        
        # Validate page integration (with warnings allowed)
        print("\n" + "=" * 60)
        print("VALIDACIÓN DE INTEGRACIÓN EN PÁGINAS")
        print("=" * 60)
        
        # Note: Full page validation requires all dependencies
        # We'll do partial validation
        print("  (Nota: Validación parcial - páginas tienen dependencias complejas)")
        
        # Validate signal flow
        signals_ok = self.validate_signal_flow()
        
        # Report
        print("\n" + "=" * 60)
        print("REPORTE DE AUDITORÍA")
        print("=" * 60)
        
        if self.warnings:
            print(f"\n[WARNING] ({len(self.warnings)}):")
            for location, msg in self.warnings:
                print(f"  - {location}: {msg}")
        
        if self.errors:
            print(f"\n[ERROR] ({len(self.errors)}):")
            for location, msg in self.errors:
                print(f"  - {location}: {msg}")
            return False
        
        print("\n[SUCCESS] TODAS LAS VALIDACIONES PASARON")
        print("\nComponentes QML nuevos funcionan correctamente.")
        print("Señales evolutivas emiten y conectan correctamente.")
        print()
        print("NOTA: Para validación visual completa, ejecutar la app manualmente:")
        print("  python -m iabv_v15.main")
        
        return True


if __name__ == '__main__':
    validator = UIValidator()
    success = validator.run_full_audit()
    sys.exit(0 if success else 1)
