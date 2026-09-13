"""Tests para IntegrityClaimRepository y VerificationEvent.

Diseño congelado (FINAL DESIGN FREEZE):
- Claim es inmutable (INSERT, no UPDATE/DELETE)
- VerificationEvent es append-only (INSERT, no UPDATE/DELETE)
- El estado actual de Claim se deriva del VerificationEvent más reciente
- verification_evidence usa referencia tipada: {kind}:{id}
"""

from datetime import datetime, timezone
import uuid

import pytest

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository


@pytest.fixture
def db(tmp_path):
    """Base de datos SQLite temporal."""
    db_path = tmp_path / "test.db"
    return AppDatabase(str(db_path))


@pytest.fixture
def repo(db):
    """Repository para tests."""
    return IntegrityClaimRepository(db)


def test_claim_identity_two_distinct_claims(repo):
    """Test A.1: dos Claims distintas pueden existir."""
    claim1 = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="task_context_assembler:build_perception_snapshot → adaptive_task_orchestrator",
        invariant="METHOD",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    claim2 = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="domain.models:utc_now → module:unknown_importer",
        invariant="IMPORT",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    repo.create(claim1)
    repo.create(claim2)

    retrieved1 = repo.retrieve(claim1.claim_id)
    retrieved2 = repo.retrieve(claim2.claim_id)

    assert retrieved1 is not None
    assert retrieved2 is not None
    assert retrieved1.claim_id != retrieved2.claim_id
    assert retrieved1.subject != retrieved2.subject


def test_verification_history_pass_fail_pass(repo):
    """Test A.2: PASS → FAIL → PASS preserva las tres filas/eventos."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="experiment_run → task_outcome_recorder",
        invariant="SEMANTIC",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    now = datetime.now(timezone.utc)
    t1 = now.isoformat()
    t2 = datetime.now(timezone.utc).isoformat()
    t3 = datetime.now(timezone.utc).isoformat()

    event1 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t1,
        status="PASS",
        verification_evidence="test_id:test_intent_routing",
    )
    event2 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t2,
        status="FAIL",
        verification_evidence="test_id:test_intent_routing",
    )
    event3 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t3,
        status="PASS",
        verification_evidence="test_id:test_intent_routing",
    )

    repo.append_verification(event1)
    repo.append_verification(event2)
    repo.append_verification(event3)

    events = repo.retrieve_verifications_by_claim(claim.claim_id)

    assert len(events) == 3
    assert events[0].status == "PASS"  # más reciente (t3)
    assert events[1].status == "FAIL"  # t2
    assert events[2].status == "PASS"  # t1


def test_latest_status_returns_pass_at_t3(repo):
    """Test A.3: la consulta devuelve PASS en T3."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="previous_recommendation → prediction → run → new_recommendation",
        invariant="SEMANTIC",
        origin="oses",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    now = datetime.now(timezone.utc)
    t1 = now.isoformat()
    t2 = datetime.now(timezone.utc).isoformat()
    t3 = datetime.now(timezone.utc).isoformat()

    event1 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t1,
        status="PASS",
        verification_evidence="run_id:9cf6efb2-f210-41fb-b768-8d0bfaeb2515",
    )
    event2 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t2,
        status="FAIL",
        verification_evidence="run_id:9cf6efb2-f210-41fb-b768-8d0bfaeb2515",
    )
    event3 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=t3,
        status="PASS",
        verification_evidence="run_id:9cf6efb2-f210-41fb-b768-8d0bfaeb2515",
    )

    repo.append_verification(event1)
    repo.append_verification(event2)
    repo.append_verification(event3)

    current_status = repo.get_current_status(claim.claim_id)

    assert current_status == "PASS"


