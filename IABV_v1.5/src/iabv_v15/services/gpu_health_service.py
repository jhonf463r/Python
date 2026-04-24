"""Servicio de salud GPU — verifica estado REAL usando ollama ps.

NO confiar solo en nvidia-smi. La verdad absoluta es `ollama ps` que muestra
el % real CPU/GPU de cada modelo cargado.

Lecciones aprendidas (2026-04-23):
- nvidia-smi reporta picos de milisegundos que no reflejan uso real
- El Admin de Tareas de Windows promedia por segundo
- Disco al 100% = Ollama cargando/descargando modelos, GPU ociosa
- gpt-oss:20b (14GB) en RTX 4050 (6GB) = 61% CPU / 39% GPU = INACEPTABLE
- gemma3:4b (4.3GB) en RTX 4050 (6GB) = 100% GPU = CORRECTO
"""
from __future__ import annotations

import logging
import subprocess
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelGpuStatus:
    name: str
    size_gb: float
    processor: str  # e.g. "100% GPU", "61%/39% CPU/GPU"
    gpu_percent: int
    cpu_percent: int
    fits_in_gpu: bool
    context: int = 0


@dataclass
class GpuHealth:
    gpu_name: str
    vram_total_mb: int
    vram_used_mb: int
    vram_free_mb: int
    loaded_models: list[ModelGpuStatus]
    healthy: bool
    warnings: list[str]
    recommendation: str


def parse_ollama_ps(output: str) -> list[ModelGpuStatus]:
    """Parsea la salida de `ollama ps` para obtener el % real CPU/GPU."""
    models = []
    lines = output.strip().splitlines()
    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue
        # Format: NAME  ID  SIZE  PROCESSOR  CONTEXT  UNTIL
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[0]
        # Find SIZE (e.g. "4.3 GB" or "14 GB")
        size_gb = 0.0
        processor = ''
        context = 0
        for i, p in enumerate(parts):
            if p == 'GB' and i > 0:
                try:
                    size_gb = float(parts[i - 1])
                except ValueError:
                    pass
            if 'GPU' in p or 'CPU' in p:
                # Processor field: "100% GPU" or "61%/39% CPU/GPU"
                if '/' in parts[i - 1] if i > 0 else False:
                    processor = f'{parts[i - 1]} {p}'
                elif '%' in (parts[i - 1] if i > 0 else ''):
                    processor = f'{parts[i - 1]} {p}'
                elif '%' in p:
                    processor = p

        # Parse GPU/CPU percentages
        gpu_pct = 0
        cpu_pct = 0
        if '100% GPU' in line:
            gpu_pct = 100
            cpu_pct = 0
        elif '100% CPU' in line:
            gpu_pct = 0
            cpu_pct = 100
        else:
            # Pattern: "XX%/YY% CPU/GPU"
            match = re.search(r'(\d+)%/(\d+)%\s+CPU/GPU', line)
            if match:
                cpu_pct = int(match.group(1))
                gpu_pct = int(match.group(2))
            else:
                match = re.search(r'(\d+)%/(\d+)%\s+GPU/CPU', line)
                if match:
                    gpu_pct = int(match.group(1))
                    cpu_pct = int(match.group(2))

        fits = gpu_pct == 100

        models.append(ModelGpuStatus(
            name=name,
            size_gb=size_gb,
            processor=processor,
            gpu_percent=gpu_pct,
            cpu_percent=cpu_pct,
            fits_in_gpu=fits,
            context=context,
        ))
    return models


