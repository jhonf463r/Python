#!/usr/bin/env python3
"""
SVG Pipeline Unificado

Une dos capas sin que se dañen entre sí:
1) Capa de origen: ancla / normaliza el SVG.
2) Capa de optimización: reordena rutas y reduce recorrido.

Diseño:
- Las capas se ejecutan por bytes, no sobre el mismo DOM vivo.
- La salida de una capa se convierte en entrada de la siguiente.
- La UI permite ejecutar una sola capa o la cadena completa.

Uso:
- Streamlit:
    streamlit run svg_unificado_app.py
- CLI:
    python svg_unificado_app.py input.svg --mode cadena -o output.svg
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from lxml import etree

HERE = Path(__file__).resolve().parent


def _load_local_module(module_name: str, filename: str):
    """
    Importa un módulo vecino por ruta para que el bundle funcione tanto
    como carpeta suelta como dentro de un ejecutable.
    """
    module_path = HERE / filename
    if module_path.exists():
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[arg-type]
            return module

    # Fallback: import normal si el archivo ya está en el sys.path.
    return __import__(module_name)


origen = _load_local_module("svg_origen", "svg_origen.py")
optimizer = _load_local_module("svg_optimizer", "svg_optimizer.py")

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore


SVG_NS = "http://www.w3.org/2000/svg"


@dataclass
class StageResult:
    name: str
    data: bytes
    info: Dict[str, object]


class SvgOriginLayer:
    """Capa de origen: ancla y normaliza la posición del SVG."""

    def __init__(self, origin_mode: str, custom_x_mm: float = 0.0, custom_y_mm: float = 0.0):
        self.origin_mode = origin_mode
        self.custom_x_mm = custom_x_mm
        self.custom_y_mm = custom_y_mm

    def run(self, svg_bytes: bytes) -> StageResult:
        out, info = origen.process_svg_bytes(
            svg_bytes,
            origin_mode=self.origin_mode,
            custom_x_mm=self.custom_x_mm,
            custom_y_mm=self.custom_y_mm,
            show_diagnostic=True,
        )
        return StageResult("origen", out, info)


class SvgOptimizationLayer:
    """Capa de optimización: reduce recorrido y reordena paths."""

    def __init__(self, allow_reverse: bool = True, preserve_style_groups: bool = True):
        self.allow_reverse = allow_reverse
        self.preserve_style_groups = preserve_style_groups

    def run(self, svg_bytes: bytes) -> StageResult:
        out, info = optimizer.optimize_svg_bytes(
            svg_bytes,
            allow_reverse=self.allow_reverse,
            preserve_style_groups=self.preserve_style_groups,
            preserve_render=True,
        )
        return StageResult("optimización", out, info)


@dataclass
class PipelineConfig:
    mode: str
    origin_mode: str
    custom_x_mm: float = 0.0
    custom_y_mm: float = 0.0
    allow_reverse: bool = True
    preserve_style_groups: bool = True

    def build_layers(self):
        origin_layer = SvgOriginLayer(self.origin_mode, self.custom_x_mm, self.custom_y_mm)
        opt_layer = SvgOptimizationLayer(self.allow_reverse, self.preserve_style_groups)
        if self.mode == "origen":
            return [origin_layer]
        if self.mode == "optimizar":
            return [opt_layer]
        # orden recomendado: primero origen, luego optimización
        return [origin_layer, opt_layer]


class SvgPipeline:
    """Ejecuta las capas de forma secuencial sin mezclar estructuras internas."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def execute(self, svg_bytes: bytes) -> list[StageResult]:
        current = svg_bytes
        results: list[StageResult] = []
        for layer in self.config.build_layers():
            result = layer.run(current)
            results.append(result)
            current = result.data
        return results


def _svg_preview_html(svg_bytes: bytes) -> str:
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"""
    <html>
      <body style="margin:0;background:#111;">
        <iframe
          src="data:image/svg+xml;base64,{encoded}"
          style="width:100%;height:100vh;border:none;background:white;"
        ></iframe>
      </body>
    </html>
    """


def _safe_name(name: str, suffix: str) -> str:
    stem = Path(name).stem or "svg"
    return f"{stem}_{suffix}.svg"


def _show_stage_metrics(stage: StageResult):
    info = stage.info or {}
    st.subheader(f"Capa: {stage.name}")
    cols = st.columns(4)

    if stage.name == "origen":
        cols[0].metric("Modo", str(info.get("origin_mode", "—")))
        cols[1].metric("Ancla", str(info.get("anchor", "—")))
        cols[2].metric("Matriz", "ver diagnóstico")
        cols[3].metric("Salida", f"{len(stage.data):,} bytes")
        with st.expander("Diagnóstico de origen", expanded=False):
            for key in ("visible_bbox", "frame_bbox", "chosen_bbox", "anchor", "matrix", "output_bbox"):
                if key in info:
                    st.write(f"**{key}**: {info[key]}")
    else:
        cols[0].metric("Paths in", str(info.get("paths_in", "—")))
        cols[1].metric("Paths out", str(info.get("paths_out", "—")))
        cols[2].metric("Travel saved", f"{float(info.get('travel_saved', 0.0)):.3f}")
        cols[3].metric("Reducción", f"{float(info.get('travel_saved_pct', 0.0)):.2f}%")
        with st.expander("Auditoría de optimización", expanded=False):
            st.json(info)


