from __future__ import annotations

try:  # pragma: no cover - exercised only when PySide6 is available
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle as _RealQQuickStyle

    PYSIDE_AVAILABLE = True

    class QQuickStyle:
        """Idempotent wrapper: ``setStyle`` only calls the real API once."""

        _applied = False

        @staticmethod
        def setStyle(style: str) -> None:
            if not QQuickStyle._applied:
                _RealQQuickStyle.setStyle(style)
                QQuickStyle._applied = True
except ImportError:  # pragma: no cover - fallback for non-UI test environments
    PYSIDE_AVAILABLE = False

    class QObject:
        def __init__(self, parent=None):
            self._parent = parent

    class _SignalProxy:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)

    class _SignalDescriptor:
        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs

        def __set_name__(self, owner, name):
            self._attr = f'_signal_proxy_{name}'

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            proxy = instance.__dict__.get(self._attr)
            if proxy is None:
                proxy = _SignalProxy()
                instance.__dict__[self._attr] = proxy
            return proxy

    def Signal(*args, **kwargs):
        return _SignalDescriptor(*args, **kwargs)

    def Slot(*args, **kwargs):
        def decorator(function):
            return function

        return decorator

    def Property(_type=None, fget=None, fset=None, fdel=None, notify=None, constant=False):
        if fget is not None:
            return property(fget, fset, fdel)
        def _decorator(func):
            return property(func)
        return _decorator

    class QTimer:
        @staticmethod
        def singleShot(_msec: int, callback):
            callback()

    class QUrl:
        def __init__(self, path: str):
            self.path = path

        @staticmethod
        def fromLocalFile(path: str) -> 'QUrl':
            return QUrl(path)

    class QGuiApplication:
        def __init__(self, argv):
            self.argv = argv

        @staticmethod
        def instance():
            return None

        def exec(self) -> int:
            return 0

        def quit(self) -> None:
            return None

    QApplication = QGuiApplication  # stub alias for non-UI environments

    class QQmlApplicationEngine:
        def __init__(self):
            self._root_objects = []

        def rootContext(self):
            return self

        def setContextProperty(self, name, value):
            setattr(self, name, value)

        def addImportPath(self, path: str):
            pass

        def load(self, url):
            self._root_objects = [url]

        def rootObjects(self):
            return self._root_objects

    class QQuickStyle:
        _applied = False

        @staticmethod
        def setStyle(_style: str) -> None:
            QQuickStyle._applied = True
