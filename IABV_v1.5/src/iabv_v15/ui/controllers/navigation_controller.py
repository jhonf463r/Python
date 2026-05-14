from __future__ import annotations

from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class NavigationController(QObject):
    currentRouteChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._routes = [
            {'key': 'dashboard', 'title': 'Resumen', 'subtitle': 'Pulso local del sistema, modelos y memoria'},
            {'key': 'control', 'title': 'Centro de Control', 'subtitle': 'Roles de trabajo, progreso, paquete Codex y PBT'},
            {'key': 'capture', 'title': 'Estudio de Ensenanza', 'subtitle': 'Formulario de ensenanza, captura visible, segundo plano y API'},
            {'key': 'evolution', 'title': 'Centro Evolutivo', 'subtitle': 'Autodiagnostico, dossiers por ejecucion y backlog priorizado'},
            {'key': 'knowledge', 'title': 'Base de Conocimiento', 'subtitle': 'Tareas confirmadas y memoria consultable'},
            {'key': 'providers', 'title': 'Stack Local', 'subtitle': 'Ollama, LM Studio, embeddings y salud tecnica'},
            {'key': 'runs', 'title': 'Historial de Ejecuciones', 'subtitle': 'Trazas por rol, reportes, severidad y dossier asociado'},
            {'key': 'centro_vivo', 'title': 'Centro Vivo', 'subtitle': 'Tablero operativo unificado: cola, IAs, heuristica, metricas y hallazgos'},
        ]
        self._current_route = 'dashboard'

    def get_routes(self) -> list[dict]:
        return self._routes

    def get_current_route(self) -> str:
        return self._current_route

    @Slot(str)
    def navigate(self, route_key: str) -> None:
        old_route = self._current_route
        valid = any(route['key'] == route_key for route in self._routes)
        if valid and route_key != self._current_route:
            self._trace_navigation('ui_navigation_requested', from_route=old_route, to_route=route_key)
            self._current_route = route_key
            self.currentRouteChanged.emit()
            self._trace_navigation('ui_navigation_applied', from_route=old_route, to_route=route_key)
        elif not valid:
            self._trace_navigation('ui_navigation_rejected', from_route=old_route, to_route=route_key, reason='unknown_route')

    def _trace_navigation(self, kind: str, **data: object) -> None:
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(kind, **data)
        except Exception:
            pass

    routes = Property(list, get_routes, constant=True)
    currentRoute = Property(str, get_current_route, notify=currentRouteChanged)
