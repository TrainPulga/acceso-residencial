"""tests/test_api.py — seguridad y flujos con vectores sintéticos; no mide biometría."""
import base64
import io
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from access_app.main import create_app
from access_app.store import Store


class FakeVision:
    """Solo prueba lógica; no representa un reconocedor ni personas reales."""
    def detect(self, image):
        return [np.array([1, 2, 80, 80])]

    def boxes(self, faces):
        return [{"x": 1, "y": 2, "w": 80, "h": 80}]

    def template(self, image):
        b, g, r = image[0, 0]
        return ([1.0, 0.0] if r > b else [0.0, 1.0]), self.boxes([])


class FakePad:
    """Control de flujo simulado; NO mide suplantación real."""
    metadata={'model':'synthetic-pad','sha256':'synthetic','threshold':.95}
    score=.99
    def predict(self,image,boxes): return self.score


def image(color):
    f = io.BytesIO()
    Image.new("RGB", (100, 100), color).save(f, "PNG")
    return base64.b64encode(f.getvalue()).decode()


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, FakeVision(), FakePad())
    clock=[0.0]
    def tick():
        clock[0]+=1.1
        return clock[0]
    app.state.pad_sequence.clock=tick
    app.state.scan_index=0
    with TestClient(app, base_url="http://127.0.0.1") as c:
        result = c.post("/api/auth/setup", json={"setup_key": app.state.store.admin_token,
            "username": "adminprueba", "name": "Administrador de laboratorio",
            "password": "ClaveDePrueba123!"})
        assert result.status_code == 201, result.text
        c.headers.update({"Authorization": "Bearer " + result.json()["token"]})
        yield c


def enroll(client, configure_pin=True):
    result = client.post("/api/residents", json={"name": "Participante experimental", "unit": "TEST-1",
        "building": "Escenario de prueba", "consent": True, "adult_volunteer": True,
        "images": [image((n, 0, 0)) for n in (170, 180, 190)]})
    if result.status_code == 201 and configure_pin:
        assert client.post("/api/residents/"+result.json()["id"]+"/pin", json={"pin":"729481","identity_verified":True}).status_code == 200
    return result


def scan(client):
    # Tres capturas sintéticas distintas, separadas por reloj controlado, NO personas reales.
    result=None
    for _ in range(3):
        n=client.app.state.scan_index;client.app.state.scan_index+=1
        result=client.post('/api/analyze',json={'image':image((200+n%40,n//40,0)),
                                               'camera_id':'browser-access'}).json()
    return result


def test_private_api_requires_key(client):
    assert client.get("/api/residents", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_other_origins_and_hosts_are_rejected(client):
    assert client.get("/api/status", headers={"Origin": "https://another.example"}).status_code == 403
    assert client.get("/api/status", headers={"Host": "another.example"}).status_code == 400


def test_consent_and_adult_required(client):
    result = client.post("/api/residents", json={"name": "Prueba", "unit": "TEST", "building": "TEST",
        "consent": False, "adult_volunteer": True, "images": [image((n, 0, 0)) for n in (1, 2, 3)]})
    assert result.status_code == 400


def test_repeated_capture_is_rejected(client):
    result = client.post("/api/residents", json={"name": "Prueba", "unit": "TEST", "building": "TEST",
        "consent": True, "adult_volunteer": True, "images": [image((10, 0, 0))]*3})
    assert result.status_code == 400


def test_match_does_not_record_or_unlock(client):
    assert enroll(client).status_code == 201
    result = scan(client)
    assert result["recognized"] is True
    assert result["door_unlocked"] is False
    assert result["liveness_verified"] is False
    assert client.get("/api/events").json() == []


def test_unknown_face_has_no_identity_or_token(client):
    enroll(client)
    result = client.post("/api/analyze", json={"image": image((0, 0, 200))}).json()
    assert not result["recognized"]
    assert "pass_token" not in result


def test_confirmed_pass_and_replay_protection(client):
    enroll(client)
    result = scan(client)
    payload = {"token": result["pass_token"], "camera_id": "browser-access",
               "direction": "entrada", "crossing_observed": True, "resident_pin":"729481"}
    assert client.post("/api/passages", json=payload).status_code == 201
    assert client.post("/api/passages", json=payload).status_code == 409
    assert len(client.get("/api/events").json()) == 1
    payload["token"] = scan(client)["pass_token"]
    assert client.post("/api/passages", json=payload).status_code == 409


def test_crossing_must_be_observed(client):
    enroll(client)
    payload = {"token": scan(client)["pass_token"], "camera_id": "browser-access",
               "direction": "entrada", "crossing_observed": False}
    assert client.post("/api/passages", json=payload).status_code == 400
    assert client.get("/api/events").json() == []


def test_baja_deletes_template_and_associated_events(client):
    resident = enroll(client).json()
    payload = {"token": scan(client)["pass_token"], "camera_id": "browser-access",
               "direction": "salida", "crossing_observed": True}
    assert client.post("/api/passages", json=payload).status_code == 201
    assert client.delete("/api/residents/"+resident["id"]).status_code == 200
    assert client.get("/api/events").json() == []
    assert client.app.state.store.gallery() == []
    assert not scan(client)["recognized"]


def test_secondary_camera_never_identifies(client):
    enroll(client)
    cam = client.post("/api/cameras", json={"label": "Observación de prueba", "role": "observe",
        "source": "usb:0", "authorized_private_use": True}).json()
    result = client.post("/api/analyze", json={"image": image((200, 0, 0)), "camera_id": cam["id"]}).json()
    assert result["mode"] == "detect"
    assert "resident" not in result and "pass_token" not in result


def test_revoked_match_cannot_record_a_passage(client):
    resident = enroll(client).json()
    result = scan(client)
    client.delete("/api/residents/"+resident["id"])
    payload = {"token": result["pass_token"], "camera_id": "browser-access",
               "direction": "entrada", "crossing_observed": True, "resident_pin":"729481"}
    assert client.post("/api/passages", json=payload).status_code == 409
    assert client.get("/api/events").json() == []


def test_incomplete_or_corrupted_frame_rejected(client):
    assert client.post("/api/analyze", json={"image": "invalid-data"}).status_code == 400


def test_duplicate_resident_does_not_expand_gallery(client):
    assert enroll(client).status_code == 201
    assert enroll(client).status_code == 400
    assert client.get("/api/status").json()["residents"] == 1


def test_personal_fields_encrypted_at_rest(client):
    enroll(client)
    binary = (client.app.state.store.directory/"access.sqlite3").read_bytes()
    assert b"Participante experimental" not in binary
    assert b"Escenario de prueba" not in binary
    assert not list(client.app.state.store.directory.glob("*.jpg"))


def test_retention_excludes_old_passages(client):
    enroll(client)
    store = client.app.state.store
    resident_id = store.residents()[0]["id"]
    store.add_event(resident_id, "browser-access", "entrada")
    old = (datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
    store.db.execute("UPDATE events SET occurred_at=?", (old,))
    store.db.commit()
    assert client.get("/api/status").json()["events"] == 0


def test_missing_key_does_not_create_new_unreadable_identity(tmp_path):
    Store(tmp_path)
    (tmp_path/"local.key").unlink()
    with pytest.raises(RuntimeError):
        Store(tmp_path)
