"""recuperar_administrador.py — recuperación offline por administrador del sistema operativo."""
import argparse
import ctypes
import getpass
import os
from pathlib import Path
import sys

from access_app.auth import Accounts
from access_app.audit import Audit
from access_app.backups import create_backup
from access_app.paths import default_data_directory
from access_app.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    privileged = bool(ctypes.windll.shell32.IsUserAnAdmin()) if os.name == "nt" else os.geteuid() == 0
    if not privileged:
        print("La recuperación requiere una cuenta administradora del sistema operativo.")
        return 1
    directory = args.data_dir or default_data_directory()
    if not (directory/"access.sqlite3").exists():
        print("No existe la base en esa ubicación. Usá --data-dir con la ruta original.")
        return 1
    # El bloqueo Qt de escritorio debe estar libre antes de tocar credenciales.
    from PySide6.QtCore import QLockFile
    lock = QLockFile(str(directory.parent/"desktop.lock"))
    if not lock.tryLock(0):
        print("Cerrá la aplicación antes de recuperar la cuenta.")
        return 1
    store = None
    try:
        store = Store(directory)
        audit = Audit(store)
        if not audit.verify()["valid"]:
            raise ValueError("La auditoría requiere revisión/restauración antes de recuperar usuarios")
        print("Instalación:", directory)
        if input("Escribí RECUPERAR para confirmar acceso autorizado a esta instalación: ").strip() != "RECUPERAR":
            return 1
        username = input("Usuario administrador existente: ").strip().lower()
        row = store.db.execute("SELECT * FROM users WHERE username=? AND role='admin'", (username,)).fetchone()
        if row is None:
            raise ValueError("No existe ese administrador. No se creó una cuenta sustituta")
        password = getpass.getpass("Nueva contraseña temporal (mínimo 12 caracteres): ")
        if password != getpass.getpass("Repetir contraseña: "):
            raise ValueError("Las contraseñas no coinciden")
        if not 12 <= len(password) <= 256:
            raise ValueError("Longitud de contraseña no válida")
        backup = create_backup(directory)
        accounts = Accounts(store)
        accounts.set_password(row["id"], password)
        with store.lock, store.db:
            store.db.execute("UPDATE users SET active=1 WHERE id=?", (row["id"],))
            store.db.execute("DELETE FROM sessions")
        actor = accounts.public(store.db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone())
        audit.append(actor, "RECUPERACION_OFFLINE", {"source": "administrador_sistema_operativo"})
        print("Cuenta recuperada; sesiones revocadas. Deberá cambiar la contraseña al ingresar.")
        print("Respaldo previo:", backup)
        return 0
    except Exception as exc:
        print("Recuperación no completada:", str(exc))
        return 1
    finally:
        if store is not None:
            store.db.close()
        lock.unlock()


if __name__ == "__main__":
    sys.exit(main())
