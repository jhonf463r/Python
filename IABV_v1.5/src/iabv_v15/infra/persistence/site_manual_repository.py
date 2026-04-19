"""Persistencia de manuales de sitio generados por el explorador.

Cada manual es un snapshot por `hostname` que resume lo aprendido en una
exploracion BFS: titulo, headings principales, links internos relevantes,
formularios detectados y rutas explicitas que ya fueron visitadas.

Se guarda en dos archivos hermanos dentro de `data/evolution/site_manuals/`:

- `<hostname>.json`: payload estructurado (fuente para codigo y tests).
- `<hostname>.md`: render humano del mismo payload (para revision manual
  y referencia desde el chat local).

No hay "memoria paralela" en el sentido de AGENTS.md: este repositorio
solo materializa el output de una exploracion en vivo. El archivo
markdown es consulta humana; el JSON es la fuente operativa.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _slugify_hostname(hostname: str) -> str:
    slug = re.sub(r'[^a-z0-9._-]', '_', hostname.strip().lower())
    return slug.strip('_') or 'unknown_host'


class SiteManualRepository:
    """Lee y escribe manuales de sitio en disco.

    El repositorio es stateless: solo conoce el directorio raiz donde
    persistir los manuales. Si el directorio no existe, se crea en la
    primera escritura.
    """

    def __init__(self, manuals_dir: Path) -> None:
        self.manuals_dir = Path(manuals_dir)

    def _paths_for(self, hostname: str) -> tuple[Path, Path]:
        slug = _slugify_hostname(hostname)
        return (
            self.manuals_dir / f'{slug}.json',
            self.manuals_dir / f'{slug}.md',
        )

    def load(self, hostname: str) -> dict[str, Any] | None:
        json_path, _ = self._paths_for(hostname)
        if not json_path.exists():
            return None
        try:
            return json.loads(json_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None

    def save(self, manual: dict[str, Any]) -> tuple[Path, Path]:
        hostname = str(manual.get('hostname') or '').strip().lower()
        if not hostname:
            raise ValueError('El manual debe incluir un hostname no vacio.')
        json_path, md_path = self._paths_for(hostname)
        self.manuals_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            **manual,
            'hostname': hostname,
            'updated_at_utc': datetime.now(timezone.utc).isoformat(),
        }
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        md_path.write_text(self._render_markdown(payload), encoding='utf-8')
        return json_path, md_path

    def _render_markdown(self, payload: dict[str, Any]) -> str:
        hostname = payload.get('hostname') or 'unknown'
        updated = payload.get('updated_at_utc') or ''
        pages = payload.get('pages') or []
        summary = str(payload.get('summary') or '').strip()
        lines: list[str] = [
            f'# Manual del sitio `{hostname}`',
            '',
            f'Actualizado: {updated}',
            f'Paginas exploradas: {len(pages)}',
            '',
        ]
        if summary:
            lines.extend(['## Resumen', summary, ''])
        if pages:
            lines.append('## Paginas visitadas')
            for page in pages:
                url = str(page.get('url') or '').strip()
                title = str(page.get('title') or '').strip() or '(sin titulo)'
                headings = [str(h).strip() for h in (page.get('headings') or []) if str(h).strip()]
                links = [str(l).strip() for l in (page.get('internal_links') or []) if str(l).strip()]
                forms = page.get('forms') or []
                lines.append(f'### {title}')
                if url:
                    lines.append(f'- URL: {url}')
                if headings:
                    lines.append(f'- Headings: {", ".join(headings[:8])}')
                if links:
                    lines.append(f'- Links internos: {len(links)} (muestra: {", ".join(links[:5])})')
                if forms:
                    lines.append(f'- Formularios detectados: {len(forms)}')
                lines.append('')
        return '\n'.join(lines).strip() + '\n'
