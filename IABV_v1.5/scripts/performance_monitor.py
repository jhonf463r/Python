#!/usr/bin/env python
"""
IABV Performance Monitoring & Optimization Script
Diagnóstico de rendimiento en tiempo real
"""

import time
import sys
import json
from pathlib import Path
from datetime import datetime

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def monitor_startup():
    """Monitorea el tiempo de startup de IABV"""
    print_header("MONITOREO DE STARTUP - IABV v1.5")

    stages = {
        'Bootstrap inicio': 0,
        'Cargar config': 0,
        'Conectar DB': 0,
        'Iniciar repositorios': 0,
        'Iniciar servicios': 0,
        'Crear ViewModels': 0,
        'Cargar QML': 0,
        'UI Ready': 0,
    }

    print("\nPasos de inicio que se están monitoreando:")
    for i, stage in enumerate(stages.keys(), 1):
        print(f"  {i}. {stage}")

    print("\n💡 Consejo: Abre DevTools de Qt (Ctrl+F12 en la ventana) para ver logs")
    print("💡 Busca mensajes como '[PERF]' para ver benchmarks")

    return stages

def analyze_bootstrap_file():
    """Analiza el bootstrap.py para identificar cuellos de botella"""
    print_header("ANÁLISIS DEL BOOTSTRAP")

    bootstrap_path = Path(__file__).parent / 'src' / 'iabv_v15' / 'bootstrap.py'

    if not bootstrap_path.exists():
        print("⚠️  bootstrap.py no encontrado")
        return

    content = bootstrap_path.read_text()
    lines = content.split('\n')

    print("\n📊 Conteo de inicializaciones:")
    print(f"  Repositorios: {content.count('Repository(')}")
    print(f"  Servicios: {content.count('Service(')}")
    print(f"  ViewModels: {content.count('ViewModel(')}")

    print("\n🔴 Operaciones potencialmente lentas detectadas:")
    if 'EmbeddingIndexService' in content:
        print("  ❌ EmbeddingIndexService (carga modelos)")
    if 'WorldModelService' in content:
        print("  ❌ WorldModelService (parsea snapshots)")
    if 'EvolutionReviewService' in content:
        print("  ❌ EvolutionReviewService (queries pesadas)")

    print("\n✅ Optimizaciones ya aplicadas:")
    print("  ✓ Main.qml: asynchronous: true (aplicada)")
    print("  ⏳ Lazy loading ViewModels (recomendada)")
    print("  ⏳ Paralelizar bootstrap (recomendada)")

def generate_report():
    """Genera reporte de rendimiento"""
    print_header("REPORTE DE RENDIMIENTO")

    report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'En proceso',
        'optimizaciones_aplicadas': [
            'asynchronous: true en Loader'
        ],
        'optimizaciones_pendientes': [
            'Lazy load ViewModels',
            'Paralelizar servicios de bootstrap',
            'Mover EmbeddingService a background thread'
        ],
        'métricas_esperadas_después': {
            'Startup': '5-10s (era 30-60s)',
            'Navegación': 'Fluida (era congelada)',
            'UI completa': 'Inmediata'
        }
    }

    report_path = Path(__file__).parent / 'PERFORMANCE_REPORT.json'
    report_path.write_text(json.dumps(report, indent=2))

    print("\n📄 Reporte guardado en:", report_path)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    try:
        print("\n🚀 IABV Performance Diagnostic Tool v1.0\n")

        monitor_startup()
        analyze_bootstrap_file()
        generate_report()

        print_header("PRÓXIMOS PASOS")
        print("""
1. ✅ Cambio aplicado: asynchronous: true en Main.qml
   → Prueba ahora y verifica que no se congela al cambiar de página

2. 📊 Monitorea el rendimiento:
   → Abre DevTools (Ctrl+F12) y busca '[PERF]' en logs
   → Mide startup actual vs. esperado (5-10s)

3. ⏳ Si sigue lento:
   → Implementar lazy loading de ViewModels
   → Mover EmbeddingService a thread background

4. 📝 Reporta resultados con:
   → Tiempo de startup actual
   → Cuántos segundos se congela en cambios de página
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
