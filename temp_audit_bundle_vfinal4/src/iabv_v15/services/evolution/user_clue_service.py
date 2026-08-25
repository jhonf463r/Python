from __future__ import annotations

from iabv_v15.domain.models import UserClue
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository


class UserClueService:
    def __init__(self, *, clue_repository: UserClueRepository, incident_repository: HiddenIncidentRepository) -> None:
        self.clue_repository = clue_repository
        self.incident_repository = incident_repository

    def attach_to_latest_context(
        self,
        *,
        text: str,
        site_id: str,
        episode_id: str | None = None,
        run_id: str | None = None,
        incident_id: str | None = None,
    ) -> UserClue:
        linked_incident_id = incident_id
        if linked_incident_id is None and episode_id:
            incidents = self.incident_repository.find_by_episode(episode_id)
            if incidents:
                linked_incident_id = incidents[0].incident_id
        clue = UserClue(
            text=text.strip(),
            episode_id=episode_id,
            run_id=run_id,
            linked_incident_id=linked_incident_id,
            site_id=site_id,
        )
        return self.clue_repository.save(clue)
