"""tests/test_updates.py — respaldo, importación, versiones y plantillas conservadas."""
import hashlib
import json
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet
import pytest

from access_app.backups import check_database, create_backup, import_data
from access_app.migrations import SCHEMA_VERSION, migrate
from access_app.store import Store


def populated(directory):
    store = Store(directory, model_signature="original-sface")
    resident = store.add_resident({"name": "Persona de prueba", "unit": "TEST", "building": "LAB"}, [1, 0])
    store.add_camera("Cámara de laboratorio", "observe", "usb:0")
    store.add_event(resident, "browser-access", "entrada")
    store.db.execute("INSERT INTO evaluation_trials(record) VALUES (?)", (store.seal({"test": "synthetic"}),))
    store.db.commit()
    return store, resident


def test_previous_version_migration_keeps_all_data_and_makes_backup(tmp_path):
    directory = tmp_path/"legacy"
    store, resident = populated(directory)
    # Recrea el esquema SIN versión/metadatos de las entregas 0.1/0.2.
    for table in ("pad_trials", "resident_credentials", "sessions", "login_attempts", "restrictions", "audit_log", "users"):
        store.db.execute("DROP TABLE "+table)
    store.db.execute("ALTER TABLE events DROP COLUMN operator_id")
    store.db.execute("DROP TABLE visit_events")
    store.db.execute("DROP TABLE visits")
    store.db.execute("DROP TABLE system_metadata")
    store.db.execute("PRAGMA user_version=0")
    store.db.commit()
    cipher = (directory/"local.key").read_bytes()
    token = store.admin_token
    encrypted = store.db.execute("SELECT template FROM residents").fetchone()[0]
    store.db.close()
    migrated = Store(directory, model_signature="original-sface")
    assert migrated.db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert migrated.resident(resident)["name"] == "Persona de prueba"
    assert migrated.gallery() == [(resident, [1, 0])]
    assert len(migrated.events()) == 1 and len(migrated.cameras()) == 1
    assert migrated.db.execute("SELECT count(*) FROM evaluation_trials").fetchone()[0] == 1
    assert migrated.admin_token == token and (directory/"local.key").read_bytes() == cipher
    assert migrated.db.execute("SELECT template FROM residents").fetchone()[0] == encrypted
    check_database(migrated.migration_backup)
    migrated.db.close()
    again = Store(directory, model_signature="original-sface")
    assert again.migration_backup is None
    again.db.close()


def test_live_database_backup_can_be_restored_without_changing_original(tmp_path):
    store, resident = populated(tmp_path/"current")
    backup = create_backup(store.directory, tmp_path/"copies")
    restored_dir = import_data(backup, tmp_path/"restored")
    restored = Store(restored_dir, model_signature="original-sface")
    assert restored.gallery() == store.gallery()
    assert restored.resident(resident) == store.resident(resident)
    assert restored.events() == store.events()
    assert restored.camera(store.cameras()[0]["id"]) == store.camera(store.cameras()[0]["id"])
    assert restored.admin_token == store.admin_token
    restored.db.close()
    store.db.close()


def test_import_never_overwrites_existing_installation(tmp_path):
    store, _ = populated(tmp_path/"origin")
    target = tmp_path/"target"
    target.mkdir()
    (target/"keep").write_text("unchanged")
    with pytest.raises(ValueError, match="ya tiene datos"):
        import_data(store.directory, target)
    assert (target/"keep").read_text() == "unchanged"
    store.db.close()


def test_legacy_program_folder_is_accepted_for_import(tmp_path):
    store, _ = populated(tmp_path/"old-program"/"data")
    target = import_data(tmp_path/"old-program", tmp_path/"new-data")
    check_database(target)
    assert store.directory.exists()
    store.db.close()


def test_wrong_key_or_incomplete_copy_does_not_create_target(tmp_path):
    store, _ = populated(tmp_path/"origin")
    store.db.close()
    (store.directory/"local.key").write_bytes(Fernet.generate_key())
    with pytest.raises(ValueError, match="clave"):
        import_data(store.directory, tmp_path/"target")
    assert not (tmp_path/"target").exists()
    (store.directory/"local.key").unlink()
    with pytest.raises(ValueError):
        import_data(store.directory, tmp_path/"target")


def test_modified_backup_detected_before_import(tmp_path):
    store, _ = populated(tmp_path/"origin")
    backup = create_backup(store.directory)
    (backup/"admin.token").write_text("different-token-long-enough-to-be-valid")
    with pytest.raises(ValueError, match="modificado"):
        import_data(backup, tmp_path/"target")
    assert not (tmp_path/"target").exists()
    store.db.close()


def test_newer_schema_is_not_downgraded(tmp_path):
    store, _ = populated(tmp_path/"origin")
    store.db.execute("PRAGMA user_version=999")
    store.db.commit()
    store.db.close()
    before = hashlib.sha256((store.directory/"access.sqlite3").read_bytes()).hexdigest()
    with pytest.raises(RuntimeError, match="más nueva"):
        Store(store.directory, model_signature="original-sface")
    assert hashlib.sha256((store.directory/"access.sqlite3").read_bytes()).hexdigest() == before


def test_different_recognition_pipeline_is_rejected_without_changing_templates(tmp_path):
    store, _ = populated(tmp_path/"origin")
    template = store.db.execute("SELECT template FROM residents").fetchone()[0]
    store.db.close()
    with pytest.raises(RuntimeError, match="motor facial"):
        Store(store.directory, model_signature="different-engine")
    same = Store(store.directory, model_signature="original-sface")
    assert same.db.execute("SELECT template FROM residents").fetchone()[0] == template
    same.db.close()


def test_failed_migration_rolls_back_schema_and_keeps_original_records(tmp_path):
    store, resident = populated(tmp_path/"origin")
    for table in ("pad_trials", "resident_credentials", "sessions", "login_attempts", "restrictions", "audit_log", "users"):
        store.db.execute("DROP TABLE "+table)
    store.db.execute("ALTER TABLE events DROP COLUMN operator_id")
    store.db.execute("DROP TABLE visit_events")
    store.db.execute("DROP TABLE visits")
    store.db.execute("DROP TABLE system_metadata")
    store.db.execute("PRAGMA user_version=0")
    store.db.commit()
    store.db.close()
    class BrokenMigration(sqlite3.Connection):
        def execute(self, query, parameters=()):
            if query.startswith("CREATE INDEX"):
                raise sqlite3.OperationalError("simulated migration failure")
            return super().execute(query, parameters)
    db = sqlite3.connect(store.directory/"access.sqlite3", factory=BrokenMigration)
    try:
        with pytest.raises(sqlite3.OperationalError, match="simulated"):
            migrate(db, store.directory, "original-sface")
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert db.execute("SELECT id FROM residents").fetchone()[0] == resident
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='system_metadata'").fetchone()
        assert list((store.directory.parent/"backups").glob("respaldo-*"))
    finally:
        db.close()
