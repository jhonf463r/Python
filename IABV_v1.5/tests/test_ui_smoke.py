from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip('PySide6')

from iabv_v15.bootstrap import AppBootstrap


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _wait_for_loader_item(app, loader, *, timeout_seconds: float = 6.0) -> None:
    import time

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        app.processEvents()
        if loader.property('item') is not None:
            return
        time.sleep(0.05)
    app.processEvents()


def _wait_for_shell_loader(app, root, *, timeout_seconds: float = 6.0):
    from PySide6.QtCore import QObject

    import time

    deadline = time.time() + timeout_seconds
    shell_loader = None
    while time.time() < deadline:
        app.processEvents()
        shell_loader = root.findChild(QObject, 'mainShellLoader')
        if shell_loader is not None and shell_loader.property('item') is not None:
            return shell_loader
        time.sleep(0.05)
    app.processEvents()
    return shell_loader

@pytest.mark.ui
def test_ui_bootstrap_loads_main_qml() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_ui_workspace')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        app, engine = bootstrap.create_engine()
        assert engine.rootObjects()
        assert bootstrap.control_center_viewmodel is not None
        app.quit()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_control_center_ui_prioritizes_chat_and_compact_default_view() -> None:
    qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'pages' / 'ControlCenterPage.qml').read_text(encoding='utf-8')
    assert 'Superior' not in qml
    assert 'ChatGPT web' not in qml
    assert 'OpenAI' not in qml
    assert 'Chat operativo' in qml
    assert 'Modo automatico' in qml
    assert 'Mostrar avanzado' in qml
    assert 'Panel avanzado' in qml
    assert 'Pulso evolutivo' in qml
    assert 'Ultimo experimento o evaluacion:' in qml
    assert 'Panel de evolucion' in qml
    assert 'Bloqueos e intervencion humana' in qml
    assert 'evolutionOverviewModel' in qml
    assert 'evolutionAreaCardsModel' in qml
    assert 'Automatico' in qml
    assert 'Popup {' in qml
    assert 'Puedes seleccionar texto del chat con el cursor.' in qml
    assert 'selectByMouse: true' in qml
    assert 'Siguiente gesto sugerido' in qml
    assert 'applySuggestedAction(modelData.action)' in qml
    assert 'assistantGuidanceTextValue' in qml
    assert 'Dock vivo de autonomia' in qml
    assert 'liveProcessSummaryModel' in qml
    assert 'assistantSessionCardsModel' in qml
    assert 'autonomyTimelineModel' in qml
    assert 'No uses este chat' in qml
    assert 'Aprendizaje incorrecto' in qml
    assert 'Actividad autonoma' in qml
    assert 'autonomyActivityModel' in qml
    assert 'visible: chatMessagesModel.length === 0 && !Boolean(autonomyActivityModel.visible)' in qml
    assert 'implicitHeight: 300' in qml
    assert 'implicitHeight: 92' in qml
    assert 'Siguiente paso:' in qml
    assert 'Aprendizaje:' in qml
    assert 'Ultima respuesta' not in qml
    assert 'Copiar ultima respuesta' not in qml
    assert 'Actualizar stack' not in qml
    assert 'chatInput.text = ""' in qml


