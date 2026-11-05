from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.domain.models import EpisodeManifest, ReplayAnnotation, SessionArtifact
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _episode_repository(tmp_path: Path) -> tuple[AppDatabase, EpisodeRepository]:
    db = AppDatabase(str(tmp_path / "episodes.sqlite"))
    return db, EpisodeRepository(str(tmp_path / "episodes"), db)


def _artifact_repository(tmp_path: Path) -> tuple[AppDatabase, SessionArtifactRepository]:
    db = AppDatabase(str(tmp_path / "artifacts.sqlite"))
    return db, SessionArtifactRepository(db, ArtifactStorage(str(tmp_path / "browser_artifacts")))


def _replay_repository(tmp_path: Path) -> tuple[AppDatabase, ReplayAnnotationRepository]:
    db = AppDatabase(str(tmp_path / "replay.sqlite"))
    return db, ReplayAnnotationRepository(db, ArtifactStorage(str(tmp_path / "replay_storage")))


def test_artifact_storage_rejects_traversal_and_absolute_paths_before_creating_directories(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    outside = tmp_path / "outside" / "payload.json"
    storage = ArtifactStorage(str(storage_root))

    with pytest.raises(ValueError, match="traversal|outside"):
        storage.resolve("../outside/payload.json")
    with pytest.raises(ValueError, match="outside"):
        storage.resolve(str(outside))
    with pytest.raises(ValueError, match="outside"):
        storage.resolve_managed_path(str(outside))

    assert not outside.parent.exists()
    assert not outside.exists()


def test_artifact_storage_rejects_symlink_escape(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    storage = ArtifactStorage(str(storage_root))
    link = storage_root / "external-link"
    try:
        link.symlink_to(outside_root, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable in this test environment: {exc}")

    with pytest.raises(ValueError, match="outside"):
        storage.resolve("external-link/payload.json")
    assert not (outside_root / "payload.json").exists()


@pytest.mark.parametrize(
    "episode_id",
    [
        "",
        ".",
        "..",
        "../outside",
        "nested/episode",
        "nested" + chr(92) + "episode",
        "/tmp/outside",
        "C:" + chr(92) + "outside" + chr(92) + "episode",
        "C:relative",
        chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "episode",
        chr(0),
    ],
)
def test_episode_repository_rejects_unsafe_ids_before_filesystem_access(
    tmp_path: Path, episode_id: str
) -> None:
    _, repository = _episode_repository(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    marker = outside / "episode.jsonl"
    marker_content = '{"action_type":"must-not-be-read"}' + chr(10)
    marker.write_text(marker_content, encoding="utf-8")

    with pytest.raises(ValueError):
        repository.load_episode(episode_id)
    assert marker.read_text(encoding="utf-8") == marker_content
    assert repository.base_dir.exists()


def test_episode_repository_rejects_unsafe_id_in_persisted_manifest(
    tmp_path: Path,
) -> None:
    db, repository = _episode_repository(tmp_path)
    malicious = EpisodeManifest(episode_id="../outside", title="Tampered index")
    db.execute(
        """
        INSERT INTO episodes
        (episode_id, title, manifest_json, step_count, updated_at_utc)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            malicious.episode_id,
            malicious.title,
            malicious.model_dump_json(),
            malicious.step_count,
            malicious.updated_at_utc.isoformat(),
        ),
    )

    with pytest.raises(ValueError):
        repository.list_recent()
    assert not (tmp_path / "outside").exists()


def test_session_artifact_repository_rejects_external_paths_on_save(
    tmp_path: Path,
) -> None:
    _, repository = _artifact_repository(tmp_path)
    outside = tmp_path / "outside" / "external.json"
    outside.parent.mkdir()
    outside.write_text('{"secret":"must-not-be-read"}', encoding="utf-8")

    with pytest.raises(ValueError):
        repository.save(
            SessionArtifact(
                episode_id="episode-a",
                kind="external",
                path=str(outside),
            )
        )
    with pytest.raises(ValueError):
        repository.save(
            SessionArtifact(
                episode_id="episode-a",
                kind="traversal",
                path="../outside/external.json",
            )
        )
    assert outside.read_text(encoding="utf-8") == '{"secret":"must-not-be-read"}'


def test_session_artifact_repository_rejects_external_index_path_on_read(
    tmp_path: Path,
) -> None:
    db, repository = _artifact_repository(tmp_path)
    artifact = repository.save(
        SessionArtifact(
            episode_id="episode-a",
            kind="learning_bundle",
            path="episode-a/learning_bundle.json",
        )
    )
    outside = tmp_path / "outside.json"
    outside.write_text('{"external":"not managed"}', encoding="utf-8")
    db.execute(
        "UPDATE session_artifacts SET path = ? WHERE artifact_id = ?",
        (str(outside), artifact.artifact_id),
    )

    with pytest.raises(ValueError, match="outside"):
        repository.list_for_episode("episode-a")
    assert outside.read_text(encoding="utf-8") == '{"external":"not managed"}'


def test_replay_annotation_repository_rejects_external_index_path_without_reading(
    tmp_path: Path,
) -> None:
    db, repository = _replay_repository(tmp_path)
    annotation = repository.save(
        ReplayAnnotation(
            annotation_id="safe-annotation",
            episode_id="episode-a",
            step_id="step-a",
            screenshot_path="frame.png",
            group_key="group-a",
        )
    )
    outside = tmp_path / "outside-annotation.json"
    outside.write_text(annotation.model_dump_json(), encoding="utf-8")
    db.execute(
        "UPDATE replay_annotations SET path = ? WHERE annotation_id = ?",
        (str(outside), annotation.annotation_id),
    )

    result = repository.get_with_diagnostics(annotation.annotation_id)

    assert result.status == ArtifactReadStatus.READ_FAILED
    assert result.error_type == "ValueError"
    assert repository.last_read_report is not None
    assert repository.last_read_report.status == RepositoryReadStatus.READ_FAILED
    with pytest.raises(RepositoryReadError):
        repository.get(annotation.annotation_id)
    assert outside.read_text(encoding="utf-8") == annotation.model_dump_json()


def test_replay_annotation_collection_rejects_external_index_path(
    tmp_path: Path,
) -> None:
    db, repository = _replay_repository(tmp_path)
    annotation = repository.save(
        ReplayAnnotation(
            annotation_id="safe-collection-annotation",
            episode_id="episode-a",
            screenshot_path="frame.png",
            group_key="group-a",
        )
    )
    outside = tmp_path / "outside-list.json"
    outside.write_text(annotation.model_dump_json(), encoding="utf-8")
    db.execute(
        "UPDATE replay_annotations SET path = ? WHERE annotation_id = ?",
        (str(outside), annotation.annotation_id),
    )

    report = repository.list_for_episode_with_diagnostics("episode-a")

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.results[0].status == ArtifactReadStatus.READ_FAILED
    assert report.results[0].error_type == "ValueError"
    assert outside.exists()



def test_artifact_storage_keeps_absolute_paths_returned_by_its_own_writes_compatible(
    tmp_path: Path,
) -> None:
    storage = ArtifactStorage(str(tmp_path / "storage"))
    saved = storage.save_json_atomic("episode-a/payload.json", {"ok": True})

    assert Path(saved).is_absolute()
    assert storage.resolve(saved) == Path(saved).resolve()
    assert storage.load_json(saved) == {"ok": True}