def check_gpu_health(ollama_base: str = 'http://127.0.0.1:11434') -> GpuHealth:
    """Verifica salud GPU REAL usando ollama ps + nvidia-smi."""
    warnings: list[str] = []
    gpu_name = 'desconocida'
    vram_total = 0
    vram_used = 0
    vram_free = 0

    # 1. nvidia-smi para VRAM info
    try:
        nv = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5,
        )
        if nv.returncode == 0:
            parts = [p.strip() for p in nv.stdout.strip().split(',')]
            gpu_name = parts[0]
            vram_total = int(parts[1])
            vram_used = int(parts[2])
            vram_free = int(parts[3])
    except Exception as e:
        warnings.append(f'nvidia-smi fallo: {e}')

    # 2. ollama ps — LA VERDAD ABSOLUTA
    loaded_models: list[ModelGpuStatus] = []
    try:
        ps = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
        if ps.returncode == 0:
            loaded_models = parse_ollama_ps(ps.stdout)
            logger.info(f'gpu_health: ollama ps -> {len(loaded_models)} modelos cargados')
        else:
            warnings.append(f'ollama ps fallo: {ps.stderr[:200]}')
    except FileNotFoundError:
        # Fallback: usar API
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(f'{ollama_base}/api/ps')
                if r.status_code == 200:
                    for m in r.json().get('models', []):
                        name = m.get('name', '')
                        size = m.get('size', 0) / 1e9
                        vram = m.get('size_vram', 0) / 1e9
                        gpu_pct = int((vram / size) * 100) if size > 0 else 0
                        cpu_pct = 100 - gpu_pct
                        loaded_models.append(ModelGpuStatus(
                            name=name, size_gb=round(size, 2),
                            processor=f'{cpu_pct}%/{gpu_pct}% CPU/GPU' if gpu_pct < 100 else '100% GPU',
                            gpu_percent=gpu_pct, cpu_percent=cpu_pct,
                            fits_in_gpu=(gpu_pct >= 95),
                        ))
        except Exception as e:
            warnings.append(f'ollama API fallo: {e}')
    except Exception as e:
        warnings.append(f'ollama ps error: {e}')

    # 3. Analizar problemas
    for model in loaded_models:
        if not model.fits_in_gpu:
            warnings.append(
                f'MODELO NO CABE EN GPU: {model.name} ({model.size_gb}GB) '
                f'corre {model.cpu_percent}% CPU / {model.gpu_percent}% GPU. '
                f'Disco al 100%% probable. Recomendacion: descargar con '
                f'"ollama stop {model.name}" y usar un modelo mas pequeno.'
            )
            logger.warning(f'gpu_health: {model.name} NO cabe en GPU — {model.processor}')

    if vram_free < 500 and vram_total > 0:
        warnings.append(
            f'VRAM casi llena: {vram_used}/{vram_total} MB usados, '
            f'solo {vram_free} MB libres. Descargar modelos para liberar.'
        )

    # 4. Recomendacion
    healthy = len(warnings) == 0
    if healthy:
        recommendation = 'GPU saludable — todos los modelos corren 100% en GPU.'
    elif any('NO CABE' in w for w in warnings):
        bad = [m for m in loaded_models if not m.fits_in_gpu]
        names = ', '.join(m.name for m in bad)
        recommendation = (
            f'Descargar modelos que no caben: {names}. '
            f'Usar modelos <= {int(vram_total * 0.85 / 1024)} GB para 100% GPU.'
        )
    else:
        recommendation = 'Revisar warnings para optimizar rendimiento GPU.'

    return GpuHealth(
        gpu_name=gpu_name,
        vram_total_mb=vram_total,
        vram_used_mb=vram_used,
        vram_free_mb=vram_free,
        loaded_models=loaded_models,
        healthy=healthy,
        warnings=warnings,
        recommendation=recommendation,
    )


def auto_free_gpu(ollama_base: str = 'http://127.0.0.1:11434') -> list[str]:
    """Descarga automaticamente modelos que no caben 100% en GPU."""
    freed: list[str] = []
    health = check_gpu_health(ollama_base)

    for model in health.loaded_models:
        if not model.fits_in_gpu:
            logger.warning(
                f'gpu_auto_free: Descargando {model.name} '
                f'({model.cpu_percent}% CPU / {model.gpu_percent}% GPU)'
            )
            try:
                with httpx.Client(timeout=15) as c:
                    c.post(f'{ollama_base}/api/generate',
                           json={'model': model.name, 'keep_alive': 0},
                           timeout=15)
                freed.append(model.name)
                logger.info(f'gpu_auto_free: {model.name} descargado')
            except Exception as e:
                logger.error(f'gpu_auto_free: error descargando {model.name}: {e}')

    return freed
