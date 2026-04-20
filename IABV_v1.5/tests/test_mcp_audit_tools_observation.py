"""Tests para `infra/mcp/audit_tools_observation.py` (F1.3).

Los 4 tools degradan explícito cuando la dependencia nativa falta, así que
los tests cubren tanto el happy path (fakes inyectados) como el fallback
(módulo inexistente o plataforma distinta).
"""

from __future__ import annotations

import platform
import sys
from types import ModuleType, SimpleNamespace

import pytest

from iabv_v15.infra.mcp import audit_tools_observation as obs


# ---------------------------------------------------------------------------
# _sanitize_cmdline — tests unitarios puros

def test_sanitize_cmdline_handles_non_string_between_flag_and_value() -> None:
    """Regresión: si entre un flag sensible y su valor hay un non-string,
    la redacción no debe propagarse al siguiente string legítimo.

    Antes: ``["--token", 123, "https://api.example.com"]`` terminaba con
    la URL redactada y el 123 silenciosamente descartado. Ahora el slot
    posicional se consume con el non-string (se redacta in-place) y la
    URL pasa intacta.
    """

    result = obs._sanitize_cmdline(["--token", 123, "https://api.example.com"])
    # El valor real del token (123, non-string) se redacta in place.
    # La URL posterior queda intacta.
    assert result == ["<redacted>", "<redacted>", "https://api.example.com"]


def test_sanitize_cmdline_space_separated_value_is_redacted() -> None:
    """Caso base: flag sensible sin `=` → valor posicional redactado."""

    result = obs._sanitize_cmdline(["--token", "sk-abc", "--flag", "ok"])
    assert result == ["<redacted>", "<redacted>", "--flag", "ok"]


# ---------------------------------------------------------------------------
# Helpers: instalar/remover un módulo fake

def _install_fake_module(monkeypatch: pytest.MonkeyPatch, name: str, module: ModuleType) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def _uninstall_module(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    if name in sys.modules:
        monkeypatch.delitem(sys.modules, name, raising=False)


# ---------------------------------------------------------------------------
# list_open_windows


def test_list_open_windows_not_supported_outside_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    result = obs.list_open_windows()
    assert result["error"] == "not_supported_platform"
    assert "windows" not in result


def test_list_open_windows_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    # Aseguramos que los imports fallan aunque estuvieran cacheados.
    for name in ("win32gui", "win32con", "win32process"):
        monkeypatch.setitem(sys.modules, name, None)  # type: ignore[arg-type]
    result = obs.list_open_windows()
    assert result["error"] == "dependency_missing"
    assert result["dependency"] == "pywin32"


def test_list_open_windows_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    win_states = {
        111: {"title": "IABV v1.5 - Control Center", "visible": True, "rect": (0, 0, 1920, 1080), "pid": 5292},
        222: {"title": "Opera", "visible": True, "rect": (100, 100, 800, 600), "pid": 9001},
        333: {"title": "", "visible": True, "rect": (0, 0, 0, 0), "pid": 1},
        444: {"title": "Background", "visible": False, "rect": (0, 0, 100, 100), "pid": 2},
    }

    class _FakeWin32Gui:
        @staticmethod
        def GetForegroundWindow() -> int:
            return 111

        @staticmethod
        def EnumWindows(callback: object, lparam: object) -> None:
            for hwnd in win_states:
                callback(hwnd, lparam)  # type: ignore[misc]

        @staticmethod
        def IsWindow(hwnd: int) -> bool:
            return hwnd in win_states

        @staticmethod
        def IsWindowVisible(hwnd: int) -> bool:
            return win_states[hwnd]["visible"]

        @staticmethod
        def GetWindowText(hwnd: int) -> str:
            return win_states[hwnd]["title"]

        @staticmethod
        def GetWindowRect(hwnd: int) -> tuple[int, int, int, int]:
            left, top, w, h = win_states[hwnd]["rect"]
            return (left, top, left + w, top + h)

    class _FakeWin32Process:
        @staticmethod
        def GetWindowThreadProcessId(hwnd: int) -> tuple[int, int]:
            return (0, win_states[hwnd]["pid"])

    fake_gui = ModuleType("win32gui")
    fake_gui.GetForegroundWindow = _FakeWin32Gui.GetForegroundWindow  # type: ignore[attr-defined]
    fake_gui.EnumWindows = _FakeWin32Gui.EnumWindows  # type: ignore[attr-defined]
    fake_gui.IsWindow = _FakeWin32Gui.IsWindow  # type: ignore[attr-defined]
    fake_gui.IsWindowVisible = _FakeWin32Gui.IsWindowVisible  # type: ignore[attr-defined]
    fake_gui.GetWindowText = _FakeWin32Gui.GetWindowText  # type: ignore[attr-defined]
    fake_gui.GetWindowRect = _FakeWin32Gui.GetWindowRect  # type: ignore[attr-defined]

    fake_con = ModuleType("win32con")
    fake_process = ModuleType("win32process")
    fake_process.GetWindowThreadProcessId = _FakeWin32Process.GetWindowThreadProcessId  # type: ignore[attr-defined]

    _install_fake_module(monkeypatch, "win32gui", fake_gui)
    _install_fake_module(monkeypatch, "win32con", fake_con)
    _install_fake_module(monkeypatch, "win32process", fake_process)

    result = obs.list_open_windows()
    assert result["platform"] == "windows"
    titles = {w["title"] for w in result["windows"]}
    assert "IABV v1.5 - Control Center" in titles
    assert "Opera" in titles
    # Empty title y no-visible quedaron fuera.
    assert "Background" not in titles
    assert "" not in titles
    iabv_entry = next(w for w in result["windows"] if "IABV" in w["title"])
    assert iabv_entry["is_foreground"] is True
    assert iabv_entry["pid"] == 5292
    assert iabv_entry["rect"] == [0, 0, 1920, 1080]
    assert result["foreground_hwnd"] == 111


# ---------------------------------------------------------------------------
# list_running_processes


def test_list_running_processes_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "psutil", None)  # type: ignore[arg-type]
    result = obs.list_running_processes()
    assert result["error"] == "dependency_missing"
    assert result["dependency"] == "psutil"


