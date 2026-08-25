"""Limits Awareness — metacognición profunda de lo que NO puede ver.

El programa debe saber qué está fuera de su alcance, qué no puede
observar, y reportarlo honestamente en vez de ignorarlo.

Categoriza los límites en:
  1. Hardware limits: sensores no accesibles, periféricos sin driver
  2. Software limits: APIs sin credenciales, programas no instalados
  3. Perception limits: monitores que no ve, procesos ocultos, red interna
  4. Knowledge limits: documentación no leída, patrones no aprendidos
  5. Autonomy limits: acciones que requieren aprobación humana
  6. Temporal limits: información que caduca, estados transitorios

Para cada límite identifica:
  - Qué no puede ver/hacer
  - Por qué (falta driver, credencial, permiso, etc.)
  - Impacto (qué decisiones podrían ser incorrectas por este blind spot)
  - Posible solución (instalar X, pedir permiso, etc.)
"""

from __future__ import annotations

import importlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _check_importable(module: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


def _check_command(cmd: str) -> bool:
    """Check if a command is available in PATH."""
    try:
        r = subprocess.run(
            ['which', cmd] if os.name != 'nt' else ['where', cmd],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# Hardware Limits
# ──────────────────────────────────────────────────────────────

def scan_hardware_limits() -> list[dict[str, Any]]:
    """Detect hardware-related blind spots."""
    limits: list[dict[str, Any]] = []

    # GPU — can we query NVIDIA?
    if not _check_command('nvidia-smi'):
        limits.append({
            'category': 'hardware',
            'blind_spot': 'GPU NVIDIA no accesible via nvidia-smi',
            'impact': 'No puede verificar qué GPU usa Ollama ni el estado de VRAM',
            'solution': 'Instalar NVIDIA drivers con nvidia-smi incluido',
            'severity': 'high',
        })

    # Temperature sensors
    if os.name != 'nt':
        if not _check_command('sensors'):
            limits.append({
                'category': 'hardware',
                'blind_spot': 'Temperatura del CPU/GPU no accesible',
                'impact': 'No puede detectar throttling térmico',
                'solution': 'Instalar lm-sensors: sudo apt install lm-sensors',
                'severity': 'medium',
            })
    else:
        # Windows: WMI temperature is unreliable without OpenHardwareMonitor
        limits.append({
            'category': 'hardware',
            'blind_spot': 'Temperatura precisa del CPU/GPU no accesible en Windows sin OpenHardwareMonitor',
            'impact': 'No puede detectar throttling térmico fino',
            'solution': 'Instalar OpenHardwareMonitor o HWiNFO para lectura precisa',
            'severity': 'low',
        })

    # Battery — only relevant for laptops
    if os.name == 'nt':
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '(Get-CimInstance Win32_Battery).EstimatedChargeRemaining'],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0 or not r.stdout.strip():
                limits.append({
                    'category': 'hardware',
                    'blind_spot': 'Estado de batería no disponible',
                    'impact': 'No puede alertar sobre batería baja durante tareas largas',
                    'solution': 'Verificar que WMI Battery class está disponible',
                    'severity': 'low',
                })
        except Exception:
            pass

    return limits


# ──────────────────────────────────────────────────────────────
# Software Limits
# ──────────────────────────────────────────────────────────────

def scan_software_limits() -> list[dict[str, Any]]:
    """Detect software-related blind spots."""
    limits: list[dict[str, Any]] = []

    # Python libraries that expand capabilities
    optional_libs = [
        ('psutil', 'Monitoreo detallado de procesos, CPU, memoria, disco',
         'pip install psutil', 'medium'),
        ('playwright', 'Automatización de navegador headless para consultas autónomas',
         'pip install playwright && playwright install', 'high'),
        ('PIL', 'Procesamiento de imágenes/screenshots para percepción visual',
         'pip install Pillow', 'medium'),
        ('cv2', 'Visión por computadora para análisis de pantalla avanzado',
         'pip install opencv-python', 'low'),
    ]
    for mod, desc, install, sev in optional_libs:
        if not _check_importable(mod):
            limits.append({
                'category': 'software',
                'blind_spot': f'Librería {mod} no disponible — {desc}',
                'impact': f'Funcionalidad limitada: {desc.lower()}',
                'solution': install,
                'severity': sev,
            })

    # External tools
    optional_tools = [
        ('docker', 'Contenedores para sandbox aislado', 'medium'),
        ('node', 'Runtime para herramientas JavaScript/MCP', 'low'),
        ('ffmpeg', 'Procesamiento de audio/video', 'low'),
    ]
    for tool, desc, sev in optional_tools:
        if not _check_command(tool):
            limits.append({
                'category': 'software',
                'blind_spot': f'{tool} no instalado — {desc}',
                'impact': f'No puede usar {desc.lower()}',
                'solution': f'Instalar {tool}',
                'severity': sev,
            })

    return limits


# ──────────────────────────────────────────────────────────────
# Perception Limits
# ──────────────────────────────────────────────────────────────

def scan_perception_limits(
    monitor_count: int = 1,
    environment_scan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Detect perception-related blind spots."""
    limits: list[dict[str, Any]] = []
    env = environment_scan or {}

    # Multi-monitor blind spot
    if monitor_count > 1:
        limits.append({
            'category': 'perception',
            'blind_spot': f'{monitor_count} monitores pero solo puede interactuar con el principal',
            'impact': 'Ventanas en monitores secundarios son invisibles para automatización',
            'solution': 'Mover ventanas al monitor principal antes de interactuar, o usar APIs headless',
            'severity': 'high',
        })

    # Network — internal network not scannable
    limits.append({
        'category': 'perception',
        'blind_spot': 'Red interna: no escanea otros dispositivos en la LAN',
        'impact': 'No sabe qué otros servicios/servidores están disponibles en la red local',
        'solution': 'Implementar scan ARP o mDNS para descubrir dispositivos locales',
        'severity': 'low',
    })

    # Clipboard — cannot read/write clipboard reliably cross-platform
    limits.append({
        'category': 'perception',
        'blind_spot': 'Contenido del portapapeles no es observable',
        'impact': 'No puede verificar qué copió el usuario ni el resultado de operaciones de copia',
        'solution': 'Usar pyperclip o win32clipboard para leer/escribir portapapeles',
        'severity': 'low',
    })

    # Audio — cannot hear or process audio
    limits.append({
        'category': 'perception',
        'blind_spot': 'Audio: no puede escuchar ni procesar audio del sistema',
        'impact': 'No puede detectar notificaciones sonoras, errores con alerta auditiva',
        'solution': 'Integrar captura de audio con pyaudio + speech recognition',
        'severity': 'low',
    })

    return limits


# ──────────────────────────────────────────────────────────────
# Knowledge Limits
# ──────────────────────────────────────────────────────────────

def scan_knowledge_limits(workspace: str | None = None) -> list[dict[str, Any]]:
    """Detect knowledge gaps based on available documentation and patterns."""
    limits: list[dict[str, Any]] = []
    ws = workspace or os.environ.get('IABV_WORKSPACE', '')
    if not ws:
        ws = str(Path(__file__).resolve().parents[3])

    # Check test coverage — if no coverage report, we don't know what's tested
    coverage_file = Path(ws) / '.coverage'
    coverage_html = Path(ws) / 'htmlcov'
    if not coverage_file.exists() and not coverage_html.exists():
        limits.append({
            'category': 'knowledge',
            'blind_spot': 'No hay reporte de cobertura de tests — no sabe qué código está probado',
            'impact': 'No puede priorizar tests ni detectar código no cubierto',
            'solution': 'Correr pytest --cov y generar reporte HTML',
            'severity': 'medium',
        })

    # Check if portable context exists
    ctx_path = Path(ws) / 'data' / 'evolution' / 'portable_context' / 'latest.json'
    if not ctx_path.exists():
        limits.append({
            'category': 'knowledge',
            'blind_spot': 'No hay contexto portable persistido — aprendizaje no acumulativo',
            'impact': 'Cada sesión empieza de cero sin aprendizaje de sesiones anteriores',
            'solution': 'Ejecutar PortableContextService.export_package()',
            'severity': 'high',
        })

    # Check if documentation for key tools exists
    docs_dir = Path(ws) / 'docs'
    if not docs_dir.exists() or len(list(docs_dir.glob('*.md'))) < 3:
        limits.append({
            'category': 'knowledge',
            'blind_spot': 'Documentación limitada del proyecto — auto-descubrimiento parcial',
            'impact': 'Nuevos agentes tardan más en entender la arquitectura',
            'solution': 'Generar documentación automática desde docstrings y AGENTS.md',
            'severity': 'low',
        })

    return limits


# ──────────────────────────────────────────────────────────────
# Autonomy Limits
# ──────────────────────────────────────────────────────────────

def scan_autonomy_limits() -> list[dict[str, Any]]:
    """Detect actions that the program cannot do without human approval."""
    return [
        {
            'category': 'autonomy',
            'blind_spot': 'No puede auto-mergear PRs que tocan contratos o capas cerradas (P1-P4)',
            'impact': 'Requiere aprobación humana para cambios arquitectónicos',
            'solution': 'Diseñado así — no debe cambiarse. Documentar para transparencia',
            'severity': 'info',
        },
        {
            'category': 'autonomy',
            'blind_spot': 'No puede instalar software con permisos de administrador',
            'impact': 'Herramientas que requieren admin no pueden instalarse automáticamente',
            'solution': 'Pedir al usuario que instale con admin o usar versiones portable',
            'severity': 'medium',
        },
        {
            'category': 'autonomy',
            'blind_spot': 'No puede observar ventanas externas sin permiso explícito del usuario',
            'impact': 'Estado real de herramientas web (ChatGPT, etc.) es UNRESOLVED hasta verificar',
            'solution': 'Seguir política de observación: pedir permiso antes de observar ventanas',
            'severity': 'info',
        },
    ]


# ──────────────────────────────────────────────────────────────
# Full Limits Awareness Report
# ──────────────────────────────────────────────────────────────

def limits_awareness_scan(
    *,
    monitor_count: int = 1,
    environment_scan: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    """Full scan of all known limits and blind spots."""
    hardware = scan_hardware_limits()
    software = scan_software_limits()
    perception = scan_perception_limits(monitor_count, environment_scan)
    knowledge = scan_knowledge_limits(workspace)
    autonomy = scan_autonomy_limits()

    all_limits = hardware + software + perception + knowledge + autonomy
    by_severity: dict[str, int] = {}
    for lim in all_limits:
        sev = lim.get('severity', 'unknown')
        by_severity[sev] = by_severity.get(sev, 0) + 1

    by_category: dict[str, int] = {}
    for lim in all_limits:
        cat = lim.get('category', 'unknown')
        by_category[cat] = by_category.get(cat, 0) + 1

    actionable = [l for l in all_limits if l.get('severity') in ('high', 'medium')]
    informational = [l for l in all_limits if l.get('severity') in ('low', 'info')]

    return {
        'limits': all_limits,
        'total_count': len(all_limits),
        'by_severity': by_severity,
        'by_category': by_category,
        'actionable': actionable,
        'actionable_count': len(actionable),
        'informational': informational,
        'informational_count': len(informational),
    }


def format_limits_report(scan: dict[str, Any]) -> str:
    """Format limits awareness scan for the auto-analysis report."""
    lines: list[str] = ['== METACOGNICION: LIMITES Y BLIND SPOTS ==']

    total = scan.get('total_count', 0)
    actionable = scan.get('actionable_count', 0)
    lines.append(f'  Limites conocidos: {total} ({actionable} accionables)')

    # Group by category
    by_cat = scan.get('by_category', {})
    if by_cat:
        cats = ', '.join(f'{k}: {v}' for k, v in sorted(by_cat.items()))
        lines.append(f'  Por categoría: {cats}')

    # Show actionable limits (high + medium severity)
    actionable_limits = scan.get('actionable', [])
    if actionable_limits:
        lines.append('  Accionables:')
        for lim in actionable_limits[:8]:
            sev = lim.get('severity', '?').upper()
            lines.append(f'    [{sev}] {lim["blind_spot"]}')
            lines.append(f'      Solución: {lim["solution"]}')

    # Informational — just count
    info_count = scan.get('informational_count', 0)
    if info_count > 0:
        lines.append(f'  Informativos: {info_count} (limitaciones de diseño o baja prioridad)')

    return '\n'.join(lines)
