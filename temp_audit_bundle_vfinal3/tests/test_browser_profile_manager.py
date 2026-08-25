from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import subprocess

from iabv_v15.domain.models import BrowserProfileConfig, PersistStrategy
from iabv_v15.services.capture.training_profile_manager import TrainingProfileManager


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_bootstrap_clone_copies_profile_without_cache_or_lock_files() -> None:
    root = _workspace('profile_clone')
    source_root = root / 'chrome_user_data'
    source_profile = source_root / 'Default'
    (source_profile / 'Cache').mkdir(parents=True, exist_ok=True)
    (source_profile / 'Local Storage').mkdir(parents=True, exist_ok=True)
    (source_profile / 'Cookies').write_text('cookies-db', encoding='utf-8')
    (source_profile / 'SingletonLock').write_text('lock', encoding='utf-8')
    (source_profile / 'Cache' / 'tmp.bin').write_text('cache', encoding='utf-8')
    (source_root / 'Local State').write_text('{"browser": true}', encoding='utf-8')

    manager = TrainingProfileManager(str(root / 'profiles'))
    profile = BrowserProfileConfig(
        profile_id='wplay_teach',
        site_id='wplay',
        user_data_dir=str(root / 'profiles' / 'wplay_teach'),
        storage_state_path=str(root / 'states' / 'wplay.json'),
        source_user_data_dir=str(source_root),
        source_profile_dir='Default',
        persist_strategy=PersistStrategy.CLONED_PROFILE,
    )
    result = manager.bootstrap_clone(profile)
    target_root = Path(result.user_data_dir)
    assert (target_root / 'Local State').exists()
    assert (target_root / 'Default' / 'Cookies').exists()
    assert not (target_root / 'Default' / 'Cache').exists()
    assert not (target_root / 'Default' / 'SingletonLock').exists()
    assert manager.list_profiles()[0]['profile_id'] == 'wplay_teach'


def test_recreate_profile_resets_existing_clone_and_state() -> None:
    root = _workspace('profile_recreate')
    manager = TrainingProfileManager(str(root / 'profiles'))
    profile = BrowserProfileConfig(
        profile_id='iabv_ai_test',
        site_id='test',
        user_data_dir=str(root / 'profiles' / 'iabv_ai_test'),
        storage_state_path=str(root / 'states' / 'test.json'),
        persist_strategy=PersistStrategy.FRESH_PROFILE,
    )
    target_root = Path(profile.user_data_dir)
    (target_root / 'Default').mkdir(parents=True, exist_ok=True)
    (target_root / 'Default' / 'old.txt').write_text('legacy', encoding='utf-8')
    Path(profile.storage_state_path).parent.mkdir(parents=True, exist_ok=True)
    Path(profile.storage_state_path).write_text('{"cookies": []}', encoding='utf-8')

    manager.recreate_profile(profile)

    assert (target_root / 'Default').exists()
    assert not (target_root / 'Default' / 'old.txt').exists()
    assert not Path(profile.storage_state_path).exists()


def test_open_profile_uses_dedicated_user_data_dir(monkeypatch) -> None:
    root = _workspace('profile_open')
    browser_exe = root / 'chrome.exe'
    browser_exe.write_text('stub', encoding='utf-8')
    manager = TrainingProfileManager(str(root / 'profiles'))
    profile = BrowserProfileConfig(
        profile_id='iabv_ai_test',
        site_id='test',
        user_data_dir=str(root / 'profiles' / 'iabv_ai_test'),
        storage_state_path=str(root / 'states' / 'test.json'),
        persist_strategy=PersistStrategy.FRESH_PROFILE,
    )
    called = {}

    def fake_popen(command, stdout=None, stderr=None):
        called['command'] = command
        class _Proc:
            pass
        return _Proc()

    monkeypatch.setenv('IABV_CHROME_EXE', str(browser_exe))
    monkeypatch.setattr(subprocess, 'Popen', fake_popen)

    result = manager.open_profile(profile, start_url='https://example.com')

    assert result['status'] == 'ok'
    assert called['command'][0] == str(browser_exe)
    assert f"--user-data-dir={profile.user_data_dir}" in called['command']
    assert '--profile-directory=Default' in called['command']
    assert called['command'][-1] == 'https://example.com'


def test_list_profiles_marks_incomplete_clone_as_unhealthy() -> None:
    root = _workspace('profile_health')
    manager = TrainingProfileManager(str(root / 'profiles'))
    profile_root = root / 'profiles' / 'broken_clone' / 'Default'
    profile_root.mkdir(parents=True, exist_ok=True)
    (profile_root / 'Cookies').write_text('cookie-db', encoding='utf-8')
    manifest_path = profile_root.parent / 'profile.json'
    manifest_path.write_text('\n'.join([
        '{',
        '  "profile_id": "broken_clone",',
        '  "site_id": "broken",',
        '  "mode": "cloned_profile",',
        f'  "user_data_dir": "{str(profile_root.parent).replace(chr(92), chr(92) * 2)}"',
        '}',
    ]), encoding='utf-8')

    profiles = manager.list_profiles()

    assert profiles[0]['healthy'] is False
    assert 'Clon incompleto' in profiles[0]['health_detail']


def test_list_profiles_marks_open_profile_as_unhealthy() -> None:
    root = _workspace('profile_in_use')
    manager = TrainingProfileManager(str(root / 'profiles'))
    profile_root = root / 'profiles' / 'busy_profile'
    default_root = profile_root / 'Default'
    default_root.mkdir(parents=True, exist_ok=True)
    (default_root / 'Preferences').write_text('{}', encoding='utf-8')
    (profile_root / 'lockfile').write_text('', encoding='utf-8')
    manifest_path = profile_root / 'profile.json'
    manifest_path.write_text('\n'.join([
        '{',
        '  "profile_id": "busy_profile",',
        '  "site_id": "busy",',
        '  "mode": "fresh_profile",',
        f'  "user_data_dir": "{str(profile_root).replace(chr(92), chr(92) * 2)}"',
        '}',
    ]), encoding='utf-8')

    profiles = manager.list_profiles()

    assert profiles[0]['healthy'] is False
    assert 'bloqueado por Chrome' in profiles[0]['health_detail']