def test_list_running_processes_sanitizes_cmdline(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_procs = [
        {
            "pid": 100,
            "ppid": 1,
            "name": "python.exe",
            "exe": "C:/python.exe",
            "cmdline": ["python", "-m", "iabv", "--token=ABC123SECRET", "--verbose"],
            "status": "running",
            "create_time": 1000.0,
            "username": "faber",
        },
        {
            "pid": 200,
            "ppid": 1,
            "name": "chrome.exe",
            "exe": "",
            "cmdline": ["chrome", "--password=XYZ"],
            "status": "running",
            "create_time": 2000.0,
            "username": "faber",
        },
        {
            "pid": 300,
            "ppid": 1,
            "name": "curl",
            "exe": "",
            # Flag + valor posicional separado: el valor también debe redactarse.
            # `--api-key <value>` (espacio-separado): el valor posicional
            # debe quedar redactado independientemente de su contenido.
            "cmdline": ["curl", "-H", "--api-key", "sk-abc123xyz", "https://api.example.com"],
            "status": "running",
            "create_time": 3000.0,
            "username": "faber",
        },
    ]

    class _FakeProc:
        def __init__(self, info: dict) -> None:
            self.info = info

    def _process_iter(keys: list[str]) -> list[_FakeProc]:
        return [_FakeProc(p) for p in fake_procs]

    fake_psutil = ModuleType("psutil")
    fake_psutil.process_iter = _process_iter  # type: ignore[attr-defined]

    class _Err(Exception):
        pass

    fake_psutil.NoSuchProcess = _Err  # type: ignore[attr-defined]
    fake_psutil.AccessDenied = _Err  # type: ignore[attr-defined]
    fake_psutil.ZombieProcess = _Err  # type: ignore[attr-defined]

    _install_fake_module(monkeypatch, "psutil", fake_psutil)

    result = obs.list_running_processes(limit=10)
    assert result["count"] == 3
    assert result["processes"][0]["pid"] == 100
    cmd0 = result["processes"][0]["cmdline"]
    assert "--token=<redacted>" in cmd0
    assert not any("ABC123SECRET" in token for token in cmd0)
    cmd1 = result["processes"][1]["cmdline"]
    assert "--password=<redacted>" in cmd1
    assert not any("XYZ" in token for token in cmd1)
    # Caso espacio-separado: --api-key sk-abc → flag y valor redactados,
    # pero la URL posterior NO debe quedar redactada.
    cmd2 = result["processes"][2]["cmdline"]
    assert not any("sk-abc123xyz" in token for token in cmd2)
    # Flag sensible se redacta y también el arg siguiente (redact_next).
    assert cmd2.count("<redacted>") == 2
    assert "https://api.example.com" in cmd2


def test_list_running_processes_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def _iter_many(keys: list[str]) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                info={
                    "pid": i,
                    "ppid": 1,
                    "name": f"p{i}",
                    "exe": "",
                    "cmdline": [],
                    "status": "running",
                    "create_time": 0.0,
                    "username": "",
                }
            )
            for i in range(10)
        ]

    fake_psutil = ModuleType("psutil")
    fake_psutil.process_iter = _iter_many  # type: ignore[attr-defined]

    class _Err(Exception):
        pass

    fake_psutil.NoSuchProcess = _Err  # type: ignore[attr-defined]
    fake_psutil.AccessDenied = _Err  # type: ignore[attr-defined]
    fake_psutil.ZombieProcess = _Err  # type: ignore[attr-defined]

    _install_fake_module(monkeypatch, "psutil", fake_psutil)

    result = obs.list_running_processes(limit=3)
    assert result["count"] == 3
    assert result["truncated"] is True


