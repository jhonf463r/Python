from __future__ import annotations

from iabv_v15.domain.models import CaptureChannel, RedactionSummary, TrainingPayloadV2
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.services.training.payload_archive_service import PayloadArchiveService


class TrainingOrchestrator:
    def __init__(
        self,
        workspace_root: str,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        archive_service: PayloadArchiveService,
        artifact_repository: SessionArtifactRepository | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.archive_service = archive_service
        self.artifact_repository = artifact_repository

    def prepare_payload(self) -> TrainingPayloadV2:
        episodes = self.episode_repository.list_recent(limit=50)
        steps = []
        artifacts = []
        redaction_summary = RedactionSummary()
        channel_values: set[str] = set()
        domains: set[str] = set()
        site_ids: set[str] = set()

        for episode in episodes:
            episode_steps = self.episode_repository.load_episode(episode.episode_id)
            steps.extend(episode_steps)
            if self.artifact_repository is not None:
                episode_artifacts = self.artifact_repository.list_for_episode(episode.episode_id)
                artifacts.extend(episode_artifacts)
                for artifact in episode_artifacts:
                    channel_value = artifact.metadata.get("capture_channel")
                    if channel_value:
                        channel_values.add(channel_value)
                    domain = artifact.metadata.get("domain")
                    if domain:
                        domains.add(domain)
                    site_id = artifact.metadata.get("site_id")
                    if site_id:
                        site_ids.add(site_id)
                    redaction_summary.redacted_network_fields += int(artifact.metadata.get("redacted_fields", 0))
                    if artifact.metadata.get("redacted"):
                        redaction_summary.warnings.append(f"Artifact {artifact.kind} was stored redacted.")

        for step in steps:
            if step.metadata.get("sensitive"):
                redaction_summary.redacted_steps += 1
            if step.metadata.get("vault_ref"):
                redaction_summary.stored_secrets += 1

        payload = TrainingPayloadV2(
            workspace=self.workspace_root,
            episodes=episodes,
            steps=steps,
            artifacts=artifacts,
            knowledge_items=self.knowledge_repository.list_recent(limit=100),
            run_records=self.run_repository.list_recent(limit=100),
            capture_channels=[CaptureChannel(value) for value in sorted(channel_values) if value],
            site_context={
                "domains": sorted(domains),
                "site_ids": sorted(site_ids),
                "episode_count": len(episodes),
            },
            redaction_summary=redaction_summary,
            metadata={
                "source": "desktop-control-app",
                "browser_teach_mode": True,
                "artifact_count": len(artifacts),
            },
        )
        return payload

    def prepare_and_archive(self) -> tuple[TrainingPayloadV2, str]:
        payload = self.prepare_payload()
        archived_path = self.archive_service.archive(payload)
        return payload, archived_path
