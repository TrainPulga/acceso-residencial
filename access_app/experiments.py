"""access_app/experiments.py — ensayos explícitos, cifrados y separados de pasos."""
import hashlib
import json
import re
import time

from access_app.domain import identify
from access_app.store import utcnow


class Experiments:
    def __init__(self, store):
        self.store = store
        with store.lock:
            store.db.execute("CREATE TABLE IF NOT EXISTS evaluation_trials "
                             "(id INTEGER PRIMARY KEY, record BLOB NOT NULL)")
            store.db.commit()

    def rows(self):
        with self.store.lock:
            return [self.store.open(r["record"]) for r in self.store.db.execute(
                "SELECT record FROM evaluation_trials ORDER BY id")]

    def clear(self):
        with self.store.lock:
            self.store.db.execute("DELETE FROM evaluation_trials")
            self.store.db.commit()

    def purge_subject(self, resident_id):
        code = hashlib.sha256(resident_id.encode()).hexdigest()
        with self.store.lock:
            ids = [r["id"] for r in self.store.db.execute("SELECT id,record FROM evaluation_trials")
                   if code in (self.store.open(r["record"])["expected_id"],
                               self.store.open(r["record"])["predicted_id"],
                               self.store.open(r["record"])["baseline_id"])]
            self.store.db.executemany("DELETE FROM evaluation_trials WHERE id=?", [(i,) for i in ids])
            self.store.db.commit()

    def record(self, payload, image, engine, gallery, threshold, margin, model_hash):
        if not payload.consent or not payload.independent_capture:
            raise ValueError("Confirmá participación adulta voluntaria y captura nueva, separada del alta")
        for value in (payload.subject_code, payload.session):
            if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", value):
                raise ValueError("Usá códigos sin nombres: letras, números, guion y guion bajo")
        if not gallery:
            raise ValueError("Registrá al menos un participante antes de evaluar")
        if payload.expected_id is not None and payload.expected_id not in {r[0] for r in gallery}:
            raise ValueError("Seleccioná un participante vigente o la opción No inscrito")
        fingerprint = hashlib.sha256(image.tobytes()).hexdigest()
        config = {"threshold": threshold, "margin": margin, "model_manifest_sha256": model_hash,
                  "gallery_size": len(gallery), "gallery_sha256": hashlib.sha256(
                      json.dumps(sorted(gallery), sort_keys=True).encode()).hexdigest()}
        config_id = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        code = lambda v: hashlib.sha256(v.encode()).hexdigest() if v is not None else None
        expected = code(payload.expected_id)
        with self.store.lock:
            old = self.rows()
            if any(r["frame_sha256"] == fingerprint for r in old):
                raise ValueError("Esta misma imagen ya fue evaluada; tomá una captura nueva")
            session_rows = [r for r in old if r["session"] == payload.session]
            if any(r["configuration_id"] != config_id or r["phase"] != payload.phase for r in session_rows):
                raise ValueError("Cambió el padrón, configuración o fase. Elegí un código de sesión nuevo")
            subject_rows = [r for r in old if r["subject_code"] == payload.subject_code]
            if any(r["expected_id"] != expected for r in subject_rows):
                raise ValueError("Ese código de participante ya corresponde a otra etiqueta")
            started = time.perf_counter()
            predicted, baseline, reason, score = None, None, "captura_no_apta", None
            try:
                vector, _ = engine.template(image)
                result = identify(vector, gallery, threshold, margin)
                predicted, reason, score = result.resident_id, result.reason, result.score
                baseline = identify(vector, gallery, -2, 0).resident_id
            except ValueError:
                pass
            row = {"occurred_at": utcnow(), "subject_code": payload.subject_code,
                   "session": payload.session, "phase": payload.phase, "condition": payload.condition,
                   "expected_id": expected, "predicted_id": code(predicted), "baseline_id": code(baseline),
                   "reason": reason, "similarity": score, "frame_sha256": fingerprint,
                   "latency_ms": (time.perf_counter()-started)*1000,
                   "configuration_id": config_id, "configuration": config,
                   "capture_source": "browser_voluntary_trial", "consent_declared": True,
                   "independent_capture_declared": True}
            self.store.db.execute("INSERT INTO evaluation_trials(record) VALUES (?)", (self.store.seal(row),))
            self.store.db.commit()
        return row
