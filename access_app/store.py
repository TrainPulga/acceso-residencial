"""access_app/store.py — SQLite local y datos identificatorios cifrados."""
import json
import os
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

from access_app.migrations import migrate
from access_app.file_security import private_path, reject_link


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Store:
    def __init__(self, directory, model_signature=None):
        self.directory = Path(directory)
        reject_link(self.directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        private_path(self.directory)
        keyfile = self.directory / "local.key"
        database = self.directory / "access.sqlite3"
        for path in (keyfile, database, self.directory/'admin.token'):
            reject_link(path)
        if database.exists() and not keyfile.exists():
            raise RuntimeError("Falta local.key. Restaurá la clave original; no se puede descifrar la base.")
        if not keyfile.exists():
            keyfile.write_bytes(Fernet.generate_key())
        private_path(keyfile)
        self.cipher = Fernet(keyfile.read_bytes())
        tokenfile = self.directory / "admin.token"
        if not tokenfile.exists():
            tokenfile.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        private_path(tokenfile)
        self.admin_token = tokenfile.read_text(encoding="utf-8").strip()
        self.lock = threading.RLock()
        self.db = sqlite3.connect(database, check_same_thread=False)
        private_path(database)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA secure_delete=ON")
        try:
            self.migration_backup = migrate(self.db, self.directory, model_signature)
        except BaseException:
            self.db.close()
            raise

    def seal(self, value):
        return self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())

    def open(self, value):
        return json.loads(self.cipher.decrypt(value))

    def residents(self):
        with self.lock:
            rows = self.db.execute("SELECT * FROM residents ORDER BY created_at DESC").fetchall()
            return [{"id": r["id"], **self.open(r["profile"]), "consent_at": r["consent_at"],
                     "created_at": r["created_at"]} for r in rows]

    def gallery(self):
        with self.lock:
            return [(r["id"], self.open(r["template"]))
                    for r in self.db.execute("SELECT id,template FROM residents")]

    def resident(self, resident_id):
        with self.lock:
            r = self.db.execute("SELECT profile FROM residents WHERE id=?", (resident_id,)).fetchone()
            return {"id": resident_id, **self.open(r["profile"])} if r else None

    def add_resident(self, profile, template):
        with self.lock:
            resident_id = uuid.uuid4().hex
            now = utcnow()
            self.db.execute("INSERT INTO residents VALUES (?,?,?,?,?)", (
                resident_id, self.seal(profile), self.seal(template), now, now))
            self.db.commit()
            return resident_id

    def delete_resident(self, resident_id):
        with self.lock:
            count = self.db.execute("DELETE FROM residents WHERE id=?", (resident_id,)).rowcount
            self.db.commit()
            return bool(count)

    def add_event(self, resident_id, camera_id, direction, operator_id=None, pin_verified=False, pad_verified=False):
        with self.lock:
            now = utcnow()
            self.db.execute("INSERT INTO events(occurred_at,resident_id,camera_id,direction,evidence,operator_id) "
                            "VALUES (?,?,?,?,?,?)", (now, resident_id, camera_id, direction,
                            "Paso confirmado manualmente por el operador; puerta simulada" +
                            ("; Se verificó PIN de residente" if pin_verified else "")+
                            ("; PAD RGB superado en secuencia (piloto por validar)" if pad_verified else ""), operator_id))
            self.db.commit()
            return now

    def events(self, limit=100, before=None):
        with self.lock:
            rows = self.db.execute("SELECT e.*, COALESCE(c.label, CASE WHEN e.camera_id='browser-access' "
                "THEN 'Cámara de esta computadora' ELSE 'Punto retirado' END) AS camera_label "
                "FROM events e LEFT JOIN cameras c ON e.camera_id=c.id "
                "WHERE (? IS NULL OR e.id < ?) ORDER BY e.id DESC LIMIT ?", (before, before, limit)).fetchall()
            return [{**dict(r), "resident": self.resident(r["resident_id"])} for r in rows]

    def prune_events(self, before):
        with self.lock:
            count = self.db.execute("DELETE FROM events WHERE occurred_at < ?", (before,)).rowcount
            self.db.commit()
            return count

    def add_camera(self, label, role, source):
        with self.lock:
            camera_id = uuid.uuid4().hex
            self.db.execute("INSERT INTO cameras VALUES (?,?,?,?,?)",
                            (camera_id, label, role, self.seal(source), utcnow()))
            self.db.commit()
            return camera_id

    def cameras(self):
        with self.lock:
            return [dict(r) for r in self.db.execute(
                "SELECT id,label,role,authorized_at FROM cameras ORDER BY label")]

    def camera(self, camera_id):
        with self.lock:
            r = self.db.execute("SELECT * FROM cameras WHERE id=?", (camera_id,)).fetchone()
            return {**dict(r), "source": self.open(r["source"])} if r else None

    def delete_camera(self, camera_id):
        with self.lock:
            count = self.db.execute("DELETE FROM cameras WHERE id=?", (camera_id,)).rowcount
            self.db.commit()
            return bool(count)

    def counts(self):
        with self.lock:
            return {table: self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("residents", "events", "cameras")}
