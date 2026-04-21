"""PromotionPrPublisher: F2.3 (thin).

Cuando ``AutonomousValidationCycleService`` promueve un candidato
(``promote_to_primary=True``), este servicio crea un PR *documental* en
GitHub describiendo la promocion, sin cambiar logica ejecutable. El objetivo
es dejar trazabilidad auditable en git cada vez que el sistema decide por
evidencia que una ruta/herramienta gana frente a otra.

Regla operativa:

    1. Genera un markdown en ``data/evolution/promoted/<ts>-<subject>.md`` con
       sujeto, ruta actual -> ruta ganadora, veredicto, evidencia y metricas.
    2. Crea una rama ``iabv-auto/promote-<subject>-<ts>`` en el checkout
       local, agrega el archivo, commitea.
    3. Llama a ``GitHubRemoteService.publish_branch_as_pr`` con esa rama.
       La policy existente (``allow_github_pr_open``) decide auto-aprobar
       (``iabv-auto/*`` con diff<=200 siempre lo es para markdown) o pedir
       humano.
    4. Deja evidencia completa en ``data/evolution/promoted/<ts>-<subject>.json``.

No decide rutas, no toca codigo ejecutable, no modifica contratos: solo
documenta lo que el ciclo de validacion ya decidio y publica via el
servicio existente.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

_GitRunner = Callable[[list[str], Path], subprocess.CompletedProcess]


def _default_git_runner(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


_SUBJECT_SLUG_RX = re.compile(r'[^a-zA-Z0-9]+')


def _slugify_subject(value: str) -> str:
    slug = _SUBJECT_SLUG_RX.sub('-', str(value or '')).strip('-').lower()
    return slug[:48] if slug else 'unknown'


@dataclass(frozen=True)
class PromotionPublishResult:
    """Resultado publico de ``publish_promotion``."""

    success: bool
    subject_key: str
    branch: str = ''
    markdown_path: str = ''
    evidence_path: str = ''
    pr_number: Optional[int] = None
    pr_url: str = ''
    blocked_by_policy: bool = False
    required_approval: bool = False
    skipped: bool = False
    error: str = ''
    extra: Mapping[str, Any] = field(default_factory=dict)


class PromotionPrPublisher:
    """Orquesta markdown + git branch + commit + publish_branch_as_pr."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
        github_remote_service: Any,
        output_dir: Path | str | None = None,
        git_runner: _GitRunner | None = None,
        clock: Callable[[], float] | None = None,
        enabled: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.github_remote_service = github_remote_service
        self.output_dir = (
            Path(output_dir)
            if output_dir is not None
            else self.repo_root / 'data' / 'evolution' / 'promoted'
        )
        self._git_runner: _GitRunner = git_runner or _default_git_runner
        self._clock = clock or time.time
        self.enabled = bool(enabled)

    # ---- public API --------------------------------------------------

    def publish_promotion(
        self,
        *,
        subject_key: str,
        proposal_kind: str,
        current_route: str,
        current_assistant_kind: str,
        candidate_route: str,
        candidate_assistant_kind: str,
        verdict: str,
        summary: str,
        metrics: Mapping[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        sandbox_experiment_id: str = '',
        proposal_id: str = '',
        base: str = 'main',
    ) -> PromotionPublishResult:
        """Publica la promocion como PR documental en una rama ``iabv-auto/*``.

        Si ``self.enabled`` es ``False`` (flag desactivado), retorna
        ``skipped=True`` sin tocar filesystem ni git. Cualquier fallo de git
        o del servicio remoto se captura y retorna en ``error``: el ciclo de
        validacion no debe caer por un problema de publicacion documental.
        """

        subject = str(subject_key or '').strip()
        if not self.enabled:
            return PromotionPublishResult(
                success=False, subject_key=subject, skipped=True,
                error='publisher disabled',
            )
        if not subject:
            return PromotionPublishResult(
                success=False, subject_key=subject,
                error='subject_key vacio.',
            )
        if self.github_remote_service is None:
            return PromotionPublishResult(
                success=False, subject_key=subject,
                error='github_remote_service no disponible.',
            )

        ts_epoch = int(self._clock())
        slug = _slugify_subject(subject)
        branch = f'iabv-auto/promote-{slug}-{ts_epoch}'
        md_name = f'{ts_epoch}-{slug}.md'
        evidence_name = f'{ts_epoch}-{slug}.json'

        metrics_map = dict(metrics or {})
        evidence_list = [str(ref) for ref in (evidence_refs or []) if ref]
        markdown = self._render_markdown(
            subject_key=subject,
            proposal_kind=proposal_kind,
            current_route=current_route,
            current_assistant_kind=current_assistant_kind,
            candidate_route=candidate_route,
            candidate_assistant_kind=candidate_assistant_kind,
            verdict=verdict,
            summary=summary,
            metrics=metrics_map,
            evidence_refs=evidence_list,
            sandbox_experiment_id=sandbox_experiment_id,
            proposal_id=proposal_id,
            ts_epoch=ts_epoch,
            branch=branch,
        )

        # 1) escribir markdown dentro del repo (bajo data/evolution/promoted).
        md_path = self._write_markdown(md_name, markdown)
        # 2) rama + commit. Cualquier fallo aca aborta la publicacion sin
        #    intentar el push remoto.
        git_ok, git_err, commit_sha = self._prepare_branch_and_commit(
            branch=branch, md_path=md_path, subject=subject,
        )
        if not git_ok:
            self._write_evidence(
                evidence_name,
                subject=subject,
                branch=branch,
                markdown_path=str(md_path),
                commit_sha=commit_sha,
                publish_payload=None,
                error=git_err,
            )
            return PromotionPublishResult(
                success=False, subject_key=subject, branch=branch,
                markdown_path=str(md_path),
                evidence_path=str(self.output_dir / evidence_name),
                error=git_err,
            )

        # 3) delegar en el servicio de PR.
        diff_lines = _count_diff_lines(markdown)
        try:
            publish = self.github_remote_service.publish_branch_as_pr(
                branch=branch,
                title=f'iabv-auto: promocion de {subject}',
                body=markdown,
                base=base,
                diff_lines=diff_lines,
                draft=False,
                approval_context={
                    'origin': 'autonomous_validation_cycle',
                    'subject_key': subject,
                    'verdict': str(verdict or ''),
                },
            )
        except Exception as exc:  # pragma: no cover - defensivo
            self._write_evidence(
                evidence_name,
                subject=subject,
                branch=branch,
                markdown_path=str(md_path),
                commit_sha=commit_sha,
                publish_payload=None,
                error=repr(exc),
            )
            return PromotionPublishResult(
                success=False, subject_key=subject, branch=branch,
                markdown_path=str(md_path),
                evidence_path=str(self.output_dir / evidence_name),
                error=repr(exc),
            )

        publish_payload = _publish_result_to_dict(publish)
        self._write_evidence(
            evidence_name,
            subject=subject,
            branch=branch,
            markdown_path=str(md_path),
            commit_sha=commit_sha,
            publish_payload=publish_payload,
            error=publish_payload.get('error') or '',
        )

        return PromotionPublishResult(
            success=bool(publish_payload.get('success')),
            subject_key=subject,
            branch=branch,
            markdown_path=str(md_path),
            evidence_path=str(self.output_dir / evidence_name),
            pr_number=publish_payload.get('pr_number'),
            pr_url=str(publish_payload.get('pr_url') or ''),
            blocked_by_policy=bool(publish_payload.get('blocked_by_policy')),
            required_approval=bool(publish_payload.get('required_approval')),
            error=str(publish_payload.get('error') or ''),
            extra={'commit_sha': commit_sha},
        )

    # ---- helpers -----------------------------------------------------

    def _write_markdown(self, name: str, markdown: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / name
        path.write_text(markdown, encoding='utf-8')
        return path

    def _write_evidence(
        self,
        name: str,
        *,
        subject: str,
        branch: str,
        markdown_path: str,
        commit_sha: str,
        publish_payload: Mapping[str, Any] | None,
        error: str,
    ) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / name
        payload = {
            'at_epoch': self._clock(),
            'id': str(uuid.uuid4()),
            'subject_key': subject,
            'branch': branch,
            'markdown_path': markdown_path,
            'commit_sha': commit_sha,
            'publish': dict(publish_payload) if publish_payload else None,
            'error': error,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return path

    def _prepare_branch_and_commit(
        self, *, branch: str, md_path: Path, subject: str,
    ) -> tuple[bool, str, str]:
        """Crea la rama ``iabv-auto/...``, agrega el markdown y commitea.

        Devuelve ``(success, error_or_empty, commit_sha)``. Deja el HEAD en
        la rama nueva para que ``publish_branch_as_pr`` pueda empujarla.
        """

        head_before = self._run_git(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        head_before_ok = head_before.returncode == 0
        starting_branch = head_before.stdout.strip() if head_before_ok else ''

        # checkout -B: crea o reutiliza la rama apuntando al HEAD actual.
        co = self._run_git(['git', 'checkout', '-B', branch])
        if co.returncode != 0:
            return False, f'git checkout fallo: {co.stderr.strip() or co.stdout.strip()}', ''

        try:
            rel_md = str(md_path.relative_to(self.repo_root))
        except ValueError:
            rel_md = str(md_path)
        add = self._run_git(['git', 'add', '--', rel_md])
        if add.returncode != 0:
            self._restore_branch(starting_branch)
            return False, f'git add fallo: {add.stderr.strip() or add.stdout.strip()}', ''

        commit = self._run_git([
            'git', 'commit',
            '-m', f'iabv-auto: promocion documentada ({subject})',
            '--no-verify',
        ])
        if commit.returncode != 0:
            self._restore_branch(starting_branch)
            return False, f'git commit fallo: {commit.stderr.strip() or commit.stdout.strip()}', ''

        rev = self._run_git(['git', 'rev-parse', 'HEAD'])
        commit_sha = rev.stdout.strip() if rev.returncode == 0 else ''
        return True, '', commit_sha

    def _restore_branch(self, starting_branch: str) -> None:
        if not starting_branch:
            return
        self._run_git(['git', 'checkout', starting_branch])

    def _run_git(self, argv: list[str]) -> subprocess.CompletedProcess:
        return self._git_runner(argv, self.repo_root)

    def _render_markdown(
        self,
        *,
        subject_key: str,
        proposal_kind: str,
        current_route: str,
        current_assistant_kind: str,
        candidate_route: str,
        candidate_assistant_kind: str,
        verdict: str,
        summary: str,
        metrics: Mapping[str, Any],
        evidence_refs: list[str],
        sandbox_experiment_id: str,
        proposal_id: str,
        ts_epoch: int,
        branch: str,
    ) -> str:
        lines: list[str] = []
        lines.append(f'# iabv-auto: promocion de {subject_key}')
        lines.append('')
        lines.append(
            'PR generado automaticamente por `AutonomousValidationCycleService` '
            'al promover un candidato validado en sandbox. Este documento no '
            'modifica logica ejecutable; solo deja traza en git de la decision.'
        )
        lines.append('')
        lines.append('## Sujeto')
        lines.append('')
        lines.append(f'- subject_key: `{subject_key}`')
        if proposal_kind:
            lines.append(f'- proposal_kind: `{proposal_kind}`')
        if proposal_id:
            lines.append(f'- proposal_id: `{proposal_id}`')
        lines.append('')
        lines.append('## Ruta actual -> ruta ganadora')
        lines.append('')
        lines.append(f'- actual: `{current_route}` / asistente `{current_assistant_kind or "n/a"}`')
        lines.append(f'- ganadora: `{candidate_route}` / asistente `{candidate_assistant_kind or "n/a"}`')
        lines.append('')
        lines.append('## Veredicto de sandbox')
        lines.append('')
        lines.append(f'- verdict: `{verdict}`')
        if sandbox_experiment_id:
            lines.append(f'- sandbox_experiment_id: `{sandbox_experiment_id}`')
        if summary:
            lines.append('')
            lines.append('### Resumen')
            lines.append('')
            lines.append(str(summary))
        lines.append('')
        lines.append('## Metricas')
        lines.append('')
        if metrics:
            for key in sorted(metrics.keys()):
                value = metrics[key]
                lines.append(f'- {key}: `{value}`')
        else:
            lines.append('- (sin metricas)')
        lines.append('')
        lines.append('## Evidencia')
        lines.append('')
        if evidence_refs:
            for ref in evidence_refs[:20]:
                lines.append(f'- `{ref}`')
        else:
            lines.append('- (sin referencias de evidencia)')
        lines.append('')
        lines.append('## Trazabilidad')
        lines.append('')
        lines.append(f'- branch: `{branch}`')
        lines.append(f'- generado_at_epoch: `{ts_epoch}`')
        lines.append('')
        return '\n'.join(lines)


def _count_diff_lines(markdown: str) -> int:
    if not markdown:
        return 0
    return sum(1 for _ in markdown.splitlines()) + 1


def _publish_result_to_dict(result: Any) -> dict[str, Any]:
    if result is None:
        return {'success': False, 'error': 'publish devolvio None'}
    if isinstance(result, Mapping):
        return dict(result)
    payload: dict[str, Any] = {}
    for field_name in (
        'success', 'branch', 'base', 'pr_number', 'pr_url', 'http_status',
        'pushed', 'blocked_by_policy', 'required_approval', 'approval_granted',
        'error', 'evidence_path',
    ):
        payload[field_name] = getattr(result, field_name, None)
    extra = getattr(result, 'extra', None)
    if extra is not None:
        try:
            payload['extra'] = dict(extra)
        except Exception:
            payload['extra'] = {}
    return payload
