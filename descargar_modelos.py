"""Download and verify the exact models used by Acceso Residencial 0.7."""
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def _matches(path, spec):
    if not path.is_file() or path.stat().st_size != spec["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == spec["sha256"]


def ensure_models(root=ROOT):
    for rel in ("models/manifest.json", "models/pad/manifest.json"):
        manifest = root / rel
        specs = json.loads(manifest.read_text(encoding="utf-8"))
        for spec in specs if isinstance(specs, list) else [specs]:
            target = manifest.parent / spec["file"]
            if _matches(target, spec):
                continue
            print(f"Descargando {target.name}…", flush=True)
            temporary = None
            try:
                with urlopen(spec["source"], timeout=45) as source:
                    with NamedTemporaryFile(dir=target.parent, delete=False) as output:
                        temporary = Path(output.name)
                        remaining = spec["size"]
                        while chunk := source.read(min(1024 * 1024, remaining + 1)):
                            remaining -= len(chunk)
                            if remaining < 0:
                                raise RuntimeError(f"Tamaño inesperado para {target.name}")
                            output.write(chunk)
                if not _matches(temporary, spec):
                    raise RuntimeError(f"El modelo {target.name} no coincide con el manifiesto")
                temporary.replace(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    ensure_models()
