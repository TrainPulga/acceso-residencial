"""access_app/migrations.py — migración versionada, respaldo y firma del motor facial."""
import hashlib
import json
import sqlite3
from pathlib import Path

from access_app.backups import create_backup

SCHEMA_VERSION = 6


def recognition_signature(models):
    manifest = json.loads((Path(models)/"manifest.json").read_text())
    description = {"models": sorted((r["file"], r["sha256"]) for r in manifest),
                   "pipeline": "yunet-landmarks-sface-align112-bgr-unit-mean-unit-v1"}
    return hashlib.sha256(json.dumps(description, sort_keys=True).encode()).hexdigest()


def migrate(db, directory, model_signature=None):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError("La base pertenece a una versión más nueva. No se modificaron sus datos")
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {"residents": {"id", "profile", "template", "consent_at", "created_at"},
                "cameras": {"id", "label", "role", "source", "authorized_at"},
                "events": {"id", "occurred_at", "resident_id", "camera_id", "direction", "evidence"}}
    if version and not set(expected).issubset(tables):
        raise RuntimeError("La base declara una versión pero le faltan tablas. No se modificó")
    if version >= 2 and not {"system_metadata", "evaluation_trials"}.issubset(tables):
        raise RuntimeError("Faltan tablas de metadatos/evaluación para esta versión")
    if version >= 3 and not {"visits", "visit_events"}.issubset(tables):
        raise RuntimeError("Faltan tablas de visitas para esta versión")
    if version >= 4 and not {"users", "sessions", "login_attempts", "restrictions", "audit_log"}.issubset(tables):
        raise RuntimeError("Faltan tablas de usuarios, restricciones o auditoría")
    if version >= 5 and ('resident_credentials' not in tables or 'last_seen_at' not in
            {r[1] for r in db.execute('PRAGMA table_info(sessions)')}):
        raise RuntimeError('Falta estructura de credenciales/sesiones para esta versión')
    if version >= 6 and 'pad_trials' not in tables:
        raise RuntimeError('Falta estructura de ensayos PAD para esta versión')
    for table, columns in expected.items():
        if table in tables and not columns.issubset({r[1] for r in db.execute("PRAGMA table_info("+table+")")}):
            raise RuntimeError("Formato de base no compatible. Restaurá un respaldo válido")
    if any(t in tables for t in expected) and not set(expected).issubset(tables):
        raise RuntimeError("La base anterior está incompleta. No se creó un padrón sustituto")
    if "system_metadata" in tables and model_signature:
        row = db.execute("SELECT value FROM system_metadata WHERE key='recognition_signature'").fetchone()
        if row and row[0] != model_signature:
            raise RuntimeError("El motor facial no es compatible con las plantillas guardadas. "
                               "Se conservaron los datos; hace falta una migración facial específica")
    backup = None
    if set(expected).issubset(tables) and version < SCHEMA_VERSION:
        backup = create_backup(directory)
    try:
        db.execute("BEGIN IMMEDIATE")
        if version < 1:
            db.execute("CREATE TABLE IF NOT EXISTS residents (id TEXT PRIMARY KEY, profile BLOB NOT NULL, "
                       "template BLOB NOT NULL, consent_at TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS cameras (id TEXT PRIMARY KEY, label TEXT NOT NULL, "
                       "role TEXT NOT NULL, source BLOB NOT NULL, authorized_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                       "occurred_at TEXT NOT NULL, resident_id TEXT REFERENCES residents(id) ON DELETE CASCADE, "
                       "camera_id TEXT NOT NULL, direction TEXT NOT NULL, evidence TEXT NOT NULL)")
        if version < 2:
            db.execute("CREATE TABLE IF NOT EXISTS evaluation_trials (id INTEGER PRIMARY KEY, record BLOB NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS system_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS events_lookup ON events(resident_id,camera_id,direction,occurred_at)")
        if version < 3:
            db.execute("CREATE TABLE visits (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                       "host_id TEXT REFERENCES residents(id) ON DELETE CASCADE, "
                       "profile BLOB NOT NULL, code_hash TEXT UNIQUE NOT NULL, request_key TEXT UNIQUE NOT NULL, "
                       "status TEXT NOT NULL CHECK(status IN ('autorizada','dentro','finalizada','cancelada')), "
                       "valid_from TEXT NOT NULL, valid_until TEXT NOT NULL, created_at TEXT NOT NULL, "
                       "updated_at TEXT NOT NULL, entered_at TEXT, left_at TEXT, revoked_at TEXT)")
            db.execute("CREATE TABLE visit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                       "visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE, "
                       "occurred_at TEXT NOT NULL, action TEXT NOT NULL, details BLOB NOT NULL)")
            db.execute("CREATE INDEX visits_host_status ON visits(host_id,status)")
        if version < 4:
            db.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, "
                       "profile BLOB NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL "
                       "CHECK(role IN ('admin','seguridad')), active INTEGER NOT NULL DEFAULT 1, "
                       "force_change INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL "
                       "REFERENCES users(id) ON DELETE CASCADE, expires_at REAL NOT NULL)")
            db.execute("CREATE TABLE login_attempts (key TEXT PRIMARY KEY, failures INTEGER NOT NULL, "
                       "blocked_until REAL NOT NULL)")
            db.execute("CREATE TABLE restrictions (id TEXT PRIMARY KEY, resident_id TEXT "
                       "REFERENCES residents(id) ON DELETE CASCADE, profile BLOB NOT NULL, "
                       "valid_from TEXT NOT NULL, valid_until TEXT NOT NULL, created_at TEXT NOT NULL, "
                       "created_by TEXT NOT NULL, released_at TEXT, released_by TEXT)")
            db.execute("CREATE INDEX restrictions_resident ON restrictions(resident_id,valid_from,valid_until)")
            db.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL, "
                       "actor_id TEXT NOT NULL, action TEXT NOT NULL, details BLOB NOT NULL, "
                       "previous_hash TEXT NOT NULL, signature TEXT NOT NULL)")
            db.execute("ALTER TABLE events ADD COLUMN operator_id TEXT")
        if version < 5:
            db.execute("ALTER TABLE sessions ADD COLUMN last_seen_at REAL NOT NULL DEFAULT 0")
            db.execute("DELETE FROM sessions")
            db.execute("CREATE TABLE resident_credentials (resident_id TEXT PRIMARY KEY "
                       "REFERENCES residents(id) ON DELETE CASCADE, pin_hash TEXT NOT NULL, "
                       "failures INTEGER NOT NULL DEFAULT 0, blocked_until REAL NOT NULL DEFAULT 0)")
        if version < 6:
            db.execute('CREATE TABLE pad_trials (id INTEGER PRIMARY KEY AUTOINCREMENT, record BLOB NOT NULL)')
            db.execute('DELETE FROM sessions')
        if model_signature:
            db.execute("INSERT OR IGNORE INTO system_metadata(key,value) VALUES ('recognition_signature',?)",
                       (model_signature,))
        db.execute("PRAGMA user_version="+str(SCHEMA_VERSION))
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Falló la integridad de referencias durante la migración")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return backup
