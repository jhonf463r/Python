"""Servicio de salud GPU con metacognicion e introspeccion.

El programa DEBE saber:
1. Que GPUs fisicas tiene el sistema (nvidia-smi -L)
2. Cual GPU esta usando Ollama REALMENTE (ollama ps + logs)
3. Si el modelo cabe 100% en esa GPU
4. Si Ollama esta usando la GPU EQUIVOCADA (integrada vs discreta)
5. Corregirlo automaticamente si es necesario

Lecciones aprendidas (2026-04-23 — RTX 4050 Laptop):
- nvidia-smi reporta picos que no reflejan uso real en Task Manager
- `ollama ps` muestra % CPU/GPU pero NO dice cual GPU fisica usa
- Ollama logs muestran "inference compute: CUDA0 <nombre>" = verdad
- En laptops con 2 GPUs (Intel + NVIDIA), Ollama puede usar la equivocada
- El disco al 100% = modelo NO esta en GPU, carga desde RAM/disco
- CUDA_VISIBLE_DEVICES controla cual GPU usa CUDA/Ollama
"""
from __future__ import annotations

import logging
import os
import subprocess
import re
import json as _json
import time as _time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PhysicalGpu:
    index: int
    name: str
    vram_total_mb: int
    vram_used_mb: int
    vram_free_mb: int
    gpu_type: str  # 'discrete' or 'integrated'
    driver: str = ''
    pci_id: str = ''


@dataclass
class OllamaGpuState:
    """Lo que Ollama realmente esta usando."""
    cuda_device_name: str = ''  # from ollama logs or /api/ps
    cuda_device_index: int = -1
    vram_available_gb: float = 0.0
    using_correct_gpu: bool = False
    models_loaded: list[dict] = field(default_factory=list)


@dataclass
class GpuMetacognition:
    """Resultado de la introspeccion completa del sistema GPU."""
    physical_gpus: list[PhysicalGpu]
    discrete_gpu: PhysicalGpu | None  # La GPU que DEBERIA usarse
    integrated_gpu: PhysicalGpu | None  # La GPU que NO deberia usarse para LLM
    ollama_state: OllamaGpuState
    healthy: bool
    problems: list[str]
    actions_taken: list[str]
    recommendation: str


def detect_physical_gpus() -> list[PhysicalGpu]:
    """Detecta TODAS las GPUs fisicas del sistema."""
    gpus: list[PhysicalGpu] = []

    # nvidia-smi para GPUs NVIDIA
    try:
        nv = subprocess.run(
            ['nvidia-smi', '-L'],
            capture_output=True, text=True, timeout=5,
        )
        if nv.returncode == 0:
            for line in nv.stdout.strip().splitlines():
                # "GPU 0: NVIDIA GeForce RTX 4050 Laptop GPU (UUID: ...)"
                match = re.match(r'GPU (\d+): (.+?)\s*\(UUID:', line)
                if match:
                    idx = int(match.group(1))
                    name = match.group(2).strip()
                    gpu_type = 'integrated' if 'Intel' in name or 'UHD' in name or 'Iris' in name else 'discrete'
                    gpus.append(PhysicalGpu(
                        index=idx, name=name, vram_total_mb=0, vram_used_mb=0,
                        vram_free_mb=0, gpu_type=gpu_type,
                    ))
    except Exception as e:
        logger.debug(f'nvidia-smi -L failed: {e}')

    # Obtener VRAM de cada GPU NVIDIA
    try:
        nv2 = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,memory.free,driver_version,pci.bus_id',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5,
        )
        if nv2.returncode == 0:
            for line in nv2.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 7:
                    idx = int(parts[0])
                    for g in gpus:
                        if g.index == idx:
                            g.vram_total_mb = int(parts[2])
                            g.vram_used_mb = int(parts[3])
                            g.vram_free_mb = int(parts[4])
                            g.driver = parts[5]
                            g.pci_id = parts[6]
    except Exception:
        pass

    # Si no encontramos GPUs con nvidia-smi, intentar wmic (Windows)
    if not gpus:
        try:
            wmic = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'Name', '/format:list'],
                capture_output=True, text=True, timeout=5,
            )
            if wmic.returncode == 0:
                for line in wmic.stdout.splitlines():
                    if line.startswith('Name='):
                        name = line.split('=', 1)[1].strip()
                        if name:
                            gpu_type = 'integrated' if any(k in name for k in ['Intel', 'UHD', 'Iris', 'Radeon Graphics']) else 'discrete'
                            gpus.append(PhysicalGpu(
                                index=len(gpus), name=name, vram_total_mb=0,
                                vram_used_mb=0, vram_free_mb=0, gpu_type=gpu_type,
                            ))
        except Exception:
            pass

    return gpus


