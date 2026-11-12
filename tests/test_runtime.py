"""tests/test_runtime.py — HTTP real y cierre del servicio que usa el escritorio."""
import json
import urllib.request

from access_app.main import create_app
from access_app.runtime import LocalServer
from test_api import FakeVision


def test_server_starts_serves_authenticated_api_and_stops(tmp_path):
    app = create_app(tmp_path, FakeVision())
    login = app.state.accounts.setup(app.state.store.admin_token, "adminprueba", "Prueba", "ClaveDePrueba123!")
    service = LocalServer(app)
    try:
        origin = service.start()
        with urllib.request.urlopen(origin, timeout=5) as response:
            assert b"PILOTO 0.7" in response.read()
        request = urllib.request.Request(origin+"/api/status", headers={
            "Authorization": "Bearer "+login["token"]})
        with urllib.request.urlopen(request, timeout=5) as response:
            status = json.load(response)
        assert status["version"] == "0.7.0"
        assert status["schema_version"] == 6
        assert not status["physical_unlock_enabled"]
    finally:
        service.stop()
    assert not service.thread.is_alive()
