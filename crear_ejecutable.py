"""crear_ejecutable.py — receta de build Windows, sin datos privados del operador."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != "win32":
        print("El ejecutable Windows debe compilarse y probarse en Windows.")
        return 1
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, "-m", "pip", "install", "PyInstaller==6.22.3"], check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--onedir", "--name", "AccesoResidencial", "--add-data", "models;models",
        "--add-data", "access_app/static;access_app/static", "--add-data", "docs;docs",
        "--add-data", "THIRD_PARTY_NOTICES.md;.", "--collect-all", "uvicorn",
        "lanzar_escritorio.pyw"], cwd=root, check=True)
    print("Build generado en dist/AccesoResidencial. Probar esa carpeta completa en un Windows limpio.")
    print("No compartir data, claves, respaldos ni ensayos. Esto aún no es un instalador firmado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
