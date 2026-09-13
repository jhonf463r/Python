from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase


class IntegrityClaimRepository:
    """Repository para Claims y VerificationEvents.

    Diseño congelado (FINAL DESIGN FREEZE):
    - Claim es inmutable (INSERT, no UPDATE/DELETE)
    - VerificationEvent es append-only (INSERT, no UPDATE/DELETE)
    - El estado actual de Claim se deriva del VerificationEvent más reciente
    """

    def __init__(self, db: AppDatabase):
        self.db = db

    # ------------------------------------------------------------------
    # Claim operations

    def create(self, claim: IntegrityClaim) -> IntegrityClaim:
        """Crea una Claim. Claim es inmutable después de creación."""
        self.db.execute(
            """
            INSERT INTO integrity_claims
            (claim_id, subject, invariant, origin, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.subject,
                claim.invariant,
                claim.origin,
                claim.created_at,
            ),
        )
        return claim

    def retrieve(self, claim_id: str) -> Optional[IntegrityClaim]:
        """Recupera una Claim por ID."""
        row = self.db.fetchone(
            "SELECT * FROM integrity_claims WHERE claim_id = ?",
            (claim_id,),
        )
        if not row:
            return None
        return IntegrityClaim(
            claim_id=row["claim_id"],
            subject=row["subject"],
            invariant=row["invariant"],
            origin=row["origin"],
            created_at=row["created_at_utc"],
        )

    def list_by_subject(self, subject: str, limit: int = 50) -> list[IntegrityClaim]:
        """Lista Claims por subject."""
        rows = self.db.fetchall(
            """
            SELECT * FROM integrity_claims
            WHERE subject = ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (subject, limit),
        )
        return [
            IntegrityClaim(
                claim_id=row["claim_id"],
                subject=row["subject"],
                invariant=row["invariant"],
                origin=row["origin"],
                created_at=row["created_at_utc"],
            )
            for row in rows
        ]

    def list_by_invariant(self, invariant: str, limit: int = 50) -> list[IntegrityClaim]:
        """Lista Claims por invariant."""
        rows = self.db.fetchall(
            """
            SELECT * FROM integrity_claims
            WHERE invariant = ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (invariant, limit),
        )
        return [
            IntegrityClaim(
                claim_id=row["claim_id"],
                subject=row["subject"],
                invariant=row["invariant"],
                origin=row["origin"],
                created_at=row["created_at_utc"],
            )
            for row in rows
        ]

    def list_recent(self, limit: int = 50) -> list[IntegrityClaim]:
        """Lista Claims recientes."""
        rows = self.db.fetchall(
            """
            SELECT * FROM integrity_claims
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            IntegrityClaim(
                claim_id=row["claim_id"],
                subject=row["subject"],
                invariant=row["invariant"],
                origin=row["origin"],
                created_at=row["created_at_utc"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # VerificationEvent operations

    def append_verification(self, event: VerificationEvent) -> VerificationEvent:
        """Añade un VerificationEvent. Append-only."""
        self.db.execute(
            """
            INSERT INTO verification_events
            (event_id, claim_id, checked_at_utc, status, verification_evidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.claim_id,
                event.checked_at,
                event.status,
                event.verification_evidence,
            ),
        )
        return event

    def retrieve_verification(self, event_id: str) -> Optional[VerificationEvent]:
        """Recupera un VerificationEvent por ID."""
        row = self.db.fetchone(
            "SELECT * FROM verification_events WHERE event_id = ?",
            (event_id,),
        )
        if not row:
            return None
        return VerificationEvent(
            event_id=row["event_id"],
            claim_id=row["claim_id"],
            checked_at=row["checked_at_utc"],
            status=row["status"],
            verification_evidence=row["verification_evidence"],
        )

    def retrieve_verifications_by_claim(
        self, claim_id: str, limit: int = 100
    ) -> list[VerificationEvent]:
        """Recupera VerificationEvents de una Claim."""
        rows = self.db.fetchall(
            """
            SELECT * FROM verification_events
            WHERE claim_id = ?
            ORDER BY checked_at_utc DESC
            LIMIT ?
            """,
            (claim_id, limit),
        )
        return [
            VerificationEvent(
                event_id=row["event_id"],
                claim_id=row["claim_id"],
                checked_at=row["checked_at_utc"],
                status=row["status"],
                verification_evidence=row["verification_evidence"],
            )
            for row in rows
        ]

    def retrieve_latest_verification(
        self, claim_id: str
    ) -> Optional[VerificationEvent]:
        """Recupera el VerificationEvent más reciente de una Claim."""
        row = self.db.fetchone(
            """
            SELECT * FROM verification_events
            WHERE claim_id = ?
            ORDER BY checked_at_utc DESC
            LIMIT 1
            """,
            (claim_id,),
        )
        if not row:
            return None
        return VerificationEvent(
            event_id=row["event_id"],
            claim_id=row["claim_id"],
            checked_at=row["checked_at_utc"],
            status=row["status"],
            verification_evidence=row["verification_evidence"],
        )

    def get_current_status(self, claim_id: str) -> Optional[str]:
        """Deriva el estado actual de una Claim desde el VerificationEvent más reciente."""
        latest = self.retrieve_latest_verification(claim_id)
        return latest.status if latest else None
