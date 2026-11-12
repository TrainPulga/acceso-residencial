"""tests/test_visits.py — flujo de visitas y errores con datos sintéticos explícitos."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import sqlite3
from uuid import uuid4

import pytest

from access_app.backups import create_backup, import_data
from access_app.store import Store
from access_app.visits import VisitError, VisitMovement
from test_api import client, enroll


@pytest.fixture
def host(client):
    result = enroll(client)
    assert result.status_code == 201
    return result.json()


def payload(host, **changes):
    now = datetime.now(timezone.utc)
    data = {"request_id": str(uuid4()), "name": "Visita de laboratorio", "kind": "mantenimiento",
            "company": "Empresa de prueba", "purpose": "Prueba de procedimiento", "host_id": host["id"],
            "authorized_by": "Responsable de laboratorio", "valid_from": (now-timedelta(minutes=1)).isoformat(),
            "valid_until": (now+timedelta(hours=1)).isoformat(), "authorization_confirmed": True,
            "privacy_notice_given": True}
    data.update(changes)
    return data


def create(client, host, **changes):
    result = client.post("/api/visits", json=payload(host, **changes))
    assert result.status_code == 201, result.text
    return result.json()


def move(client, visit, action, **changes):
    body = {"camera_id": "browser-access", "identity_checked": True, "crossing_observed": True, "restrictions_checked": True}
    body.update(changes)
    return client.post(f'/api/visits/{visit["id"]}/{action}', json=body)


def test_create_entry_exit_and_history_do_not_unlock_or_use_biometrics(client, host):
    visit = create(client, host)
    assert visit["display_status"] == "autorizada" and visit["reference_code"].startswith("V-")
    assert not visit["door_unlocked"]
    assert move(client, visit, "entry").json()["status"] == "dentro"
    assert move(client, visit, "exit").json()["status"] == "finalizada"
    result = client.get(f'/api/visits/{visit["id"]}').json()
    assert [e["action"] for e in result["history"]] == ["creada", "entrada", "salida"]
    assert all(not e["door_unlocked"] for e in result["history"])
    assert result["entered_at"] and result["left_at"]
    assert client.get("/api/events").json() == []  # Historial de residentes separado.


@pytest.mark.parametrize("changes", [{"authorization_confirmed": False}, {"privacy_notice_given": False},
    {"name": "  "}, {"purpose": "  "}, {"authorized_by": "  "}])
def test_authorization_and_complete_fields_required(client, host, changes):
    assert client.post("/api/visits", json=payload(host, **changes)).status_code == 400
    assert client.get("/api/visits").json()["items"] == []


def test_requires_real_registered_host_and_private_admin_key(client, host):
    assert client.post("/api/visits", json=payload(host, host_id="missing")).status_code == 404
    assert client.post("/api/visits", json=payload(host), headers={"Authorization": "Bearer bad"}).status_code == 401
    visit = create(client, host)
    assert client.get(f'/api/visits/{visit["id"]}', headers={"Authorization": "Bearer bad"}).status_code == 401


def test_timezone_required_and_invalid_window_rejected(client, host):
    assert client.post("/api/visits", json=payload(host, valid_from="2026-10-17T10:00:00")).status_code == 400
    past = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    assert client.post("/api/visits", json=payload(host, valid_until=past)).status_code == 400


def test_scheduled_then_expired_entry_rejected_but_real_exit_allowed(client, host):
    now = datetime.now(timezone.utc)
    visit = create(client, host, valid_from=(now+timedelta(hours=1)).isoformat(),
                   valid_until=(now+timedelta(hours=2)).isoformat())
    assert visit["display_status"] == "programada"
    assert move(client, visit, "entry").status_code == 409
    client.app.state.visits.clock = lambda: now+timedelta(minutes=90)
    assert move(client, visit, "entry").status_code == 200
    client.app.state.visits.clock = lambda: now+timedelta(hours=3)
    detail = client.get(f'/api/visits/{visit["id"]}').json()
    assert detail["authorization_expired_while_inside"]
    assert move(client, visit, "exit").status_code == 200


def test_expired_unused_permission_never_records_entry(client, host):
    now = datetime.now(timezone.utc)
    visit = create(client, host)
    client.app.state.visits.clock = lambda: now+timedelta(hours=3)
    assert move(client, visit, "entry").status_code == 409
    assert client.get(f'/api/visits/{visit["id"]}').json()["display_status"] == "vencida"


def test_repeated_entry_exit_and_exit_without_entry_rejected(client, host):
    visit = create(client, host)
    assert move(client, visit, "exit").status_code == 409
    assert move(client, visit, "entry").status_code == 200
    assert move(client, visit, "entry").status_code == 409
    assert move(client, visit, "exit").status_code == 200
    assert move(client, visit, "exit").status_code == 409
    assert move(client, visit, "entry").status_code == 409


def test_same_create_request_is_idempotent_and_cannot_change_person(client, host):
    data = payload(host)
    one = client.post("/api/visits", json=data).json()
    two = client.post("/api/visits", json=data).json()
    assert one["id"] == two["id"]
    assert len(client.get(f'/api/visits/{one["id"]}').json()["history"]) == 1
    data["name"] = "Otra persona de prueba"
    assert client.post("/api/visits", json=data).status_code == 409


def test_manual_checks_and_access_camera_required(client, host):
    visit = create(client, host)
    assert move(client, visit, "entry", identity_checked=False).status_code == 400
    assert move(client, visit, "entry", crossing_observed=False).status_code == 400
    camera = client.post("/api/cameras", json={"label": "Observación de prueba", "role": "observe", "source": "usb:0",
                                               "authorized_private_use": True}).json()
    assert move(client, visit, "entry", camera_id=camera["id"]).status_code == 400
    assert move(client, visit, "entry", camera_id="missing").status_code == 404


def test_cancel_unused_blocks_entry_and_cannot_cancel_twice(client, host):
    visit = create(client, host)
    cancel = f'/api/visits/{visit["id"]}/cancel'
    assert client.post(cancel, json={"reason": "   "}).status_code == 400
    assert client.post(cancel, json={"reason": "Cancelación de prueba"}).json()["status"] == "cancelada"
    assert move(client, visit, "entry").status_code == 409
    assert client.post(cancel, json={"reason": "Otra cancelación"}).status_code == 409


def test_cancel_inside_preserves_pending_exit_and_protects_host_deletion(client, host):
    visit = create(client, host)
    assert move(client, visit, "entry").status_code == 200
    canceled = client.post(f'/api/visits/{visit["id"]}/cancel', json={"reason": "Fin anticipado de autorización"}).json()
    assert canceled["status"] == "dentro" and canceled["revoked_at"]
    assert client.delete('/api/residents/'+host["id"]).status_code == 409
    assert move(client, visit, "exit").status_code == 200
    assert client.delete('/api/residents/'+host["id"]).status_code == 200
    assert client.get(f'/api/visits/{visit["id"]}').status_code == 404


def test_private_names_codes_and_reasons_encrypted_and_not_in_list_reference(client, host):
    visit = create(client, host)
    client.post(f'/api/visits/{visit["id"]}/cancel', json={"reason": "Motivo confidencial experimental"})
    database = (client.app.state.store.directory/'access.sqlite3').read_bytes()
    for value in ["Visita de laboratorio", "Empresa de prueba", "Motivo confidencial experimental", visit["reference_code"]]:
        assert value.encode() not in database
    listing = client.get('/api/visits', params={"q": visit["reference_code"]}).json()
    assert len(listing["items"]) == 1 and "reference_code" not in listing["items"][0]


def test_filters_pagination_and_pending_exit_counts(client, host):
    a = create(client, host, name="Persona Alfa")
    b = create(client, host, name="Persona Beta")
    move(client, a, "entry")
    inside = client.get('/api/visits?inside=true').json()["items"]
    assert [r["id"] for r in inside] == [a["id"]]
    one = client.get('/api/visits?limit=1').json()
    assert one["items"][0]["id"] == b["id"] and one["next_before"] == b["id"]
    two = client.get('/api/visits', params={"limit": 1, "before": one["next_before"]}).json()
    assert two["items"][0]["id"] == a["id"] and two["next_before"] is None
    assert client.get('/api/visits?q=Alfa').json()["items"][0]["id"] == a["id"]
    counts = client.get('/api/status').json()["visits"]
    assert counts == {"inside": 1, "authorized_now": 1}


def test_retention_never_hides_a_visit_with_no_recorded_exit(client, host):
    a, b = create(client, host), create(client, host)
    move(client, a, "entry")
    move(client, b, "entry")
    move(client, b, "exit")
    store = client.app.state.store
    old = (datetime.now(timezone.utc)-timedelta(days=40)).isoformat(timespec="milliseconds")
    store.db.execute("UPDATE visits SET updated_at=?, valid_until=?", (old, old))
    store.db.commit()
    client.get('/api/status')
    assert client.get(f'/api/visits/{a["id"]}').json()["status"] == "dentro"
    assert client.get(f'/api/visits/{b["id"]}').status_code == 404
    assert store.db.execute("SELECT count(*) FROM visit_events WHERE visit_id=?", (b["id"],)).fetchone()[0] == 0


def test_concurrent_entry_produces_one_event(client, host):
    visit = create(client, host)
    manager = client.app.state.visits
    movement = VisitMovement(identity_checked=True, crossing_observed=True, restrictions_checked=True)
    camera = {"id": "browser-access", "label": "Prueba", "role": "access"}
    def attempt():
        try:
            manager.move(visit["id"], "entrada", movement, camera)
            return 200
        except VisitError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(statuses) == [200, 409]
    assert [e["action"] for e in manager.detail(visit["id"])["history"]].count("entrada") == 1


def test_visits_backup_and_restore_preserve_history(client, host, tmp_path):
    visit = create(client, host)
    move(client, visit, "entry")
    store = client.app.state.store
    backup = create_backup(store.directory, tmp_path/'backup')
    target = import_data(backup, tmp_path/'restored')
    restored = Store(target)
    from access_app.visits import Visits
    assert Visits(restored).detail(visit["id"]) == client.get(f'/api/visits/{visit["id"]}').json()
    restored.db.close()


def test_schema2_migration_preserves_existing_resident_template_and_key(tmp_path):
    directory = tmp_path/'old03'
    store = Store(directory, model_signature="unchanged")
    resident = store.add_resident({"name": "Prueba", "building": "TEST", "unit": "1"}, [1, 0])
    encrypted = store.db.execute("SELECT template FROM residents").fetchone()[0]
    key = (directory/'local.key').read_bytes()
    for table in ("pad_trials", "resident_credentials", "sessions", "login_attempts", "restrictions", "audit_log", "users"):
        store.db.execute("DROP TABLE "+table)
    store.db.execute("ALTER TABLE events DROP COLUMN operator_id")
    store.db.execute("DROP TABLE visit_events")
    store.db.execute("DROP TABLE visits")
    store.db.execute("PRAGMA user_version=2")
    store.db.commit()
    store.db.close()
    updated = Store(directory, model_signature="unchanged")
    assert updated.migration_backup is not None
    assert updated.resident(resident)["name"] == "Prueba"
    assert updated.db.execute("SELECT template FROM residents").fetchone()[0] == encrypted
    assert (directory/'local.key').read_bytes() == key
    assert updated.db.execute("PRAGMA user_version").fetchone()[0] == 6
    updated.db.close()


def test_damaged_visitor_record_blocks_backup(client, host, tmp_path):
    visit = create(client, host)
    store = client.app.state.store
    store.db.execute("UPDATE visits SET profile=? WHERE id=?", (b"invalid-ciphertext", visit["id"]))
    store.db.commit()
    with pytest.raises(ValueError, match="cifrados"):
        create_backup(store.directory, tmp_path/'invalid-backups')
    assert not (tmp_path/'invalid-backups').exists()


def test_common_area_maintenance_does_not_require_enrolling_a_fake_resident(client):
    data = payload({"id": "unused"}, host_id=None, host_kind="administracion",
                   building="Edificio de laboratorio", destination="Sala de máquinas")
    result = client.post('/api/visits', json=data)
    assert result.status_code == 201
    visit = result.json()
    assert visit["host_id"] is None and visit["host"]["name"] == "Administración"
    assert move(client, visit, "entry").status_code == 200
    assert move(client, visit, "exit").status_code == 200
    assert client.get('/api/residents').json() == []


def test_common_area_destination_must_be_defined(client, host):
    assert client.post('/api/visits', json=payload(host, host_id=None, host_kind="administracion")).status_code == 400
    assert client.post('/api/visits', json=payload(host, host_kind="administracion", building="TEST")).status_code == 400


def test_failed_schema2_to3_migration_rolls_back_new_tables(tmp_path):
    from access_app.migrations import migrate
    directory = tmp_path/'old03'
    store = Store(directory, model_signature="unchanged")
    resident = store.add_resident({"name": "Prueba", "building": "TEST", "unit": "1"}, [1, 0])
    for table in ("pad_trials", "resident_credentials", "sessions", "login_attempts", "restrictions", "audit_log", "users"):
        store.db.execute("DROP TABLE "+table)
    store.db.execute("ALTER TABLE events DROP COLUMN operator_id")
    store.db.execute("DROP TABLE visit_events")
    store.db.execute("DROP TABLE visits")
    store.db.execute("PRAGMA user_version=2")
    store.db.commit()
    store.db.close()
    class BrokenVisitIndex(sqlite3.Connection):
        def execute(self, query, parameters=()):
            if query.startswith("CREATE INDEX visits_host_status"):
                raise sqlite3.OperationalError("simulated visits migration failure")
            return super().execute(query, parameters)
    db = sqlite3.connect(directory/'access.sqlite3', factory=BrokenVisitIndex)
    try:
        with pytest.raises(sqlite3.OperationalError, match="simulated"):
            migrate(db, directory, "unchanged")
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("SELECT id FROM residents").fetchone()[0] == resident
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='visits'").fetchone()
    finally:
        db.close()