def detect_ollama_gpu_state(ollama_base: str = 'http://127.0.0.1:11434') -> OllamaGpuState:
    """Detecta que GPU esta usando Ollama REALMENTE."""
    import httpx

    state = OllamaGpuState()

    # 1. ollama ps — modelos cargados y % CPU/GPU
    try:
        ps = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
        if ps.returncode == 0:
            for line in ps.stdout.splitlines()[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                name = parts[0] if parts else ''
                gpu_pct = 0
                cpu_pct = 0
                if '100% GPU' in line:
                    gpu_pct = 100
                elif '100% CPU' in line:
                    cpu_pct = 100
                else:
                    m = re.search(r'(\d+)%/(\d+)%\s+CPU/GPU', line)
                    if m:
                        cpu_pct = int(m.group(1))
                        gpu_pct = int(m.group(2))
                state.models_loaded.append({
                    'name': name, 'gpu_percent': gpu_pct, 'cpu_percent': cpu_pct,
                    'fits_gpu': gpu_pct == 100,
                })
    except Exception:
        pass

    # 2. API /api/ps — VRAM info
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f'{ollama_base}/api/ps')
            if r.status_code == 200:
                for m in r.json().get('models', []):
                    name = m.get('name', '')
                    vram = m.get('size_vram', 0) / 1e9
                    total = m.get('size', 0) / 1e9
                    for loaded in state.models_loaded:
                        if loaded['name'] == name or name.startswith(loaded['name'].split(':')[0]):
                            loaded['vram_gb'] = round(vram, 2)
                            loaded['total_gb'] = round(total, 2)
    except Exception:
        pass

    return state


