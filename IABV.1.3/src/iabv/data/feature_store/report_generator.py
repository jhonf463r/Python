# src/iabv/data/feature_store/report_generator.py
"""
Funciones ligeras para guardar reports de validación/snapshots:
- save_json(obj, path)
- save_markdown(report, path)
- save_html(report, path)
- save_index(directory)  -> crea index.html con enlaces a JSON/MD/HTML en el directorio
"""
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime
from typing import Any, Dict, Optional

def _ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def save_json(obj: Any, path: Path) -> Path:
    p = Path(path)
    _ensure_parent(p)
    # if obj is not serializable, coerce gently
    with p.open("w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return p

def _render_kv_lines(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"- **valid**: {report.get('valid')}")
    if "sha1" in report:
        lines.append(f"- **sha1**: `{report.get('sha1')}`")
    if "timestamp_utc" in report:
        lines.append(f"- **timestamp_utc**: {report.get('timestamp_utc')}")
    # short lists
    if report.get("critical_errors"):
        lines.append("- **critical_errors:**")
        for e in report.get("critical_errors", []):
            lines.append(f"  - {e}")
    if report.get("warnings"):
        lines.append("- **warnings:**")
        for w in report.get("warnings", []):
            lines.append(f"  - {w}")
    if report.get("info"):
        lines.append("- **info:**")
        for i in report.get("info", []):
            lines.append(f"  - {i}")
    return "\n".join(lines)

def save_markdown(report: Dict[str, Any], path: Path, title: Optional[str] = None) -> Path:
    p = Path(path)
    _ensure_parent(p)
    t = title or f"Validation report {report.get('sha1', '')[:8]}"
    md = [f"# {t}", "", _render_kv_lines(report), ""]
    # include raw payload/sample if present
    if "raw" in report and report["raw"] is not None:
        md.append("## Raw")
        md.append("```json")
        try:
            md.append(json.dumps(report["raw"], ensure_ascii=False, indent=2, default=str))
        except Exception:
            md.append(str(report["raw"]))
        md.append("```")
    p.write_text("\n".join(md), encoding="utf8")
    return p

def save_html(report: Dict[str, Any], path: Path, title: Optional[str] = None) -> Path:
    p = Path(path)
    _ensure_parent(p)
    t = title or f"Validation report {report.get('sha1', '')[:8]}"
    body = f"<h1>{t}</h1>\n"
    body += "<ul>\n"
    body += f"<li>valid: {report.get('valid')}</li>\n"
    if "sha1" in report:
        body += f"<li>sha1: <code>{report.get('sha1')}</code></li>\n"
    if "timestamp_utc" in report:
        body += f"<li>timestamp_utc: {report.get('timestamp_utc')}</li>\n"
    body += "</ul>\n"
    if report.get("critical_errors"):
        body += "<h2>Critical errors</h2>\n<ul>\n"
        for e in report.get("critical_errors", []):
            body += f"<li>{e}</li>\n"
        body += "</ul>\n"
    # raw
    if "raw" in report and report["raw"] is not None:
        body += "<h2>Raw</h2>\n<pre>\n"
        try:
            body += json.dumps(report["raw"], ensure_ascii=False, indent=2, default=str)
        except Exception:
            body += str(report["raw"])
        body += "\n</pre>\n"
    html = f"<!doctype html>\n<html><head><meta charset='utf-8'><title>{t}</title></head><body>{body}</body></html>"
    p.write_text(html, encoding="utf8")
    return p

def save_index(directory: Path) -> Path:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for ext in ("*.json", "*.md", "*.html"):
        for p in sorted(d.glob(ext)):
            items.append(p.name)
    lines = ["<html><head><meta charset='utf-8'><title>Reports index</title></head><body>",
             "<h1>Reports</h1>", "<ul>"]
    for it in items:
        lines.append(f"<li><a href=\"{it}\">{it}</a></li>")
    lines.append("</ul></body></html>")
    idx = d / "index.html"
    idx.write_text("\n".join(lines), encoding="utf8")
    return idx
