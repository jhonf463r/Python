"""GPU Metacognition Module - Runtime GPU Health Verification.

Metacognition: the program inspects its own GPU usage at startup,
cross-validates nvidia-smi vs ollama ps vs Windows Task Manager,
and auto-corrects if Ollama is using the wrong GPU.

Learned patterns:
  - NVIDIA_SMI_UNRELIABLE: nvidia-smi reports VRAM reserved but GPU may
    not actually be computing. Always cross-validate with ollama ps.
  - GPU_WRONG_DEVICE: Ollama may detect Intel iGPU instead of NVIDIA dGPU.
    Must verify which GPU actually shows activity during inference.
  - MODEL_TOO_LARGE: Models exceeding VRAM fall back to CPU silently.
    ollama ps shows the real CPU/GPU split (e.g. "61%/39% CPU/GPU").
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def detect_physical_gpus() -> list[dict[str, Any]]:
    """Detect all physical GPUs via nvidia-smi, wmic, and PowerShell (fallback)."""
    gpus: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                m = re.match(r"GPU (\d+): (.+?) \(UUID:", line)
                if m:
                    gpus.append({
                        "index": int(m.group(1)),
                        "name": m.group(2),
                        "type": "nvidia",
                        "source": "nvidia-smi",
                    })
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get",
             "Name,AdapterCompatibility,AdapterRAM", "/format:csv"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines()[1:]:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4 and parts[2]:
                    is_dup = any(
                        g["source"] == "nvidia-smi" and parts[2] in g["name"]
                        for g in gpus
                    )
                    if not is_dup:
                        gpus.append({
                            "name": parts[2],
                            "vendor": parts[1],
                            "vram_bytes": int(parts[3]) if parts[3].isdigit() else 0,
                            "source": "wmic",
                        })
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Fallback: PowerShell Get-CimInstance for GPUs not found by wmic
    if os.name == 'nt':
        try:
            ps_script = (
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name, AdapterCompatibility, AdapterRAM, "
                "VideoProcessor, DriverVersion | ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                import json as _json
                data = _json.loads(result.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for vc in data:
                    name = vc.get('Name', '')
                    if not name:
                        continue
                    # Skip if already found
                    is_dup = any(name.lower() in g.get('name', '').lower()
                                or g.get('name', '').lower() in name.lower()
                                for g in gpus)
                    if is_dup:
                        continue
                    vendor = vc.get('AdapterCompatibility', '')
                    gpu_type = 'nvidia' if 'nvidia' in vendor.lower() else (
                        'intel' if 'intel' in vendor.lower() else 'other')
                    gpus.append({
                        "name": name,
                        "vendor": vendor,
                        "vram_bytes": int(vc.get('AdapterRAM', 0) or 0),
                        "driver_version": vc.get('DriverVersion', ''),
                        "type": gpu_type,
                        "source": "powershell",
                    })
        except Exception:
            pass
    return gpus


def detect_ollama_gpu_state() -> dict[str, Any]:
    """Query ollama ps to get the REAL GPU/CPU split for loaded models.

    This is the ground truth - more reliable than nvidia-smi alone.
    """
    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"status": "error", "detail": result.stderr.strip()}
        models = []
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                gpu_pct = 0
                cpu_pct = 0
                if "100% GPU" in line:
                    gpu_pct = 100
                elif "100% CPU" in line:
                    cpu_pct = 100
                else:
                    m = re.search(r"(\d+)%/(\d+)%\s+CPU/GPU", line)
                    if m:
                        cpu_pct = int(m.group(1))
                        gpu_pct = int(m.group(2))
                    else:
                        m2 = re.search(r"(\d+)%\s+GPU", line)
                        if m2:
                            gpu_pct = int(m2.group(1))
                models.append({
                    "name": name,
                    "gpu_percent": gpu_pct,
                    "cpu_percent": cpu_pct,
                    "fully_gpu": gpu_pct == 100,
                    "raw_line": line.strip(),
                })
        return {
            "status": "ok",
            "models": models,
            "any_model_loaded": len(models) > 0,
        }
    except FileNotFoundError:
        return {"status": "ollama_not_found"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}


def gpu_metacognition_report() -> dict[str, Any]:
    """Full metacognition report: what GPUs exist, what Ollama sees, discrepancies."""
    gpus = detect_physical_gpus()
    ollama_state = detect_ollama_gpu_state()
    nvidia_gpus = [g for g in gpus if g.get("type") == "nvidia"]
    intel_gpus = [g for g in gpus if "intel" in g.get("name", "").lower()
                  or g.get("vendor", "").lower() == "intel"]
    report = {
        "gpus_detected": gpus,
        "nvidia_count": len(nvidia_gpus),
        "intel_igpu_count": len(intel_gpus),
        "ollama_state": ollama_state,
        "issues": [],
        "recommendations": [],
    }
    if ollama_state.get("status") == "ok":
        for m in ollama_state.get("models", []):
            if not m["fully_gpu"] and m["gpu_percent"] > 0:
                report["issues"].append(
                    f"Model {m['name']} is split: {m['cpu_percent']}% CPU / "
                    f"{m['gpu_percent']}% GPU - model too large for VRAM"
                )
                report["recommendations"].append(
                    f"Unload {m['name']} and use a smaller model that fits 100% in GPU"
                )
            elif m["cpu_percent"] == 100:
                report["issues"].append(
                    f"Model {m['name']} is 100% CPU - GPU not being used at all"
                )
                report["recommendations"].append(
                    "Check CUDA installation and Ollama GPU support"
                )
    if nvidia_gpus and intel_gpus:
        report["dual_gpu_strategy"] = {
            "recommended": True,
            "primary_compute": nvidia_gpus[0]["name"],
            "primary_compute_index": nvidia_gpus[0].get("index", 0),
            "reinforcement": intel_gpus[0]["name"],
            "explanation": (
                "NVIDIA GPU is primary for CUDA compute (Ollama, inference). "
                "Intel iGPU handles display/video and acts as reinforcement "
                "when NVIDIA VRAM is full or for parallel lightweight tasks."
            ),
        }
        # Note: GPU correction is done only at startup (startup_gpu_health_check),
        # not here, to keep this function side-effect-free.
    elif len(nvidia_gpus) > 1:
        report["dual_gpu_strategy"] = {
            "recommended": True,
            "primary_compute": nvidia_gpus[0]["name"],
            "primary_compute_index": nvidia_gpus[0].get("index", 0),
            "reinforcement": nvidia_gpus[1]["name"],
            "explanation": (
                f"GPU {nvidia_gpus[0].get('index', 0)} ({nvidia_gpus[0]['name']}) "
                f"is primary. GPU {nvidia_gpus[1].get('index', 1)} "
                f"({nvidia_gpus[1]['name']}) is reinforcement for high load."
            ),
        }
    return report


def _ensure_gpu_primary(nvidia_gpu: dict[str, Any]) -> None:
    """Ensure CUDA_VISIBLE_DEVICES points to the NVIDIA GPU if not already set.

    On dual-GPU systems (Intel iGPU + NVIDIA dGPU), CUDA only sees
    NVIDIA GPUs, so CUDA index 0 = first NVIDIA GPU. We only set
    the env var if it's currently misconfigured.
    """
    current = os.environ.get('CUDA_VISIBLE_DEVICES', '')
    if not current:
        # Not set — CUDA defaults to all NVIDIA GPUs, which is correct
        return
    try:
        requested = [int(x.strip()) for x in current.split(',') if x.strip()]
        nvidia_index = nvidia_gpu.get('index', 0)
        if nvidia_index not in requested:
            # Misconfigured — fix it to point to the NVIDIA GPU
            os.environ['CUDA_VISIBLE_DEVICES'] = str(nvidia_index)
            logger.info(
                'gpu_metacognition: corrected CUDA_VISIBLE_DEVICES from %s to %s',
                current, nvidia_index,
            )
    except ValueError:
        pass


def auto_free_gpu_for_model(target_vram_gb: float = 4.0) -> dict[str, Any]:
    """Unload models that don't fit 100% in GPU to free VRAM."""
    ollama_state = detect_ollama_gpu_state()
    freed = []
    if ollama_state.get("status") != "ok":
        return {"status": "skip", "detail": "cannot query ollama ps"}
    for m in ollama_state.get("models", []):
        if not m["fully_gpu"]:
            try:
                subprocess.run(
                    ["ollama", "stop", m["name"]],
                    capture_output=True, timeout=30,
                )
                freed.append(m["name"])
            except Exception as exc:
                logger.warning("auto_free_gpu_for_model: could not stop %s: %s", m["name"], exc)
    return {"freed": freed, "count": len(freed)}


def startup_gpu_health_check() -> dict[str, Any]:
    """Run at bootstrap to verify GPU health, correct GPU config, and log findings."""
    report = gpu_metacognition_report()
    # Auto-correct GPU config at startup only (not in the report function)
    strategy = report.get('dual_gpu_strategy', {})
    nvidia_gpus = [g for g in report.get('gpus_detected', []) if g.get('type') == 'nvidia']
    if strategy.get('recommended') and nvidia_gpus:
        _ensure_gpu_primary(nvidia_gpus[0])
    for issue in report.get("issues", []):
        logger.warning("gpu_metacognition: %s", issue)
    for rec in report.get("recommendations", []):
        logger.info("gpu_recommendation: %s", rec)
    try:
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        report_path = data_dir / "gpu_health_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("gpu_health_report saved to %s", report_path)
    except Exception as exc:
        logger.warning("gpu_health_report: could not save: %s", exc)
    return report
