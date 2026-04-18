from __future__ import annotations

from iabv_v15.domain.models import ApprovalCheckpoint, IssueSeverity, StrategyCandidate, StrategyPack, TaskIntent


class ApprovalGateService:
    def evaluate(
        self,
        *,
        intent: TaskIntent,
        pack: StrategyPack,
        strategy_candidates: list[StrategyCandidate],
    ) -> list[ApprovalCheckpoint]:
        checkpoints: list[ApprovalCheckpoint] = []
        requires_strategy = pack.approval_policy != 'never' or any(item.requires_approval for item in strategy_candidates)
        if requires_strategy:
            checkpoints.append(
                ApprovalCheckpoint(
                    title='Aprobar estrategia',
                    detail=f'Se propone {strategy_candidates[0].title if strategy_candidates else pack.title} antes de pasar a la fase operativa.',
                    phase_key='strategy',
                    reason='El flujo requiere confirmacion humana antes de seguir.',
                    risk_level=pack.risk_level,
                )
            )
        if intent.sensitive or intent.monetary:
            checkpoints.append(
                ApprovalCheckpoint(
                    title='Aprobar fase critica',
                    detail='La siguiente fase toca login sensible, dinero o una accion operativa delicada.',
                    phase_key='execute_sensitive',
                    reason='No se omiten checkpoints explicitos en acciones sensibles o monetarias.',
                    risk_level=IssueSeverity.CRITICAL if intent.monetary else IssueSeverity.HIGH,
                )
            )
        return checkpoints