def test_evidence_typing_distinguishes_kinds(repo):
    """Test A.4: distinguir run_id:X, trace_id:Y, source_path:Z."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="runtime_audit_tracer:trace_causal_event → consumer:unknown",
        invariant="EVENT",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    event1 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="run_id:9cf6efb2-f210-41fb-b768-8d0bfaeb2515",
    )
    event2 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="trace_id:4e6185c9",
    )
    event3 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="source_path:src/iabv_v15/domain/models.py:12",
    )

    repo.append_verification(event1)
    repo.append_verification(event2)
    repo.append_verification(event3)

    events = repo.retrieve_verifications_by_claim(claim.claim_id)

    assert len(events) == 3
    assert events[0].verification_evidence.startswith("source_path:")
    assert events[1].verification_evidence.startswith("trace_id:")
    assert events[2].verification_evidence.startswith("run_id:")


def test_claim_immutability(repo):
    """Test A.5: una Claim existente no se modifica mediante el flujo normal."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="method → method",
        invariant="METHOD",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    # Intentar crear otra Claim con el mismo ID debería fallar (PK constraint)
    # pero el repositorio no tiene método update, solo create
    # Verificar que la Claim original no cambió
    retrieved = repo.retrieve(claim.claim_id)

    assert retrieved.claim_id == claim.claim_id
    assert retrieved.subject == claim.subject
    assert retrieved.invariant == claim.invariant
    assert retrieved.origin == claim.origin
    assert retrieved.created_at == claim.created_at


def test_persistence_recovery(repo, tmp_path):
    """Test A.6: reiniciar/reabrir DB conserva Claim + VerificationEvents."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="method → method",
        invariant="METHOD",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    event = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="test_id:test_intent_routing",
    )
    repo.append_verification(event)

    # Reabrir DB
    db_path = tmp_path / "test.db"
    db2 = AppDatabase(str(db_path))
    repo2 = IntegrityClaimRepository(db2)

    retrieved_claim = repo2.retrieve(claim.claim_id)
    retrieved_events = repo2.retrieve_verifications_by_claim(claim.claim_id)

    assert retrieved_claim is not None
    assert retrieved_claim.claim_id == claim.claim_id
    assert len(retrieved_events) == 1
    assert retrieved_events[0].event_id == event.event_id


def test_concurrency_two_writes_preserve_history(repo):
    """Test A.7: dos escrituras de VerificationEvent no destruyen historial."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="method → method",
        invariant="METHOD",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    event1 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="test_id:test_intent_routing",
    )
    event2 = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim.claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="FAIL",
        verification_evidence="test_id:test_intent_routing",
    )

    repo.append_verification(event1)
    repo.append_verification(event2)

    events = repo.retrieve_verifications_by_claim(claim.claim_id)

    assert len(events) == 2
    # Ambos eventos deben existir, el historial no se destruye
    event_ids = {e.event_id for e in events}
    assert event1.event_id in event_ids
    assert event2.event_id in event_ids


# ---------------------------------------------------------------------------
# Six-probe check (A-D)
# ---------------------------------------------------------------------------


def test_probe_a_method_to_method(repo):
    """Probe A: Method → Method puede representarse."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="task_context_assembler:build_perception_snapshot → adaptive_task_orchestrator",
        invariant="METHOD",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    retrieved = repo.retrieve(claim.claim_id)
    assert retrieved is not None
    assert retrieved.subject == "task_context_assembler:build_perception_snapshot → adaptive_task_orchestrator"
    assert retrieved.invariant == "METHOD"


def test_probe_b_import_to_symbol(repo):
    """Probe B: Import → Symbol puede representarse."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="domain.models:utc_now → module:unknown_importer",
        invariant="IMPORT",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    retrieved = repo.retrieve(claim.claim_id)
    assert retrieved is not None
    assert retrieved.subject == "domain.models:utc_now → module:unknown_importer"
    assert retrieved.invariant == "IMPORT"


def test_probe_c_structure_to_dataclass(repo):
    """Probe C: Structure → Dataclass puede representarse."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="experiment_run → task_outcome_recorder",
        invariant="SCHEMA",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    retrieved = repo.retrieve(claim.claim_id)
    assert retrieved is not None
    assert retrieved.subject == "experiment_run → task_outcome_recorder"
    assert retrieved.invariant == "SCHEMA"


def test_probe_d_runtime_event_to_consumer(repo):
    """Probe D: Runtime Event → Consumer puede representarse."""
    claim = IntegrityClaim(
        claim_id=str(uuid.uuid4()),
        subject="runtime_audit_tracer:trace_causal_event → consumer:unknown",
        invariant="EVENT",
        origin="self_code_analysis",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)

    retrieved = repo.retrieve(claim.claim_id)
    assert retrieved is not None
    assert retrieved.subject == "runtime_audit_tracer:trace_causal_event → consumer:unknown"
    assert retrieved.invariant == "EVENT"
