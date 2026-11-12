"""access_app/evaluation.py — métricas de ensayos etiquetados por un operador."""
import math
from collections import defaultdict


def rate(successes, total):
    """Wilson descriptivo; las repeticiones por persona no son independientes."""
    if total == 0:
        return {"count": successes, "total": 0, "rate": None, "wilson95_descriptive": None}
    p, z = successes / total, 1.959963984540054
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt(p * (1-p) / total + z*z / (4*total*total)) / den
    return {"count": successes, "total": total, "rate": p,
            "wilson95_descriptive": [max(0, center-half), min(1, center+half)]}


def quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered)-1)*q
    lower = int(index)
    return ordered[lower] + (ordered[min(lower+1, len(ordered)-1)]-ordered[lower])*(index-lower)


def metrics(trials, prediction_key="predicted_id"):
    # Escenas vacías o múltiples son pruebas de robustez, no intentos de un no inscrito.
    individual = [t for t in trials if t.get("condition") not in ("sin_rostro", "varios_rostros")]
    known = [t for t in individual if t["expected_id"] is not None]
    unknown = [t for t in individual if t["expected_id"] is None]
    return {
        "known_correct": rate(sum(t[prediction_key] == t["expected_id"] for t in known), len(known)),
        "known_rejected": rate(sum(t[prediction_key] is None for t in known), len(known)),
        "known_wrong_identity": rate(sum(t[prediction_key] not in (None, t["expected_id"]) for t in known), len(known)),
        "unknown_accepted": rate(sum(t[prediction_key] is not None for t in unknown), len(unknown)),
        "capture_not_suitable": rate(sum(t["reason"] == "captura_no_apta" for t in trials), len(trials)),
        "individual_trials": len(individual),
        "robustness_trials": len(trials)-len(individual),
    }


def summarize(trials):
    groups = defaultdict(list)
    for trial in trials:
        groups[(trial["session"], trial["phase"], trial["configuration_id"])].append(trial)
    reports = []
    for (session, phase, configuration), rows in groups.items():
        conditions = sorted({r["condition"] for r in rows})
        reports.append({"session": session, "phase": phase, "configuration_id": configuration,
            "configuration": rows[0]["configuration"], "trials": len(rows),
            "participants": len({r["subject_code"] for r in rows}),
            "model": metrics(rows), "baseline_nearest_without_rejection": metrics(rows, "baseline_id"),
            "latency_processing_ms_median": quantile([r["latency_ms"] for r in rows], .5),
            "latency_processing_ms_p95": quantile([r["latency_ms"] for r in rows], .95),
            "by_condition": {c: metrics([r for r in rows if r["condition"] == c]) for c in conditions},
            "final_validation_complete": False})
    return {"schema_version": "1.0", "source": "Capturas voluntarias etiquetadas manualmente; sin fotos guardadas",
        "sessions": reports, "total_trials": len(trials), "trials": trials,
        "limitations": ["La etiqueta del operador puede ser incorrecta.",
            "Sesiones distintas no acreditan independencia por sí solas. No ajustar parámetros con la prueba final.",
            "Intervalos Wilson descriptivos por intento: no corrigen dependencia entre capturas de una persona.",
            "La latencia excluye cámara, transporte HTTP y pantalla; no es latencia integral.",
            "Sin evaluación PAD, cerraduras o cruces automáticos; no certifica seguridad.",
            "Una muestra sin errores no demuestra error cero. Faltan datos cuando un denominador es cero."]}
