"""access_app/backups.py — snapshots SQLite y claves, con verificación antes de importar."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time

from cryptography.fernet import Fernet, InvalidToken
from access_app.file_security import private_path, reject_link

BACKUP_FILES = ("access.sqlite3", "local.key", "admin.token")


def normalize_source(source):
    source = Path(source).resolve()
    if not (source/"access.sqlite3").exists() and (source/"data"/"access.sqlite3").exists():
        source = source/"data"
    return source


def check_database(directory):
    directory = Path(directory)
    reject_link(directory)
    for name in BACKUP_FILES:
        reject_link(directory/name)
    if any(not (directory/n).is_file() for n in BACKUP_FILES):
        raise ValueError("La carpeta debe contener access.sqlite3, local.key y admin.token originales")
    if len((directory/"admin.token").read_text(encoding="utf-8").strip()) < 20:
        raise ValueError("La clave de administración está incompleta")
    db = sqlite3.connect((directory/"access.sqlite3").resolve().as_uri()+"?mode=ro", uri=True, timeout=10)
    try:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("La base de datos no superó la comprobación de integridad")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("La base contiene referencias incompletas")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"residents", "cameras", "events"}.issubset(tables):
            raise ValueError("La base no corresponde al formato de Acceso Residencial")
        cipher = Fernet((directory/"local.key").read_bytes())
        for table, columns in (("residents", ("profile", "template")), ("cameras", ("source",)),
                               ("evaluation_trials", ("record",)), ("visits", ("profile",)),
                               ("visit_events", ("details",)), ("users", ("profile",)),
                               ("restrictions", ("profile",)), ("audit_log", ("details",)),
                               ('pad_trials',('record',))):
            if table not in tables:
                continue
            for row in db.execute("SELECT "+",".join(columns)+" FROM "+table):
                for value in row:
                    json.loads(cipher.decrypt(value))
    except (InvalidToken, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("La clave no corresponde a la base o hay registros cifrados dañados") from exc
    finally:
        db.close()


def create_backup(directory, destination=None):
    directory = Path(directory).resolve()
    check_database(directory)
    destination = Path(destination or directory.parent/"backups").resolve()
    destination.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".preparando-", dir=destination))
    private_path(staging)
    target = destination/("respaldo-"+time.strftime("%Y%m%d-%H%M%S")+"-"+str(time.time_ns()))
    try:
        source = sqlite3.connect((directory/"access.sqlite3").as_uri()+"?mode=ro", uri=True, timeout=10)
        snapshot = sqlite3.connect(staging/"access.sqlite3")
        try:
            source.backup(snapshot)
        finally:
            snapshot.close()
            source.close()
        for name in ("local.key", "admin.token"):
            shutil.copy2(directory/name, staging/name)
            os.chmod(staging/name, 0o600)
        check_database(staging)
        manifest = {"format": "acceso-backup-1", "created_unix_ns": time.time_ns(),
                    "files": {n: hashlib.sha256((staging/n).read_bytes()).hexdigest() for n in BACKUP_FILES}}
        (staging/"backup.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for path in staging.iterdir():
            private_path(path)
        staging.rename(target)
        return target
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def import_data(source, destination):
    """Importa a una instalación vacía; no sobrescribe ni mezcla bases/claves."""
    source, destination = normalize_source(source), Path(destination).resolve()
    if source == destination:
        raise ValueError("La carpeta de origen y destino son la misma")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("El destino ya tiene datos. No se sobrescribió ningún registro")
    check_database(source)
    if (source/"backup.json").exists():
        manifest = json.loads((source/"backup.json").read_text(encoding="utf-8"))
        if manifest.get("format") != "acceso-backup-1":
            raise ValueError("Formato de respaldo no compatible")
        for name in BACKUP_FILES:
            if manifest["files"].get(name) != hashlib.sha256((source/name).read_bytes()).hexdigest():
                raise ValueError("El respaldo está incompleto o fue modificado")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".importando-", dir=destination.parent))
    private_path(staging)
    try:
        # Snapshot consistente: no copiar directamente una base abierta.
        origin = sqlite3.connect((source/"access.sqlite3").as_uri()+"?mode=ro", uri=True, timeout=10)
        target = sqlite3.connect(staging/"access.sqlite3")
        try:
            origin.backup(target)
        finally:
            target.close()
            origin.close()
        imported = sqlite3.connect(staging/"access.sqlite3")
        try:
            if imported.execute("SELECT 1 FROM sqlite_master WHERE name='sessions'").fetchone():
                imported.execute("DELETE FROM sessions")
                imported.commit()
        finally:
            imported.close()
        for name in ("local.key", "admin.token"):
            shutil.copy2(source/name, staging/name)
            os.chmod(staging/name, 0o600)
        check_database(staging)
        for path in staging.iterdir():
            private_path(path)
        if destination.exists():
            destination.rmdir()  # Solo una carpeta aún vacía; nunca se elimina contenido.
        staging.rename(destination)
        return destination
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