def test_capture_studio_ui_uses_generic_teaching_flow() -> None:
    qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'pages' / 'CaptureStudioPage.qml').read_text(encoding='utf-8')
    main_qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml').read_text(encoding='utf-8')
    assert 'Estudio de Ensenanza Web' not in qml
    assert 'Estudio de Ensenanza Web' not in main_qml
    assert 'Estudio de ensenanza' in qml
    assert 'Que vas a ensenar' in qml
    assert 'URL inicial o punto de arranque' in qml
    assert 'Iniciar captura' in qml
    assert 'Sesion y selectores' in qml
    assert 'No hay perfiles visibles en esta pantalla' in qml
    assert 'sesion ligera por sitio' in qml
    assert 'storage state por sitio' in qml
    assert '!sessionActiveState && !sessionFinalizingState' in qml
    assert 'Pausar' in qml
    assert 'Reanudar' in qml
    assert 'Detener y recopilar' in qml
    assert 'Registrar pista' in qml
    assert 'captura visible ok' in qml
    assert 'bridge activo' in qml
    assert 'API en modo inteligente' in qml
    assert 'Recopilando...' in qml
    assert 'Historial de ensenanza y replay guiado' in qml
    assert 'Ver replay guiado' in qml
    assert 'capturas:' in qml
    assert 'screenshot_url' in qml
    assert 'Replay guiado ampliado' in qml
    assert 'Galeria visual' in qml
    assert 'Timeline de eventos' in qml
    assert 'Filmstrip' in qml
    assert 'Todo' in qml
    assert 'Verde' in qml
    assert 'Naranja' in qml
    assert 'Rojo' in qml
    assert 'replayStatusMatches' in qml
    assert 'frameMatchesFilter' in qml
    assert 'Zoom' in qml
    assert 'Doble clic sobre la imagen para ampliar o volver al ajuste.' in qml
    assert 'TapHandler' in qml
    assert 'replayEffectiveScale' in qml
    assert 'Redibujar' in qml
    assert 'Marcar verde' in qml
    assert 'Marcar naranja' in qml
    assert 'Marcar rojo' in qml
    assert 'Guardar etiqueta' in qml
    assert 'Eliminar anotacion' in qml
    assert 'Aprendizaje clave' in qml
    assert 'Login aprendido' in qml
    assert 'Auditoria 2 planos | audit_status:' in qml
    assert 'replayAuditMetadata' in qml
    assert 'replayAuditConfidenceLabel' in qml
    assert 'replayAuditPrimaryIssue' in qml
    assert 'replayAuditDetailLine' in qml
    assert 'discrepancias:' in qml
    assert 'Comando sugerido' in qml
    assert 'replay:' in qml
    assert 'incidentes:' in qml
    assert 'Cerrar replay' in qml
    assert 'Eliminar' in qml
    assert 'Replay cargado con ' in qml
    assert 'credential_check' in qml
    assert 'Replay de asistentes externos' in qml
    assert 'assistantReplayCardsModel' in qml
    assert 'assistantReplayStepsModel' in qml
    assert 'assistantLaneSummaryModel' in qml
    assert 'Timeline y auditoria del asistente' in qml
    assert 'No uses este chat' in qml
    assert 'Crear o reutilizar perfil IA' not in qml
    assert 'Abrir perfil IA' not in qml
    assert 'Recrear perfil IA' not in qml


@pytest.mark.ui
def test_capture_route_materializes_loader_item() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QObject

    workspace = _workspace('test_ui_capture_workspace')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        app, engine = bootstrap.create_engine()
        root = engine.rootObjects()[0]
        root.show()
        app.processEvents()
        shell_loader = _wait_for_shell_loader(app, root)
        assert shell_loader is not None
        bootstrap.navigation_controller.navigate('capture')
        loader = root.findChild(QObject, 'pageLoader')
        assert loader is not None
        assert loader.property('source')
        _wait_for_loader_item(app, loader)
        assert loader.property('item') is not None
        app.quit()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.ui
def test_evolution_route_materializes_loader_item() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QObject

    workspace = _workspace('test_ui_evolution_workspace')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        app, engine = bootstrap.create_engine()
        root = engine.rootObjects()[0]
        root.show()
        app.processEvents()
        shell_loader = _wait_for_shell_loader(app, root)
        assert shell_loader is not None
        bootstrap.navigation_controller.navigate('evolution')
        loader = root.findChild(QObject, 'pageLoader')
        assert loader is not None
        assert loader.property('source')
        _wait_for_loader_item(app, loader)
        assert loader.property('item') is not None
        app.quit()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_ui_shows_hidden_incidents_panel() -> None:
    qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'pages' / 'EvolutionCenterPage.qml').read_text(encoding='utf-8')
    assert 'Incidentes invisibles recientes' in qml
    assert 'Captura' in qml
    assert 'Navegacion' in qml
    assert 'Finalizacion' in qml
    assert 'Replay' in qml
    assert 'Ver evidencia relacionada' in qml
    assert 'Evidencia relacionada' in qml


def test_main_navigation_labels_fit_within_cards() -> None:
    main_qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml').read_text(encoding='utf-8')
    assert 'width: navText.width' in main_qml
    assert 'width: workspaceInfo.width' in main_qml



