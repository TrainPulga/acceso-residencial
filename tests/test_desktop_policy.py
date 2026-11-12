"""tests/test_desktop_policy.py — permisos nativos; no render ni webcam física."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

try:
    import escritorio
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineCore import QWebEnginePermission
except ImportError:
    pytest.skip("Qt WebEngine o sus bibliotecas nativas no están instalados", allow_module_level=True)


class Request:
    def __init__(self, url, kind):
        self.url, self.kind, self.allowed = QUrl(url), kind, None

    def origin(self):
        return self.url

    def permissionType(self):
        return self.kind

    def grant(self):
        self.allowed = True

    def deny(self):
        self.allowed = False


def test_camera_requires_same_origin_and_explicit_yes():
    window = SimpleNamespace(origin=QUrl("http://127.0.0.1:8123"))
    kind = QWebEnginePermission.PermissionType.MediaVideoCapture
    request = Request("http://127.0.0.1:8123", kind)
    with patch.object(escritorio.QMessageBox, "question", return_value=escritorio.QMessageBox.StandardButton.Yes):
        escritorio.DesktopWindow.permission(window, request)
    assert request.allowed is True
    request = Request("http://127.0.0.1:8123", kind)
    with patch.object(escritorio.QMessageBox, "question", return_value=escritorio.QMessageBox.StandardButton.No):
        escritorio.DesktopWindow.permission(window, request)
    assert request.allowed is False


@pytest.mark.parametrize("url,kind", [
    ("http://127.0.0.1:8124", "MediaVideoCapture"),
    ("https://outside.example", "MediaVideoCapture"),
    ("http://127.0.0.1:8123", "MediaAudioCapture"),
    ("http://127.0.0.1:8123", "DesktopVideoCapture"),
])
def test_other_origins_microphone_and_screen_are_denied(url, kind):
    window = SimpleNamespace(origin=QUrl("http://127.0.0.1:8123"))
    request = Request(url, getattr(QWebEnginePermission.PermissionType, kind))
    with patch.object(escritorio.QMessageBox, "question") as question:
        escritorio.DesktopWindow.permission(window, request)
        question.assert_not_called()
    assert request.allowed is False


def test_external_http_requests_are_blocked():
    policy = escritorio.PrivateRequests(QUrl("http://127.0.0.1:8123"), None)
    for url, blocked in [("http://127.0.0.1:8123/static/app.js", False),
                         ("http://127.0.0.1:8124/", True),
                         ("https://outside.example/", True),
                         ("file:///private-data", True)]:
        state = []
        info = SimpleNamespace(requestUrl=lambda: QUrl(url), block=lambda value: state.append(value))
        policy.interceptRequest(info)
        assert bool(state) is blocked


def test_native_backup_menu_requires_admin_session():
    calls=[]
    page=SimpleNamespace(runJavaScript=lambda script,callback:callback('test-token'))
    accounts=SimpleNamespace(resolve=lambda token:{'role':'seguridad','force_change':False})
    window=SimpleNamespace(page=page,service=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(accounts=accounts))))
    with patch.object(escritorio.QMessageBox,'warning') as warning:
        escritorio.DesktopWindow.with_admin(window,lambda:calls.append('backup'))
        warning.assert_called_once()
    assert not calls
    accounts.resolve=lambda token:{'role':'admin','force_change':False}
    escritorio.DesktopWindow.with_admin(window,lambda:calls.append('backup'))
    assert calls==['backup']