def introspect_gpu(ollama_base: str = 'http://127.0.0.1:11434') -> GpuMetacognition:
    """Introspeccion completa: detectar, analizar, diagnosticar, recomendar."""
    problems: list[str] = []
    actions: list[str] = []

    # 1. Detectar GPUs fisicas
    gpus = detect_physical_gpus()
    discrete = next((g for g in gpus if g.gpu_type == 'discrete'), None)
    integrated = next((g for g in gpus if g.gpu_type == 'integrated'), None)

    logger.info(f'gpu_metacognition: {len(gpus)} GPUs detectadas')
    for g in gpus:
        logger.info(f'  GPU {g.index}: {g.name} ({g.gpu_type}) — VRAM: {g.vram_total_mb}MB')

    if not discrete:
        problems.append('No se detecto GPU discreta (NVIDIA). Ollama correra en CPU.')

    # 2. Detectar que usa Ollama
    ollama_state = detect_ollama_gpu_state(ollama_base)

    # 3. Analizar problemas
    for model in ollama_state.models_loaded:
        if not model.get('fits_gpu', False):
            gpu_pct = model.get('gpu_percent', 0)
            cpu_pct = model.get('cpu_percent', 0)
            total_gb = model.get('total_gb', 0)
            problems.append(
                f'Modelo {model["name"]} NO cabe 100% en GPU: '
                f'{cpu_pct}% CPU / {gpu_pct}% GPU (total: {total_gb}GB). '
                f'Disco al 100% probable.'
            )

    # 4. Verificar si hay GPU discreta pero modelos corren en CPU
    if discrete and ollama_state.models_loaded:
        all_cpu = all(m.get('cpu_percent', 0) >= 50 for m in ollama_state.models_loaded)
        if all_cpu:
            problems.append(
                f'GPU discreta {discrete.name} disponible pero modelos corren mayormente en CPU. '
                f'Posible causa: CUDA_VISIBLE_DEVICES incorrecto o Ollama usando GPU integrada.'
            )

    # 5. Auto-correccion: descargar modelos que no caben
    import httpx
    for model in ollama_state.models_loaded:
        if not model.get('fits_gpu', False) and model.get('gpu_percent', 0) < 95:
            model_name = model['name']
            try:
                with httpx.Client(timeout=15) as c:
                    c.post(f'{ollama_base}/api/generate',
                           json={'model': model_name, 'keep_alive': 0}, timeout=15)
                actions.append(f'Auto-descargado {model_name} (no cabe 100% en GPU)')
                logger.warning(f'gpu_metacognition: auto-descargado {model_name}')
            except Exception as e:
                logger.error(f'gpu_metacognition: error descargando {model_name}: {e}')

    # 6. Recomendacion
    healthy = len(problems) == 0
    if healthy:
        recommendation = 'GPU saludable — todos los modelos corren 100% en GPU discreta.'
    elif discrete:
        max_model_gb = int(discrete.vram_total_mb * 0.85 / 1024)
        recommendation = (
            f'Usar solo modelos <= {max_model_gb}GB para 100% GPU en {discrete.name} '
            f'({discrete.vram_total_mb}MB VRAM). '
            f'Modelos recomendados: gemma3:4b (3.3GB), qwen2.5-coder:7b (4.7GB).'
        )
    else:
        recommendation = 'Sin GPU discreta. Instalar CUDA y drivers NVIDIA.'

    return GpuMetacognition(
        physical_gpus=gpus,
        discrete_gpu=discrete,
        integrated_gpu=integrated,
        ollama_state=ollama_state,
        healthy=healthy,
        problems=problems,
        actions_taken=actions,
        recommendation=recommendation,
    )


def gpu_metacognition_report(ollama_base: str = 'http://127.0.0.1:11434') -> str:
    """Genera un reporte legible de la introspeccion GPU."""
    meta = introspect_gpu(ollama_base)

    lines = ['=== INTROSPECCION GPU ===']
    lines.append(f'GPUs fisicas: {len(meta.physical_gpus)}')
    for g in meta.physical_gpus:
        marker = ' [DISCRETA]' if g.gpu_type == 'discrete' else ' [INTEGRADA]'
        lines.append(f'  GPU {g.index}: {g.name}{marker} — VRAM: {g.vram_total_mb}MB (usado: {g.vram_used_mb}MB)')

    lines.append(f'\nModelos Ollama cargados: {len(meta.ollama_state.models_loaded)}')
    for m in meta.ollama_state.models_loaded:
        fits = 'OK' if m.get('fits_gpu') else 'NO CABE'
        lines.append(f'  {m["name"]}: {m.get("gpu_percent",0)}% GPU / {m.get("cpu_percent",0)}% CPU [{fits}]')

    if meta.problems:
        lines.append(f'\nPROBLEMAS ({len(meta.problems)}):')
        for p in meta.problems:
            lines.append(f'  ! {p}')

    if meta.actions_taken:
        lines.append(f'\nACCIONES TOMADAS:')
        for a in meta.actions_taken:
            lines.append(f'  > {a}')

    lines.append(f'\nSALUD: {"OK" if meta.healthy else "PROBLEMAS DETECTADOS"}')
    lines.append(f'RECOMENDACION: {meta.recommendation}')

    return '\n'.join(lines)
