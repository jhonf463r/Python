"""GitHubRemoteService: publica una rama local como PR en GitHub.

No es otro cerebro ni decisor de rutas. Es un orquestador minimo que:

    1. Valida via ``AutonomyGovernancePolicy.allow_github_pr_open`` si la
       apertura del PR puede auto-aprobarse por patron de rama y tamano.
    2. Si no, pide aprobacion humana via ``HumanApprovalBroker`` (opcional).
    3. Empuja la rama local a ``origin`` via ``git push`` (subprocess).
    4. Llama a ``GitHubApiToolAdapter.run`` con ``github_action=create_pr``.
    5. Registra evidencia JSON en ``data/evolution/pr_history/<ts>-<id>.json``.

Todo el conocimiento de REST GitHub vive en ``GitHubApiToolAdapter``. Este
servicio solo coordina y deja traza auditable. No toca ViewModels, no duplica
``PerceptionSnapshot`` / ``WorldModelSnapshot``, no instala un loop de
decision: su API es una sola funcion bloqueante (``publish_branch_as_pr``).

Consumers tipicos:
    * UI (EvolutionCenterPage) al presionar "Publicar cambio como PR".
    * ``AutonomousValidationCycleService`` cuando un candidato valida y
      queda listo para salir en una rama ``iabv-auto/*``.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import GitHubApiToolAdapter
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
from iabv_v15.services.trust.authority_client import AuthorityClient


@dataclass(frozen=True)
class PublishResult:
    """Resultado publico de ``publish_branch_as_pr``. Inmutable."""

    success: bool
    branch: str
    base: str
    pr_number: Optional[int] = None
    pr_url: str = ''
    http_status: Optional[int] = None
    pushed: bool = False
    blocked_by_policy: bool = False
    required_approval: bool = False
    approval_granted: bool = False
    error: str = ''
    evidence_path: str = ''
    extra: Mapping[str, Any] = field(default_factory=dict)


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


class GitHubRemoteService:
    """Orquesta ``git push`` + ``GitHubApiToolAdapter.create_pr`` + evidencia.

    Parameters
    ----------
    repo_root:
        Raiz del checkout local (la carpeta donde vive ``.git``).
    adapter:
        Instancia ya configurada de ``GitHubApiToolAdapter`` (token + repo).
    governance_policy:
        Objeto con ``allow_github_pr_open(branch=, base=, diff_lines=) ->
        (bool, reason|None)``. Se satisface con ``AutonomyGovernancePolicy``.
    approval_broker:
        Opcional. Si la policy pide humano y este parametro es ``None``,
        ``publish_branch_as_pr`` devuelve ``required_approval=True`` sin
        crear nada. Si se pasa, se llama a ``request(...)`` y se espera
        hasta el timeout.
    evidence_dir:
        Carpeta donde se escribe la evidencia JSON. Por defecto
        ``{repo_root}/data/evolution/pr_history``.
    git_runner:
        Callable inyectable para pruebas; firma igual a ``subprocess.run``.
    clock:
        ``time.time``-like, inyectable para pruebas.
    approval_timeout_s:
        Timeout en segundos cuando se pide aprobacion humana. Default 300.
    """

    _CARD_ID = 'github_api'

    def __init__(
        self,
        *,
        repo_root: Path | str,
        adapter: GitHubApiToolAdapter,
        governance_policy: Any,
        approval_broker: Any | None = None,
        evidence_dir: Path | str | None = None,
        git_runner: _GitRunner | None = None,
        clock: Callable[[], float] | None = None,
        approval_timeout_s: float = 300.0,
        # F14: Authority integration
        capability_action_bridge: CapabilityActionBridge | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.adapter = adapter
        self.governance_policy = governance_policy
        self.approval_broker = approval_broker
        self.evidence_dir = (
            Path(evidence_dir)
            if evidence_dir is not None
            else self.repo_root / 'data' / 'evolution' / 'pr_history'
        )
        self._git_runner: _GitRunner = git_runner or _default_git_runner
        self._clock = clock or time.time
        self.approval_timeout_s = float(approval_timeout_s)
        # F14: Authority integration
        self.capability_action_bridge = capability_action_bridge

    # ---- public API --------------------------------------------------

    def publish_branch_as_pr(
        self,
        *,
        branch: str,
        title: str,
        body: str = '',
        base: str = 'main',
        diff_lines: int | None = None,
        draft: bool = False,
        remote: str = 'origin',
        approval_context: Mapping[str, str] | None = None,
    ) -> PublishResult:
        """Empuja ``branch`` y abre un PR en GitHub.

        El flujo es estrictamente secuencial: policy -> approval (si aplica)
        -> push -> create_pr -> evidencia. Cualquier paso que falle se
        registra igual en la evidencia y se devuelve en ``PublishResult``.
        """

        head = str(branch or '').strip()
        base_name = str(base or 'main').strip()
        title_text = str(title or '').strip()

        evidence: dict[str, Any] = {
            'requested_at_epoch': self._clock(),
            'branch': head,
            'base': base_name,
            'title': title_text,
            'body_len': len(body or ''),
            'diff_lines': diff_lines,
            'draft': bool(draft),
            'remote': remote,
        }

        if not head:
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    error='branch vacio.',
                ),
            )
        if not title_text:
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    error='title vacio.',
                ),
            )

        # 1) policy
        allowed, block_reason = self.governance_policy.allow_github_pr_open(
            branch=head, base=base_name, diff_lines=diff_lines,
        )
        evidence['policy'] = {
            'auto_approved': bool(allowed),
            'reason': block_reason,
        }

        approval_granted = False
        required_approval = False
        if not allowed:
            required_approval = True
            if self.approval_broker is None:
                return self._finalize(
                    evidence,
                    PublishResult(
                        success=False, branch=head, base=base_name,
                        blocked_by_policy=True,
                        required_approval=True,
                        error=block_reason or 'policy requiere aprobacion humana.',
                    ),
                )
            scope: dict[str, str] = {
                'kind': 'open_pr',
                'branch': head,
                'base': base_name,
            }
            if approval_context:
                for k, v in approval_context.items():
                    scope[str(k)] = str(v)
            result = self.approval_broker.request(
                kind='external_call_authorization',
                reason=(
                    f"Abrir PR {head} -> {base_name}: {block_reason or 'policy lo requiere'}"
                ),
                scope=scope,
                timeout_s=self.approval_timeout_s,
            )
            evidence['approval'] = {
                'approved': bool(getattr(result, 'approved', False)),
                'rejected': bool(getattr(result, 'rejected', False)),
                'timed_out': bool(getattr(result, 'timed_out', False)),
                'auto_resolved': bool(getattr(result, 'auto_resolved', False)),
            }
            if not getattr(result, 'approved', False):
                return self._finalize(
                    evidence,
                    PublishResult(
                        success=False, branch=head, base=base_name,
                        blocked_by_policy=True,
                        required_approval=True,
                        approval_granted=False,
                        error=(
                            'approval rechazada/expirada: no se abre PR.'
                        ),
                    ),
                )
            approval_granted = True

        # F17 FIX: P0.213 authorization BEFORE git push
        # Build task with capability fields for authorization
        # Note: This task is used for authorization; actual PR creation task is built later
        card = ToolCard(
            tool_id=self._CARD_ID,
            title='GitHub API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key=self._CARD_ID,
            metadata={'provider': 'github'},
        )
        
        # Extract repo name from git remote for target specification
        # This is used for capability target identification
        repo_target = f'github_remote:{remote}'
        
        # F17: Authorize git push BEFORE executing git push
        # ACTION: PUSH
        # TARGET: github_remote:{remote}
        if self.capability_action_bridge is None:
            # Authority unavailable - reject execution (fail-closed)
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=False,
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    error="Authority system is not available. Protected git push requires authority process to be running.",
                ),
            )
        
        # For git push authorization, we need capability fields
        # These should be provided by the caller via the publish_branch_as_pr context
        # For now, we'll use a placeholder - in production, these must be passed in
        # TODO: Add lease_id, action, target parameters to publish_branch_as_pr signature
        # For F17 fix, we check if capability fields are available in metadata or context
        lease_id = None
        action = 'PUSH'  # Canonical action for git push
        target = repo_target  # Canonical target for git push
        
        # Try to get capability fields from approval_context if available
        if approval_context:
            lease_id = approval_context.get('lease_id')
            # Override target if provided in context
            if 'target' in approval_context:
                target = approval_context['target']
        
        # Require capability for git push (default-deny)
        if lease_id is None:
            # Missing capability - reject git push (fail-closed)
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=False,
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    error="Protected git push requires capability (lease_id). No capability provided in approval_context.",
                ),
            )
        
        # Authorize git push action with capability
        push_auth_result = self.capability_action_bridge.authorize_action(
            lease_id=lease_id,
            requested_action=action,
            requested_target=target,
            execution_id=f'git_push_{head}_{int(self._clock())}',
        )
        if not push_auth_result.authorized:
            # Authorization failed - reject git push (fail-closed)
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=False,
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    error=f"Git push authorization failed: {push_auth_result.error or 'Unknown error'}",
                ),
            )
        
        evidence['push_authorization'] = {
            'authorized': push_auth_result.authorized,
            'action': action,
            'target': target,
            'lease_id': lease_id,
        }
        
        # 2) git push (NOW AUTHORIZED)
        push_result = self._git_runner(
            ['git', 'push', '--set-upstream', remote, head],
            self.repo_root,
        )
        evidence['push'] = {
            'returncode': push_result.returncode,
            'stderr_tail': (push_result.stderr or '')[-400:],
        }
        if push_result.returncode != 0:
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=False,
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    error=(
                        f'git push fallo (rc={push_result.returncode}): '
                        f'{(push_result.stderr or "")[-200:]}'
                    ),
                ),
            )

        # 3) create_pr via adapter (usa la misma via que el ToolRegistry)
        # Build task for PR creation authorization
        pr_task = ToolTask(
            tool_id=self._CARD_ID,
            title=f'create_pr:{head}->{base_name}',
            objective=title_text,
            actions=[],
            metadata={
                'github_action': 'create_pr',
                'github_params': {
                    'title': title_text,
                    'body': str(body or ''),
                    'head': head,
                    'base': base_name,
                    'draft': bool(draft),
                },
            },
            lease_id=lease_id,  # Reuse same lease for PR creation
            action='CREATE_PR',  # Canonical action for PR creation
            target=target,  # Reuse same target
            execution_id=f'create_pr_{head}_{int(self._clock())}',
        )
        
        # F17: Authorize PR creation BEFORE executing PR creation
        # ACTION: CREATE_PR
        # TARGET: github_remote:{remote}
        pr_auth_result = self.capability_action_bridge.authorize_action(
            lease_id=pr_task.lease_id,
            requested_action=pr_task.action,
            requested_target=pr_task.target,
            execution_id=pr_task.execution_id,
        )
        if not pr_auth_result.authorized:
            # Authorization failed - reject PR creation (fail-closed)
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=True,  # git push already succeeded
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    error=f"PR creation authorization failed: {pr_auth_result.error or 'Unknown error'}",
                ),
            )
        
        evidence['pr_authorization'] = {
            'authorized': pr_auth_result.authorized,
            'action': pr_task.action,
            'target': pr_task.target,
            'lease_id': pr_task.lease_id,
        }
        
        api_response = self.adapter.run(card, pr_task, sandbox=False)
        evidence['api'] = {
            'success': bool(api_response.get('success')),
            'http_status': api_response.get('metadata', {}).get('github_http_status'),
            'error_message': api_response.get('error_message', ''),
        }

        if not api_response.get('success'):
            return self._finalize(
                evidence,
                PublishResult(
                    success=False, branch=head, base=base_name,
                    pushed=True,
                    required_approval=required_approval,
                    approval_granted=approval_granted,
                    http_status=api_response.get('metadata', {}).get('github_http_status'),
                    error=api_response.get('error_message') or 'create_pr fallo.',
                ),
            )

        data = api_response.get('extracted_data') or {}
        pr_number = data.get('number') if isinstance(data.get('number'), int) else None
        pr_url = str(data.get('html_url') or api_response.get('output_text') or '')

        return self._finalize(
            evidence,
            PublishResult(
                success=True, branch=head, base=base_name,
                pushed=True,
                required_approval=required_approval,
                approval_granted=approval_granted,
                pr_number=pr_number,
                pr_url=pr_url,
                http_status=api_response.get('metadata', {}).get('github_http_status'),
            ),
        )

    # ---- internals ---------------------------------------------------

    def _finalize(self, evidence: dict[str, Any], result: PublishResult) -> PublishResult:
        """Guarda evidencia en disco y devuelve el resultado enriquecido.

        La evidencia queda en ``{evidence_dir}/<ts>-<uuid>.json`` incluso si
        el PR no se creo; es la fuente de auditoria para
        ``OperationalSelfExaminationService``.
        """
        try:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            return PublishResult(
                success=result.success,
                branch=result.branch, base=result.base,
                pr_number=result.pr_number, pr_url=result.pr_url,
                http_status=result.http_status, pushed=result.pushed,
                blocked_by_policy=result.blocked_by_policy,
                required_approval=result.required_approval,
                approval_granted=result.approval_granted,
                error=result.error or f'evidence_dir no accesible: {exc}',
                evidence_path='',
            )

        file_id = uuid.uuid4().hex[:12]
        ts = int(evidence.get('requested_at_epoch') or self._clock())
        target = self.evidence_dir / f'{ts}-{file_id}.json'
        snapshot: dict[str, Any] = dict(evidence)
        snapshot['result'] = {
            'success': result.success,
            'pr_number': result.pr_number,
            'pr_url': result.pr_url,
            'http_status': result.http_status,
            'pushed': result.pushed,
            'blocked_by_policy': result.blocked_by_policy,
            'required_approval': result.required_approval,
            'approval_granted': result.approval_granted,
            'error': result.error,
        }
        try:
            target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
            evidence_path = str(target)
        except Exception as exc:  # noqa: BLE001
            evidence_path = ''
            if not result.error:
                result = PublishResult(
                    success=result.success,
                    branch=result.branch, base=result.base,
                    pr_number=result.pr_number, pr_url=result.pr_url,
                    http_status=result.http_status, pushed=result.pushed,
                    blocked_by_policy=result.blocked_by_policy,
                    required_approval=result.required_approval,
                    approval_granted=result.approval_granted,
                    error=f'no se pudo guardar evidencia: {exc}',
                    evidence_path='',
                )

        return PublishResult(
            success=result.success,
            branch=result.branch, base=result.base,
            pr_number=result.pr_number, pr_url=result.pr_url,
            http_status=result.http_status, pushed=result.pushed,
            blocked_by_policy=result.blocked_by_policy,
            required_approval=result.required_approval,
            approval_granted=result.approval_granted,
            error=result.error,
            evidence_path=evidence_path,
        )
