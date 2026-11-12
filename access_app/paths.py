"""access_app/paths.py — recursos del programa separados de los datos persistentes."""
import os
import sys
from pathlib import Path

APP_VERSION = "0.7.0"


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def default_data_directory():
    override = os.environ.get("ACCESO_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()/"AppData"/"Local"))
    elif sys.platform == "darwin":
        base = Path.home()/"Library"/"Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local"/"share"))
    return base/"AccesoResidencial"/"data"
