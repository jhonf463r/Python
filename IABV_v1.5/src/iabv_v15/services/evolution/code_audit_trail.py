"""Code audit trail — registro persistente de auditorías de código.

Registra cada ronda de auditoría realizada sobre el código fuente de IABV,
sea por un agente externo (Devin, Codex), por la autoexaminación interna
(OSES) o por el usuario humano.

Propósito:
- Saber qué se auditó, cuándo, por quién y en qué entorno
- Detectar patrones de bugs recurrentes entre rondas
- Identificar qué necesita verificación cruzada (Linux vs Windows)
- Alimentar el contexto portable para que sesiones nuevas no repitan trabajo
- Permitir que IABV aprenda de sus propias auditorías

Arquitectura:
- Append-only JSONL en ``data/evolution/code_audits/``
- NO es otro orquestador — puramente observacional y analítico
- Consumido por OperationalSelfExaminationService y PortableContextService
- Expuesto vía MCP para que agentes externos registren hallazgos
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AuditSource(str, Enum):
    EXTERNAL_AGENT = 'external_agent'
    SELF_EXAMINATION = 'self_examination'
    HUMAN = 'human'


class AuditEnvironment(str, Enum):
    LINUX_VM = 'linux_vm'
    WINDOWS_NATIVE = 'windows_native'
    UNKNOWN = 'unknown'


class FindingSeverity(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class FindingStatus(str, Enum):
    FOUND = 'found'
    FIXED = 'fixed'
    UNRESOLVED = 'unresolved'
    WONT_FIX = 'wont_fix'
    NEEDS_CROSS_VERIFICATION = 'needs_cross_verification'


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

class AuditFinding:
    """A single finding from an audit round."""

    __slots__ = (
        'finding_id', 'round_id', 'bug_id',
        'module_path', 'line_range', 'category',
        'title', 'description', 'impact',
        'severity', 'status', 'fix_description',
        'pr_url', 'pattern_tag',
        'needs_windows_verification', 'needs_linux_verification',
        'confidence', 'metadata',
    )

    def __init__(
        self,
        *,
        finding_id: str = '',
        round_id: str = '',
        bug_id: str = '',
        module_path: str = '',
        line_range: str = '',
        category: str = '',
        title: str = '',
        description: str = '',
        impact: str = '',
        severity: FindingSeverity = FindingSeverity.MEDIUM,
        status: FindingStatus = FindingStatus.FOUND,
        fix_description: str = '',
        pr_url: str = '',
        pattern_tag: str = '',
        needs_windows_verification: bool = False,
        needs_linux_verification: bool = False,
        confidence: float = 0.9,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.finding_id = finding_id or str(uuid4())[:8]
        self.round_id = round_id
        self.bug_id = bug_id
        self.module_path = module_path
        self.line_range = line_range
        self.category = category
        self.title = title
        self.description = description
        self.impact = impact
        self.severity = severity
        self.status = status
        self.fix_description = fix_description
        self.pr_url = pr_url
        self.pattern_tag = pattern_tag
        self.needs_windows_verification = needs_windows_verification
        self.needs_linux_verification = needs_linux_verification
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            'finding_id': self.finding_id,
            'round_id': self.round_id,
            'bug_id': self.bug_id,
            'module_path': self.module_path,
            'line_range': self.line_range,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'severity': self.severity.value,
            'status': self.status.value,
            'fix_description': self.fix_description,
            'pr_url': self.pr_url,
            'pattern_tag': self.pattern_tag,
            'needs_windows_verification': self.needs_windows_verification,
            'needs_linux_verification': self.needs_linux_verification,
            'confidence': self.confidence,
            'metadata': self.metadata,
        }


class AuditRound:
    """One complete audit cycle (ronda)."""

    __slots__ = (
        'round_id', 'round_number', 'timestamp_utc',
        'auditor_name', 'auditor_session_url',
        'source', 'environment',
        'modules_audited', 'total_loc_audited',
        'findings', 'tests_added', 'tests_passed', 'tests_failed',
        'pr_url', 'ci_status',
        'unresolved_items',
        'metadata',
    )

    def __init__(
        self,
        *,
        round_id: str = '',
        round_number: int = 0,
        auditor_name: str = '',
        auditor_session_url: str = '',
        source: AuditSource = AuditSource.EXTERNAL_AGENT,
        environment: AuditEnvironment = AuditEnvironment.UNKNOWN,
        modules_audited: list[str] | None = None,
        total_loc_audited: int = 0,
        findings: list[AuditFinding] | None = None,
        tests_added: int = 0,
        tests_passed: int = 0,
        tests_failed: int = 0,
        pr_url: str = '',
        ci_status: str = '',
        unresolved_items: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.round_id = round_id or str(uuid4())[:12]
        self.round_number = round_number
        self.timestamp_utc = now.isoformat()
        self.auditor_name = auditor_name
        self.auditor_session_url = auditor_session_url
        self.source = source
        self.environment = environment
        self.modules_audited = modules_audited or []
        self.total_loc_audited = total_loc_audited
        self.findings = findings or []
        self.tests_added = tests_added
        self.tests_passed = tests_passed
        self.tests_failed = tests_failed
        self.pr_url = pr_url
        self.ci_status = ci_status
        self.unresolved_items = unresolved_items or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            'round_id': self.round_id,
            'round_number': self.round_number,
            'timestamp_utc': self.timestamp_utc,
            'auditor_name': self.auditor_name,
            'auditor_session_url': self.auditor_session_url,
            'source': self.source.value,
            'environment': self.environment.value,
            'modules_audited': self.modules_audited,
            'total_loc_audited': self.total_loc_audited,
            'findings': [f.to_dict() for f in self.findings],
            'findings_count': len(self.findings),
            'bugs_found': sum(1 for f in self.findings if f.status == FindingStatus.FIXED),
            'tests_added': self.tests_added,
            'tests_passed': self.tests_passed,
            'tests_failed': self.tests_failed,
            'pr_url': self.pr_url,
            'ci_status': self.ci_status,
            'unresolved_items': self.unresolved_items,
            'metadata': self.metadata,
        }


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

class BugPatternTrend:
    """Aggregated trend for a recurring bug pattern across rounds."""

    __slots__ = (
        'pattern_tag', 'occurrences', 'affected_modules',
        'first_seen_round', 'last_seen_round',
        'all_fixed', 'description',
    )

    def __init__(
        self,
        *,
        pattern_tag: str,
        occurrences: int = 0,
        affected_modules: list[str] | None = None,
        first_seen_round: int = 0,
        last_seen_round: int = 0,
        all_fixed: bool = True,
        description: str = '',
    ) -> None:
        self.pattern_tag = pattern_tag
        self.occurrences = occurrences
        self.affected_modules = affected_modules or []
        self.first_seen_round = first_seen_round
        self.last_seen_round = last_seen_round
        self.all_fixed = all_fixed
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        return {
            'pattern_tag': self.pattern_tag,
            'occurrences': self.occurrences,
            'affected_modules': self.affected_modules,
            'first_seen_round': self.first_seen_round,
            'last_seen_round': self.last_seen_round,
            'all_fixed': self.all_fixed,
            'description': self.description,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CodeAuditTrail:
    """Append-only audit trail for code audits.

    Persists to ``data/evolution/code_audits/rounds.jsonl``.
    Provides pattern analysis, cross-audit insights, and portable
    summaries for new sessions.

    NOT another orchestrator — purely observational.
    Consumed by OperationalSelfExaminationService and PortableContextService.
    """

    def __init__(self, *, data_root: str | Path = '') -> None:
        import os
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_root:
            self._data_root = Path(data_root)
        elif env_dir:
            self._data_root = Path(env_dir)
        else:
            self._data_root = Path.home() / 'IABV_v1.5' / 'data'
        self.experiment_lab: Any | None = None

    @property
    def _audit_dir(self) -> Path:
        d = self._data_root / 'evolution' / 'code_audits'
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def _log_path(self) -> Path:
        return self._audit_dir / 'rounds.jsonl'

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record_round(self, audit_round: AuditRound) -> None:
        """Append a complete audit round to the trail."""
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_round.to_dict(), ensure_ascii=False) + '\n')
        bugs = sum(1 for f in audit_round.findings if f.status == FindingStatus.FIXED)
        logger.info(
            'code-audit-trail: recorded round %d [%s] modules=%d loc=%d bugs=%d tests_added=%d',
            audit_round.round_number, audit_round.auditor_name,
            len(audit_round.modules_audited), audit_round.total_loc_audited,
            bugs, audit_round.tests_added,
        )
        self._publish_to_experiment_lab(audit_round)

    def _publish_to_experiment_lab(self, audit_round: AuditRound) -> None:
        """Publish audit round as ExperimentRun so ExperimentLab can
        compare auditor effectiveness across assistant_kinds.

        Each auditor (devin, codex, iabv_self, human) gets scored by:
        - precision: bugs found / modules audited (detection rate)
        - robustness: tests added / bugs found (coverage depth)
        - execution_ms: LOC audited (throughput proxy)
        """
        lab = self.experiment_lab
        if lab is None:
            return
        try:
            from iabv_v15.domain.models import (
                EvaluationRoute,
                ExperimentDomain,
            )
            bugs_found = sum(
                1 for f in audit_round.findings
                if f.status == FindingStatus.FIXED
            )
            modules_count = max(len(audit_round.modules_audited), 1)
            precision = min(bugs_found / modules_count, 1.0)
            robustness = (
                min(audit_round.tests_added / max(bugs_found, 1), 1.0)
                if audit_round.tests_added > 0
                else 0.0
            )
            lab.record_outcome(
                domain=ExperimentDomain.CODE_AUDIT,
                objective=f'audit_round_{audit_round.round_number}',
                subject_key=f'code_audit:{audit_round.auditor_name or "unknown"}',
                route=EvaluationRoute.CODE_AUDIT,
                candidate_label=audit_round.auditor_name or 'unknown',
                success=bugs_found > 0 or len(audit_round.findings) == 0,
                observed_summary=(
                    f'R{audit_round.round_number}: {bugs_found} bugs in '
                    f'{modules_count} modules, {audit_round.total_loc_audited} LOC, '
                    f'{audit_round.tests_added} tests added'
                ),
                precision=precision,
                robustness=robustness,
                execution_ms=audit_round.total_loc_audited,
                evidence_refs=[audit_round.pr_url] if audit_round.pr_url else [],
                suite_name='code_audit',
                metadata={
                    'assistant_kind': audit_round.auditor_name or 'unknown',
                    'comparison_scope_key': 'code_audit',
                    'round_number': audit_round.round_number,
                    'environment': audit_round.environment.value,
                    'source': audit_round.source.value,
                    'modules_audited': audit_round.modules_audited[:10],
                    'bugs_found': bugs_found,
                    'findings_count': len(audit_round.findings),
                    'tests_added': audit_round.tests_added,
                    'pattern_tags': list({
                        f.pattern_tag for f in audit_round.findings
                        if f.pattern_tag
                    }),
                },
            )
        except Exception as exc:
            logger.warning('code-audit-trail: failed to publish to ExperimentLab: %s', exc)

    def record_finding(
        self,
        *,
        round_id: str = '',
        round_number: int = 0,
        auditor_name: str = '',
        source: str = 'external_agent',
        environment: str = 'unknown',
        module_path: str = '',
        line_range: str = '',
        category: str = '',
        bug_id: str = '',
        title: str = '',
        description: str = '',
        impact: str = '',
        severity: str = 'medium',
        status: str = 'found',
        fix_description: str = '',
        pr_url: str = '',
        pattern_tag: str = '',
        needs_windows_verification: bool = False,
        needs_linux_verification: bool = False,
        confidence: float = 0.9,
    ) -> dict[str, Any]:
        """Register a single finding (convenience for MCP consumers).

        Creates a minimal AuditRound with one finding and appends it.
        Returns the finding dict for confirmation.
        """
        finding = AuditFinding(
            round_id=round_id,
            bug_id=bug_id,
            module_path=module_path,
            line_range=line_range,
            category=category,
            title=title,
            description=description,
            impact=impact,
            severity=FindingSeverity(severity) if severity in FindingSeverity.__members__.values() else FindingSeverity.MEDIUM,
            status=FindingStatus(status) if status in FindingStatus.__members__.values() else FindingStatus.FOUND,
            fix_description=fix_description,
            pr_url=pr_url,
            pattern_tag=pattern_tag,
            needs_windows_verification=needs_windows_verification,
            needs_linux_verification=needs_linux_verification,
            confidence=confidence,
        )
        audit_round = AuditRound(
            round_id=round_id or finding.finding_id,
            round_number=round_number,
            auditor_name=auditor_name,
            source=AuditSource(source) if source in AuditSource.__members__.values() else AuditSource.EXTERNAL_AGENT,
            environment=AuditEnvironment(environment) if environment in AuditEnvironment.__members__.values() else AuditEnvironment.UNKNOWN,
            modules_audited=[module_path] if module_path else [],
            findings=[finding],
        )
        self.record_round(audit_round)
        return finding.to_dict()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_rounds(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load the most recent audit rounds."""
        if not self._log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries[-limit:]

    def load_all_findings(self, limit: int = 200) -> list[dict[str, Any]]:
        """Flatten all findings from all rounds."""
        rounds = self.load_rounds(limit=limit)
        findings: list[dict[str, Any]] = []
        for r in rounds:
            for f in (r.get('findings') or []):
                f['round_number'] = r.get('round_number', 0)
                f['auditor_name'] = r.get('auditor_name', '')
                f['source'] = r.get('source', '')
                f['environment'] = r.get('environment', '')
                f['round_timestamp'] = r.get('timestamp_utc', '')
                findings.append(f)
        return findings[-limit:]

    def pending_cross_verifications(self) -> list[dict[str, Any]]:
        """Return findings that need verification on a different environment."""
        findings = self.load_all_findings()
        return [
            f for f in findings
            if f.get('needs_windows_verification') or f.get('needs_linux_verification')
        ]

    # ------------------------------------------------------------------
    # Pattern analysis
    # ------------------------------------------------------------------

    def analyze_bug_patterns(self) -> list[dict[str, Any]]:
        """Detect recurring bug patterns across audit rounds."""
        findings = self.load_all_findings()
        if not findings:
            return []

        by_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for f in findings:
            tag = f.get('pattern_tag', '').strip()
            if not tag:
                tag = f.get('category', '').strip()
            if tag:
                by_pattern[tag].append(f)

        trends: list[BugPatternTrend] = []
        for pattern_tag, items in by_pattern.items():
            modules = list({f.get('module_path', '') for f in items if f.get('module_path')})
            round_numbers = [f.get('round_number', 0) for f in items]
            all_fixed = all(f.get('status') == 'fixed' for f in items)
            descriptions = [f.get('title', '') for f in items if f.get('title')]

            trends.append(BugPatternTrend(
                pattern_tag=pattern_tag,
                occurrences=len(items),
                affected_modules=modules,
                first_seen_round=min(round_numbers) if round_numbers else 0,
                last_seen_round=max(round_numbers) if round_numbers else 0,
                all_fixed=all_fixed,
                description='; '.join(descriptions[:3]),
            ))

        trends.sort(key=lambda t: t.occurrences, reverse=True)
        return [t.to_dict() for t in trends]

    def audit_coverage_summary(self) -> dict[str, Any]:
        """Summary of what has been audited and what hasn't."""
        rounds = self.load_rounds()
        if not rounds:
            return {
                'total_rounds': 0,
                'total_loc_audited': 0,
                'total_bugs_found': 0,
                'total_bugs_fixed': 0,
                'modules_audited': [],
                'auditors': [],
                'environments_used': [],
                'pending_cross_verifications': 0,
            }

        all_modules: list[str] = []
        total_loc = 0
        total_bugs_found = 0
        total_bugs_fixed = 0
        total_tests_added = 0
        auditors: set[str] = set()
        environments: set[str] = set()
        sources: set[str] = set()

        for r in rounds:
            all_modules.extend(r.get('modules_audited', []))
            total_loc += r.get('total_loc_audited', 0)
            total_bugs_found += len(r.get('findings', []))
            total_bugs_fixed += r.get('bugs_found', 0)
            total_tests_added += r.get('tests_added', 0)
            if r.get('auditor_name'):
                auditors.add(r['auditor_name'])
            if r.get('environment'):
                environments.add(r['environment'])
            if r.get('source'):
                sources.add(r['source'])

        module_counts = Counter(all_modules)
        unique_modules = list(module_counts.keys())
        cross_verifications = self.pending_cross_verifications()

        return {
            'total_rounds': len(rounds),
            'total_loc_audited': total_loc,
            'total_bugs_found': total_bugs_found,
            'total_bugs_fixed': total_bugs_fixed,
            'total_tests_added': total_tests_added,
            'modules_audited': unique_modules,
            'modules_audit_count': dict(module_counts.most_common(20)),
            'auditors': sorted(auditors),
            'environments_used': sorted(environments),
            'sources_used': sorted(sources),
            'pending_cross_verifications': len(cross_verifications),
            'latest_round': rounds[-1].get('round_number', 0) if rounds else 0,
        }

    # ------------------------------------------------------------------
    # Summary for portable context and OSES
    # ------------------------------------------------------------------

    def summary_for_portable_context(self) -> dict[str, Any]:
        """Build a compact summary suitable for PortableContextService."""
        coverage = self.audit_coverage_summary()
        patterns = self.analyze_bug_patterns()
        cross_verifications = self.pending_cross_verifications()

        recent_rounds = self.load_rounds(limit=5)
        recent_items: list[dict[str, Any]] = []
        for r in recent_rounds:
            bugs = r.get('bugs_found', 0)
            modules = r.get('modules_audited', [])
            recent_items.append({
                'round_number': r.get('round_number', 0),
                'auditor': r.get('auditor_name', ''),
                'source': r.get('source', ''),
                'environment': r.get('environment', ''),
                'modules': modules[:4],
                'bugs_found': bugs,
                'loc_audited': r.get('total_loc_audited', 0),
                'pr_url': r.get('pr_url', ''),
                'timestamp': r.get('timestamp_utc', ''),
            })

        return {
            'coverage': coverage,
            'recurring_patterns': patterns[:5],
            'recent_rounds': recent_items,
            'pending_cross_verifications': [
                {
                    'finding_id': f.get('finding_id', ''),
                    'title': f.get('title', ''),
                    'module_path': f.get('module_path', ''),
                    'needs_windows': f.get('needs_windows_verification', False),
                    'needs_linux': f.get('needs_linux_verification', False),
                }
                for f in cross_verifications[:5]
            ],
        }

    def findings_for_oses_cross_reference(self) -> list[dict[str, Any]]:
        """Return findings formatted for OSES pattern cross-referencing.

        OSES can compare these with its own findings to detect:
        - Bugs that Devin found statically but IABV hasn't seen at runtime
        - Patterns that IABV detects at runtime but Devin missed statically
        - Modules that both flagged independently (high confidence)
        """
        findings = self.load_all_findings(limit=50)
        return [
            {
                'finding_id': f.get('finding_id', ''),
                'round_number': f.get('round_number', 0),
                'auditor': f.get('auditor_name', ''),
                'source': f.get('source', ''),
                'environment': f.get('environment', ''),
                'module_path': f.get('module_path', ''),
                'category': f.get('category', ''),
                'pattern_tag': f.get('pattern_tag', ''),
                'title': f.get('title', ''),
                'severity': f.get('severity', ''),
                'status': f.get('status', ''),
                'needs_windows_verification': f.get('needs_windows_verification', False),
                'needs_linux_verification': f.get('needs_linux_verification', False),
            }
            for f in findings
        ]

    # ------------------------------------------------------------------
    # Auditor performance comparison
    # ------------------------------------------------------------------

    def auditor_performance_summary(self) -> dict[str, Any]:
        """Compare auditor effectiveness across all registered rounds.

        Groups by auditor_name and computes per-auditor metrics:
        - rounds: how many audit rounds this auditor did
        - bugs_found: total bugs found and fixed
        - loc_audited: total lines of code reviewed
        - detection_rate: bugs / modules (how effective at finding bugs)
        - tests_added: total tests contributed
        - coverage_depth: tests_added / bugs_found (testing rigor)
        - pattern_specialties: which pattern_tags this auditor finds most
        - environments: which environments this auditor covers
        - categories: which bug categories this auditor detects

        This feeds ExperimentLab's comparison_scope_key='code_audit'
        so StrategySelector can recommend the best auditor per task.
        """
        rounds = self.load_rounds()
        if not rounds:
            return {
                'auditors': {},
                'comparison': [],
                'recommendation': 'Sin datos de auditoria registrados.',
            }

        by_auditor: dict[str, dict[str, Any]] = {}
        for r in rounds:
            auditor = r.get('auditor_name', 'unknown') or 'unknown'
            if auditor not in by_auditor:
                by_auditor[auditor] = {
                    'rounds': 0,
                    'bugs_found': 0,
                    'findings_total': 0,
                    'loc_audited': 0,
                    'modules_audited': [],
                    'tests_added': 0,
                    'environments': set(),
                    'sources': set(),
                    'pattern_tags': Counter(),
                    'categories': Counter(),
                    'severities': Counter(),
                }
            stats = by_auditor[auditor]
            stats['rounds'] += 1
            stats['bugs_found'] += r.get('bugs_found', 0)
            stats['findings_total'] += len(r.get('findings', []))
            stats['loc_audited'] += r.get('total_loc_audited', 0)
            stats['modules_audited'].extend(r.get('modules_audited', []))
            stats['tests_added'] += r.get('tests_added', 0)
            if r.get('environment'):
                stats['environments'].add(r['environment'])
            if r.get('source'):
                stats['sources'].add(r['source'])
            for f in r.get('findings', []):
                if f.get('pattern_tag'):
                    stats['pattern_tags'][f['pattern_tag']] += 1
                if f.get('category'):
                    stats['categories'][f['category']] += 1
                if f.get('severity'):
                    stats['severities'][f['severity']] += 1

        auditor_summaries: dict[str, dict[str, Any]] = {}
        for auditor, stats in by_auditor.items():
            unique_modules = list(set(stats['modules_audited']))
            modules_count = max(len(unique_modules), 1)
            bugs = stats['bugs_found']
            detection_rate = bugs / modules_count if modules_count > 0 else 0.0
            coverage_depth = (
                stats['tests_added'] / max(bugs, 1)
                if stats['tests_added'] > 0
                else 0.0
            )
            auditor_summaries[auditor] = {
                'rounds': stats['rounds'],
                'bugs_found': bugs,
                'findings_total': stats['findings_total'],
                'loc_audited': stats['loc_audited'],
                'modules_audited': len(unique_modules),
                'unique_modules': unique_modules[:20],
                'tests_added': stats['tests_added'],
                'detection_rate': round(detection_rate, 3),
                'coverage_depth': round(coverage_depth, 2),
                'environments': sorted(stats['environments']),
                'sources': sorted(stats['sources']),
                'pattern_specialties': dict(stats['pattern_tags'].most_common(5)),
                'category_distribution': dict(stats['categories'].most_common(5)),
                'severity_distribution': dict(stats['severities'].most_common()),
            }

        comparison: list[dict[str, Any]] = []
        for auditor, summary in sorted(
            auditor_summaries.items(),
            key=lambda x: x[1]['bugs_found'],
            reverse=True,
        ):
            comparison.append({
                'auditor': auditor,
                'bugs_found': summary['bugs_found'],
                'detection_rate': summary['detection_rate'],
                'loc_audited': summary['loc_audited'],
                'tests_added': summary['tests_added'],
                'coverage_depth': summary['coverage_depth'],
                'pattern_specialties': list(summary['pattern_specialties'].keys()),
                'environments': summary['environments'],
            })

        if len(comparison) >= 2:
            best = comparison[0]
            recommendation = (
                f"{best['auditor']} lidera con {best['bugs_found']} bugs encontrados "
                f"y detection_rate {best['detection_rate']}. "
                f"Especialidades: {', '.join(best['pattern_specialties'][:3])}."
            )
        elif len(comparison) == 1:
            only = comparison[0]
            recommendation = (
                f"Solo {only['auditor']} ha auditado hasta ahora. "
                f"Agregar mas auditores para comparar efectividad."
            )
        else:
            recommendation = 'Sin datos de auditoria registrados.'

        return {
            'auditors': auditor_summaries,
            'comparison': comparison,
            'recommendation': recommendation,
        }
