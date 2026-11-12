"""Select supported Python before creating a local venv; preserve app data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PROBE = "import sys,json; print(json.dumps([list(sys.version_info[:2]),sys.executable]))"
INSTALLER = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"


def probe(command):
    try:
        result = subprocess.run(
            [*command, "-c", PROBE], capture_output=True, text=True, timeout=20,
            check=True,
        )
        version, executable = json.loads(result.stdout.strip())
        if (3, 11) <= tuple(version) < (3, 14):
            return executable
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        pass
    return None


def candidates():
    for version in ("3.12", "3.13", "3.11"):
        yield ["py", "-" + version]
    yield [sys.executable]
    yield ["python"]
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles")):
        if base:
            for version in ("312", "313", "311"):
                root = Path(base)
                yield [str(root / "Programs" / "Python" / ("Python" + version) / "python.exe")]
                yield [str(root / ("Python" + version) / "python.exe")]


def prepare(root=ROOT, desktop=False):
    env = root / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not (python.exists() and probe([str(python)])):
        selected = next((found for command in candidates() if (found := probe(command))), None)
        if selected is None:
            print("\nNo se encontro Python 3.11, 3.12 o 3.13.")
            print("Instala Python 3.12 de 64 bits desde:")
            print(INSTALLER)
            print("Despues vuelve a abrir ABRIR_ACCESO.bat. Tus datos se conservan.")
            return None
        if env.exists():
            backup = root / (".venv-anterior-" + str(time.time_ns()))
            env.rename(backup)
            print("El entorno incompatible se conservo en " + backup.name)
        print("Creando entorno con " + selected, flush=True)
        subprocess.run([selected, "-m", "venv", str(env)], check=True)
        if not probe([str(python)]):
            raise RuntimeError("No se pudo crear un entorno Python compatible.")
    requirements = root / ("requirements-desktop.txt" if desktop else "requirements.txt")
    contents = requirements.read_bytes()
    if desktop:
        contents += (root / "requirements.txt").read_bytes()
    constraints = root/'constraints-seguridad.txt'
    if constraints.exists():
        contents += constraints.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()
    marker = env / ("escritorio-instalado.txt" if desktop else "paquetes-instalados.txt")
    if not marker.exists() or marker.read_text().strip() != digest:
        print("Instalando dependencias. Esta etapa necesita internet.", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)
        marker.write_text(digest, encoding="utf-8")
    return python


def main():
    try:
        desktop = "--desktop" in sys.argv or "--build" in sys.argv
        python = prepare(desktop=desktop)
        if python is None:
            return 1
        from descargar_modelos import ensure_models

        ensure_models()
        if "--build" in sys.argv:
            return subprocess.call([str(python), "-X", "utf8", str(ROOT/"crear_ejecutable.py")], cwd=ROOT)
        if desktop:
            if os.name == "nt":
                command = [str(python.with_name("pythonw.exe")), "-X", "utf8", str(ROOT/"lanzar_escritorio.pyw")]
                subprocess.Popen(command, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
                print("Aplicación de escritorio iniciada. Esta ventana de preparación puede cerrarse.")
                return 0
            return subprocess.call([str(python), "-X", "utf8", str(ROOT/"escritorio.py")], cwd=ROOT)
        return subprocess.call([str(python), "-X", "utf8", str(ROOT / "iniciar.py")], cwd=ROOT)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("\nNo se pudo preparar o iniciar el programa: " + str(exc))
        print("Copia este mensaje y las ultimas lineas de arriba para revisarlo.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
