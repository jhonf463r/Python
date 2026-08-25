from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from iabv_v15.domain.models import BrowserProfileConfig, PersistStrategy


class TrainingProfileManager:
    TRANSIENT_DIRS = {
        "cache",
        "code cache",
        "gpucache",
        "grshadercache",
        "shadercache",
        "dawncache",
        "crashpad",
        "component updater",
        "blob_storage",
    }
    TRANSIENT_FILES = {
        "singletonlock",
        "singletoncookie",
        "singletonsocket",
        "lock",
        "lockfile",
        "current session",
        "current tabs",
        "last session",
        "last tabs",
    }

    def __init__(self, profiles_root: str):
        self.profiles_root = Path(profiles_root)
        self.profiles_root.mkdir(parents=True, exist_ok=True)

    def bootstrap_clone(self, profile_config: BrowserProfileConfig) -> BrowserProfileConfig:
        profile_root = Path(profile_config.user_data_dir or (self.profiles_root / profile_config.profile_id))
        default_target = profile_root / "Default"
        profile_root.mkdir(parents=True, exist_ok=True)
        default_target.mkdir(parents=True, exist_ok=True)

        result = profile_config
        mode = profile_config.persist_strategy.value
        warning = ""

        try:
            if profile_config.persist_strategy == PersistStrategy.CLONED_PROFILE and self._needs_clone_repair(profile_root):
                shutil.rmtree(profile_root, ignore_errors=True)
                profile_root.mkdir(parents=True, exist_ok=True)
                default_target = profile_root / 'Default'
                default_target.mkdir(parents=True, exist_ok=True)
                warning = 'Perfil clonado incompleto detectado; se reinicio como perfil IA fresco.'
                result = profile_config.model_copy(update={'persist_strategy': PersistStrategy.FRESH_PROFILE})
                mode = PersistStrategy.FRESH_PROFILE.value
            elif profile_config.persist_strategy == PersistStrategy.CLONED_PROFILE:
                self._clone_profile(profile_config, profile_root, default_target)
            elif profile_config.persist_strategy == PersistStrategy.STORAGE_STATE_ONLY:
                mode = PersistStrategy.STORAGE_STATE_ONLY.value
            else:
                mode = PersistStrategy.FRESH_PROFILE.value
        except Exception as exc:
            warning = str(exc)
            mode = PersistStrategy.FRESH_PROFILE.value
            result = profile_config.model_copy(update={"persist_strategy": PersistStrategy.FRESH_PROFILE})
            default_target.mkdir(parents=True, exist_ok=True)

        health = self._profile_health(profile_root, mode)
        manifest = {
            "profile_id": result.profile_id,
            "site_id": result.site_id,
            "mode": mode,
            "user_data_dir": str(profile_root),
            "storage_state_path": result.storage_state_path,
            "source_user_data_dir": result.source_user_data_dir,
            "source_profile_dir": result.source_profile_dir,
            "warning": warning,
            "healthy": health['healthy'],
            "health_detail": health['detail'],
        }
        (profile_root / "profile.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def list_profiles(self) -> list[dict]:
        profiles: list[dict] = []
        for manifest_path in sorted(self.profiles_root.glob("*/profile.json")):
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload.setdefault("label", payload.get("profile_id", manifest_path.parent.name))
            health = self._profile_health(manifest_path.parent, payload.get('mode', PersistStrategy.FRESH_PROFILE.value))
            payload['healthy'] = health['healthy']
            payload['health_detail'] = health['detail']
            profiles.append(payload)
        return profiles

    def _clone_profile(self, profile_config: BrowserProfileConfig, profile_root: Path, default_target: Path) -> None:
        source_root = Path(profile_config.source_user_data_dir or "")
        source_profile_dir = profile_config.source_profile_dir or "Default"
        source_profile = Path(source_profile_dir)
        if not source_profile.is_absolute():
            source_profile = source_root / source_profile_dir

        if default_target.exists() and any(default_target.iterdir()):
            return

        if source_root.exists():
            local_state = source_root / "Local State"
            if local_state.exists() and not (profile_root / "Local State").exists():
                shutil.copy2(local_state, profile_root / "Local State")

        if source_profile.exists():
            self._copy_filtered_dir(source_profile, default_target)

    def _copy_filtered_dir(self, source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            lower_name = item.name.lower()
            if item.is_dir() and lower_name in self.TRANSIENT_DIRS:
                continue
            if lower_name in self.TRANSIENT_FILES or lower_name.endswith(".tmp"):
                continue
            destination = target / item.name
            if item.is_dir():
                self._copy_filtered_dir(item, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)


    def remove_profile(self, profile_id: str, *, storage_state_path: str | None = None) -> bool:
        profile_root = self.profiles_root / profile_id
        removed = False
        if profile_root.exists():
            shutil.rmtree(profile_root, ignore_errors=True)
            removed = True
        if storage_state_path:
            state_path = Path(storage_state_path)
            if state_path.exists():
                state_path.unlink(missing_ok=True)
                removed = True
        return removed

    def recreate_profile(self, profile_config: BrowserProfileConfig) -> BrowserProfileConfig:
        self.remove_profile(profile_config.profile_id, storage_state_path=profile_config.storage_state_path)
        fresh = profile_config.model_copy(update={'persist_strategy': PersistStrategy.FRESH_PROFILE})
        return self.bootstrap_clone(fresh)

    def open_profile(self, profile_config: BrowserProfileConfig, *, start_url: str | None = None) -> dict:
        if profile_config.persist_strategy == PersistStrategy.CLONED_PROFILE and self._needs_clone_repair(Path(profile_config.user_data_dir)):
            profile_config = self.recreate_profile(profile_config)
        executable = self._detect_browser_executable(profile_config.channel)
        if executable is None:
            return {'status': 'error', 'detail': 'No encontre Chrome o Edge instalado para abrir el perfil IA.', 'command': []}
        profile_root = Path(profile_config.user_data_dir or (self.profiles_root / profile_config.profile_id))
        profile_root.mkdir(parents=True, exist_ok=True)
        command = [
            executable,
            f'--user-data-dir={profile_root}',
            '--profile-directory=Default',
            '--start-maximized',
        ]
        if start_url:
            command.append(start_url)
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {'status': 'ok', 'detail': f'Perfil IA abierto con {Path(executable).name}.', 'command': command}
        except Exception as exc:
            return {'status': 'error', 'detail': str(exc), 'command': command}

    def _detect_browser_executable(self, channel: str | None) -> str | None:
        env_override = os.getenv('IABV_CHROME_EXE')
        candidates: list[Path] = []
        if env_override:
            candidates.append(Path(env_override))
        local_app_data = Path(os.getenv('LOCALAPPDATA', ''))
        program_files = Path(os.getenv('PROGRAMFILES', ''))
        program_files_x86 = Path(os.getenv('PROGRAMFILES(X86)', ''))
        chrome_candidates = [
            local_app_data / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            program_files / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            program_files_x86 / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        ]
        edge_candidates = [
            local_app_data / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            program_files / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            program_files_x86 / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
        ]
        if (channel or '').lower() == 'msedge':
            candidates.extend(edge_candidates + chrome_candidates)
        else:
            candidates.extend(chrome_candidates + edge_candidates)
        for candidate in candidates:
            if candidate and str(candidate) and candidate.exists():
                return str(candidate)
        return shutil.which('chrome') or shutil.which('msedge')


    def _needs_clone_repair(self, profile_root: Path) -> bool:
        default_target = profile_root / 'Default'
        if not default_target.exists() or not any(default_target.iterdir()):
            return False
        preferences = default_target / 'Preferences'
        secure_preferences = default_target / 'Secure Preferences'
        return not preferences.exists() and not secure_preferences.exists()

    def _profile_in_use(self, profile_root: Path) -> bool:
        candidates = [profile_root, profile_root / 'Default']
        for base in candidates:
            if not base.exists():
                continue
            for name in self.TRANSIENT_FILES:
                if (base / name).exists() or (base / name.title()).exists():
                    return True
            for path in base.glob('Singleton*'):
                if path.exists():
                    return True
        return False

    def _profile_health(self, profile_root: Path, mode: str) -> dict:
        default_target = profile_root / 'Default'
        if not default_target.exists():
            return {'healthy': True, 'detail': 'Perfil IA aun no inicializado por Chrome.'}
        if mode == PersistStrategy.CLONED_PROFILE.value and self._needs_clone_repair(profile_root):
            return {'healthy': False, 'detail': 'Clon incompleto detectado. Conviene recrearlo como perfil IA fresco.'}
        if self._profile_in_use(profile_root):
            return {'healthy': False, 'detail': 'Perfil IA abierto o bloqueado por Chrome. Cierra ese navegador antes de iniciar captura administrada.'}
        preferences = default_target / 'Preferences'
        if preferences.exists():
            return {'healthy': True, 'detail': 'Perfil IA listo para reutilizar sesion en esta maquina.'}
        if any(default_target.iterdir()):
            return {'healthy': True, 'detail': 'Perfil IA creado; Chrome terminara de inicializarlo al abrirlo.'}
        return {'healthy': True, 'detail': 'Perfil IA fresco y vacio. Abrelo una vez para iniciar sesion manualmente.'}