# ---------------------------------------------------------------------------
# read_clipboard


def test_read_clipboard_via_pyperclip(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ModuleType("pyperclip")
    fake.paste = lambda: "hola mundo"  # type: ignore[attr-defined]
    _install_fake_module(monkeypatch, "pyperclip", fake)

    result = obs.read_clipboard()
    assert result["source"] == "pyperclip"
    assert result["content"] == "hola mundo"
    assert result["length"] == 10
    assert result["truncated"] is False


def test_read_clipboard_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    big = "x" * (obs.MAX_CLIPBOARD_BYTES + 100)
    fake = ModuleType("pyperclip")
    fake.paste = lambda: big  # type: ignore[attr-defined]
    _install_fake_module(monkeypatch, "pyperclip", fake)

    result = obs.read_clipboard()
    assert result["truncated"] is True
    assert len(result["content"]) == obs.MAX_CLIPBOARD_BYTES


def test_read_clipboard_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyperclip", None)  # type: ignore[arg-type]
    monkeypatch.setitem(sys.modules, "tkinter", None)  # type: ignore[arg-type]

    result = obs.read_clipboard()
    assert result["error"] == "clipboard_unavailable"
    assert "pyperclip" in result["detail"]


# ---------------------------------------------------------------------------
# dump_qml_tree


def test_dump_qml_tree_no_qapplication() -> None:
    result = obs.dump_qml_tree(app_factory=lambda: None)
    assert result["error"] == "ui_not_running"


def test_dump_qml_tree_walks_fake_tree() -> None:
    class _FakeMeta:
        def __init__(self, cls: str) -> None:
            self._cls = cls

        def className(self) -> str:
            return self._cls

    class _FakeWidget:
        def __init__(self, cls: str, name: str = "", title: str = "") -> None:
            self._cls = cls
            self._name = name
            self._title = title
            self._children: list["_FakeWidget"] = []

        def add(self, child: "_FakeWidget") -> None:
            self._children.append(child)

        def children(self) -> list["_FakeWidget"]:
            return list(self._children)

        def objectName(self) -> str:
            return self._name

        def windowTitle(self) -> str:
            return self._title

        def metaObject(self) -> _FakeMeta:
            return _FakeMeta(self._cls)

    main = _FakeWidget("MainWindow", name="main", title="IABV")
    stack = _FakeWidget("QStackedWidget", name="stack")
    page1 = _FakeWidget("ControlCenterPage", name="control_center")
    page2 = _FakeWidget("EvolutionCenterPage", name="evolution_center")
    main.add(stack)
    stack.add(page1)
    stack.add(page2)

    fake_app = SimpleNamespace(topLevelWidgets=lambda: [main])

    result = obs.dump_qml_tree(app_factory=lambda: fake_app)
    assert result["top_level_count"] == 1
    assert result["count"] == 4
    classes = [n["class"] for n in result["nodes"]]
    assert "MainWindow" in classes
    assert "ControlCenterPage" in classes
    assert "EvolutionCenterPage" in classes
    # El root tiene parent_id None y window_title "IABV"
    root = next(n for n in result["nodes"] if n["class"] == "MainWindow")
    assert root["parent_id"] is None
    assert root["window_title"] == "IABV"
    # El stack es hijo del root
    stack_node = next(n for n in result["nodes"] if n["class"] == "QStackedWidget")
    assert stack_node["parent_id"] == root["id"]


def test_dump_qml_tree_truncates() -> None:
    class _FakeMeta:
        def __init__(self, cls: str) -> None:
            self._cls = cls

        def className(self) -> str:
            return self._cls

    class _FakeWidget:
        def __init__(self, cls: str) -> None:
            self._cls = cls
            self._children: list["_FakeWidget"] = []

        def metaObject(self) -> _FakeMeta:
            return _FakeMeta(self._cls)

        def add(self, child: "_FakeWidget") -> None:
            self._children.append(child)

        def children(self) -> list["_FakeWidget"]:
            return list(self._children)

        def objectName(self) -> str:
            return ""

        def windowTitle(self) -> str:
            return ""

    root = _FakeWidget("Root")
    for i in range(20):
        root.add(_FakeWidget(f"Child{i}"))

    fake_app = SimpleNamespace(topLevelWidgets=lambda: [root])

    result = obs.dump_qml_tree(max_nodes=5, app_factory=lambda: fake_app)
    assert result["count"] == 5
    assert result["truncated"] is True
