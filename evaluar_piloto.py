"""evaluar_piloto.py — evaluación 1:N con participantes voluntarios y pruebas separadas."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from access_app.domain import identify, unit
from access_app.vision import Vision


def evaluate(manifest_path, threshold=0.50, margin=0.08):
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("consent_confirmed") is not True:
        raise ValueError("Falta constancia de participación voluntaria y autorización para la evaluación")
    engine = Vision(Path(__file__).resolve().parent/"models")
    gallery, gallery_sessions, used = [], {}, set()

    def read_image(relative):
        p = (root/relative).resolve()
        data = p.read_bytes()
        fingerprint = hashlib.sha256(data).hexdigest()
        if fingerprint in used:
            raise ValueError("Hay imágenes idénticas entre altas/pruebas. Eliminá la fuga de datos")
        used.add(fingerprint)
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("No se pudo leer una captura de evaluación")
        return image

    for subject in manifest["gallery"]:
        if subject["id"] in gallery_sessions or not subject.get("session") or len(subject["images"]) < 3:
            raise ValueError("Cada alta necesita ID único, sesión y al menos tres imágenes")
        vectors = [engine.template(read_image(path))[0] for path in subject["images"]]
        gallery.append((subject["id"], unit(np.mean(vectors, axis=0))))
        gallery_sessions[subject["id"]] = subject["session"]
    results, latencies = [], []
    for probe in manifest["probes"]:
        expected = probe.get("expected_id")
        if expected is not None and expected not in gallery_sessions:
            raise ValueError("expected_id debe ser un ID registrado o null para una persona no inscrita")
        if not probe.get("session") or (expected and probe["session"] == gallery_sessions[expected]):
            raise ValueError("Las pruebas de una persona deben proceder de una sesión distinta de su alta")
        image = read_image(probe["image"])
        start = perf_counter()
        try:
            vector, _ = engine.template(image)
            result = identify(vector, gallery, threshold, margin)
            predicted, reason = result.resident_id, result.reason
        except ValueError:
            predicted, reason = None, "captura_no_apta"
        latencies.append((perf_counter()-start)*1000)
        results.append({"probe_id": probe["id"], "expected_id": expected,
                        "predicted_id": predicted, "reason": reason})
    known = [r for r in results if r["expected_id"] is not None]
    unknown = [r for r in results if r["expected_id"] is None]
    if not known or not unknown:
        raise ValueError("Se necesitan tanto pruebas de inscritos como de personas no inscritas")
    return {"source": "Participantes voluntarios; resultados de las capturas aportadas",
        "threshold": threshold, "margin": margin, "gallery_size": len(gallery),
        "known_trials": len(known), "unknown_trials": len(unknown),
        "correct_known": sum(r["predicted_id"] == r["expected_id"] for r in known),
        "rejected_known": sum(r["predicted_id"] is None for r in known),
        "wrong_identity_known": sum(r["predicted_id"] not in [None, r["expected_id"]] for r in known),
        "accepted_unknown": sum(r["predicted_id"] is not None for r in unknown),
        "unknown_false_acceptance_rate": sum(r["predicted_id"] is not None for r in unknown)/len(unknown),
        "latency_ms_median": float(np.median(latencies)),
        "latency_ms_p95": float(np.quantile(latencies, .95)),
        "liveness_tested": False, "physical_access_certified": False,
        "caution": "No seleccionar umbrales con este conjunto si se declara prueba final. "
                   "Una tasa observada cero en pocas pruebas no demuestra error real cero.",
        "trials": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--margin", type=float, default=0.08)
    parser.add_argument("--output", type=Path, default=Path("evaluacion_local.json"))
    args = parser.parse_args()
    if not 0 < args.threshold < 1 or not 0 < args.margin < 1:
        parser.error("Umbrales fuera de rango")
    try:
        report = evaluate(args.manifest, args.threshold, args.margin)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Evaluación guardada en", args.output)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, "Evaluación no completada: "+str(exc)+"\n")
