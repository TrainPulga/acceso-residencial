"""tests/test_evaluation.py — evidencia técnica, no precisión de personas reales."""
import math

import pytest

from access_app.evaluation import metrics, quantile, rate
from test_api import client, enroll, image


def trial(client, **changes):
    payload = {"image": image((200, 0, 0)), "subject_code": "V01", "session": "prueba_dia2",
               "phase": "prueba", "condition": "frontal", "expected_id": None,
               "consent": True, "independent_capture": True}
    payload.update(changes)
    return client.post("/api/evaluation/trials", json=payload)


def test_no_measurement_is_not_zero_error():
    assert rate(0, 0)["rate"] is None
    result = rate(0, 4)
    assert result["wilson95_descriptive"][1] > .4
    assert quantile([], .95) is None
    assert math.isclose(quantile([10, 20, 30], .95), 29)


def test_wrong_known_is_distinct_from_unknown_acceptance():
    rows = [{"expected_id": "A", "predicted_id": "B", "reason": "coincidencia_experimental"},
            {"expected_id": "A", "predicted_id": None, "reason": "sin_coincidencia"},
            {"expected_id": None, "predicted_id": "A", "reason": "coincidencia_experimental"}]
    result = metrics(rows)
    assert result["known_wrong_identity"]["count"] == 1
    assert result["known_rejected"]["count"] == 1
    assert result["unknown_accepted"]["rate"] == 1


def test_trials_are_explicit_and_do_not_record_movements(client):
    resident = enroll(client).json()
    assert client.get("/api/evaluation/report").json()["total_trials"] == 0
    response = trial(client, expected_id=resident["id"])
    assert response.status_code == 201
    row = response.json()
    assert row["expected_id"] == row["predicted_id"]
    assert row["expected_id"] != resident["id"]
    report = client.get("/api/evaluation/report").json()
    session = report["sessions"][0]
    assert session["model"]["known_correct"]["rate"] == 1
    assert session["model"]["unknown_accepted"]["rate"] is None
    assert session["final_validation_complete"] is False
    assert client.get("/api/events").json() == []
    assert "image" not in row
    assert b'prueba_dia2' not in (client.app.state.store.directory/"access.sqlite3").read_bytes()


def test_rejection_beats_always_nearest_for_synthetic_unknown(client):
    enroll(client)
    assert trial(client, image=image((0, 0, 200))).status_code == 201
    session = client.get("/api/evaluation/report").json()["sessions"][0]
    assert session["model"]["unknown_accepted"]["count"] == 0
    assert session["baseline_nearest_without_rejection"]["unknown_accepted"]["count"] == 1


def test_reused_capture_and_session_configuration_drift_rejected(client):
    enroll(client)
    assert trial(client).status_code == 201
    assert trial(client).status_code == 400
    client.app.state.gallery.append(("synthetic-new", [0, 1]))
    assert trial(client, image=image((210, 0, 0))).status_code == 400
    assert trial(client, image=image((210, 0, 0)), session="prueba_dia3").status_code == 201


@pytest.mark.parametrize("changes", [{"consent": False}, {"independent_capture": False},
    {"subject_code": "nombre con espacios"}, {"expected_id": "not-enrolled"}])
def test_invalid_trial_rejected(client, changes):
    enroll(client)
    assert trial(client, **changes).status_code == 400


def test_subject_code_cannot_change_ground_truth(client):
    resident = enroll(client).json()
    assert trial(client, expected_id=resident["id"]).status_code == 201
    assert trial(client, image=image((0, 0, 210))).status_code == 400


def test_delete_resident_also_removes_associated_trial(client):
    resident = enroll(client).json()
    assert trial(client, expected_id=resident["id"]).status_code == 201
    client.delete("/api/residents/"+resident["id"])
    assert client.get("/api/evaluation/report").json()["total_trials"] == 0


def test_erasing_trials_and_protecting_reports(client):
    enroll(client)
    assert trial(client).status_code == 201
    assert client.get("/api/evaluation/report", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert client.delete("/api/evaluation/trials").status_code == 200
    assert client.get("/api/evaluation/report").json()["total_trials"] == 0


def test_multiple_faces_visible_but_no_access_identity_or_token(client):
    enroll(client)
    engine = client.app.state.vision
    engine.detect = lambda im: [1, 2]
    engine.boxes = lambda faces: [{"x": i*30, "y": 2, "w": 20, "h": 20} for i in faces]
    def reject(im):
        raise ValueError("Debe verse exactamente un rostro")
    engine.template = reject
    result = client.post("/api/analyze", json={"image": image((200, 0, 0))}).json()
    assert result["face_count"] == 2 and len(result["boxes"]) == 2
    assert not result["recognized"] and not result["door_unlocked"]
    assert "pass_token" not in result
    detect = client.post("/api/analyze?mode=detect", json={"image": image((200, 0, 0))}).json()
    assert detect["face_count"] == 2 and "resident" not in detect


def test_empty_and_multiple_scenes_cannot_inflate_unknown_rejection():
    result = metrics([
        {"expected_id": None, "predicted_id": None, "reason": "captura_no_apta", "condition": "sin_rostro"},
        {"expected_id": None, "predicted_id": None, "reason": "captura_no_apta", "condition": "varios_rostros"},
    ])
    assert result["unknown_accepted"]["total"] == 0
    assert result["unknown_accepted"]["rate"] is None
    assert result["robustness_trials"] == 2


def test_invalid_content_length_is_controlled(client):
    response = client.get('/api/status', headers={'Content-Length': 'not-a-number'})
    assert response.status_code == 400
    assert client.get('/api/status', headers={'Content-Length': '-1'}).status_code == 400