def _process_upload(uploaded, config: PipelineConfig):
    pipeline = SvgPipeline(config)
    original = uploaded.getvalue()
    stages = pipeline.execute(original)

    st.divider()
    st.markdown(f"### {uploaded.name}")
    st.write(f"Entrada: {len(original):,} bytes")

    if not stages:
        st.warning("No se ejecutó ninguna capa.")
        return

    for stage in stages:
        _show_stage_metrics(stage)
        preview_col, download_col = st.columns([3, 1])
        with preview_col:
            st.components.v1.html(_svg_preview_html(stage.data), height=500, scrolling=True)
        with download_col:
            st.download_button(
                label=f"Descargar {stage.name}",
                data=stage.data,
                file_name=_safe_name(uploaded.name, stage.name),
                mime="image/svg+xml",
                use_container_width=True,
                key=f"dl_{uploaded.name}_{stage.name}",
            )

    final = stages[-1]
    st.success("Cadena completa ejecutada.")
    st.download_button(
        label="Descargar salida final",
        data=final.data,
        file_name=_safe_name(uploaded.name, "final"),
        mime="image/svg+xml",
        use_container_width=True,
        key=f"dl_{uploaded.name}_final",
    )


def _run_streamlit_ui() -> None:
    if st is None:
        raise RuntimeError("Streamlit no está instalado en este entorno.")

    st.set_page_config(page_title="SVG Pipeline Unificado", layout="wide")
    st.title("SVG Pipeline Unificado")
    st.caption(
        "Dos capas separadas y ordenadas: origen y optimización. "
        "Cada paso trabaja sobre los bytes de salida del paso anterior."
    )

    with st.sidebar:
        st.header("Procesamiento")
        mode = st.selectbox("Modo", ["cadena", "origen", "optimizar"], index=0)
        st.markdown("**Orden recomendado**: origen → optimización.")
        st.subheader("Capa de origen")
        origin_mode = st.selectbox(
            "Origen CNC",
            [
                "Superior izquierda (0,0)",
                "Inferior izquierda",
                "Centro",
                "Superior derecha",
                "Inferior derecha",
                "Personalizado X/Y",
            ],
            index=0,
        )
        custom_x_mm = 0.0
        custom_y_mm = 0.0
        if origin_mode == "Personalizado X/Y":
            c1, c2 = st.columns(2)
            with c1:
                custom_x_mm = st.number_input("X (mm)", value=0.0, step=1.0, format="%.3f")
            with c2:
                custom_y_mm = st.number_input("Y (mm)", value=0.0, step=1.0, format="%.3f")

        st.subheader("Capa de optimización")
        allow_reverse = st.checkbox("Permitir reverse de PATH completo", value=True)
        preserve_style_groups = st.checkbox("Preservar grupos contiguos por estilo", value=True)

    uploaded_files = st.file_uploader("Sube uno o varios SVG", type=["svg"], accept_multiple_files=True)
    run = st.button("Procesar", type="primary", use_container_width=True)

    if not run:
        return
    if not uploaded_files:
        st.warning("Carga al menos un SVG.")
        return

    config = PipelineConfig(
        mode=mode,
        origin_mode=origin_mode,
        custom_x_mm=custom_x_mm,
        custom_y_mm=custom_y_mm,
        allow_reverse=allow_reverse,
        preserve_style_groups=preserve_style_groups,
    )

    for uploaded in uploaded_files:
        try:
            _process_upload(uploaded, config)
        except Exception as exc:
            st.error(f"Error procesando {uploaded.name}: {exc}")


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI simple para usar la misma lógica sin Streamlit.
    """
    if argv is None and st is not None:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
            if get_script_run_ctx() is not None:
                _run_streamlit_ui()
                return 0
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="svg_unificado_app.py", description="Capa origen + capa optimización para SVG.")
    parser.add_argument("input", nargs="?", help="SVG de entrada. Usa '-' para stdin.")
    parser.add_argument("-o", "--output", help="Ruta de salida final.")
    parser.add_argument("--mode", choices=["cadena", "origen", "optimizar"], default="cadena")
    parser.add_argument("--origin-mode", default="Superior izquierda (0,0)")
    parser.add_argument("--custom-x-mm", type=float, default=0.0)
    parser.add_argument("--custom-y-mm", type=float, default=0.0)
    parser.add_argument("--no-reverse", action="store_true")
    parser.add_argument("--no-style-groups", action="store_true")
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 2

    if args.input == "-":
        svg_bytes = sys.stdin.buffer.read()
        input_name = "stdin.svg"
    else:
        svg_bytes = Path(args.input).read_bytes()
        input_name = Path(args.input).name

    config = PipelineConfig(
        mode=args.mode,
        origin_mode=args.origin_mode,
        custom_x_mm=args.custom_x_mm,
        custom_y_mm=args.custom_y_mm,
        allow_reverse=not args.no_reverse,
        preserve_style_groups=not args.no_style_groups,
    )
    pipeline = SvgPipeline(config)
    stages = pipeline.execute(svg_bytes)

    final_bytes = stages[-1].data if stages else svg_bytes
    output_path = Path(args.output) if args.output else Path(input_name).with_name(Path(input_name).stem + "_final.svg")
    output_path.write_bytes(final_bytes)
    print(f"OK: {input_name} -> {output_path}")
    for stage in stages:
        print(f"[{stage.name}] {len(stage.data)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
