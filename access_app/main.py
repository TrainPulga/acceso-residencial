"""access_app/main.py — API y panel local, sin apertura física ni rastreo multicámara."""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import cv2
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from access_app.cameras import CameraHub, validate_source
from access_app.domain import PassTokens, identify, unit
from access_app.evaluation import summarize
from access_app.experiments import Experiments
from access_app.store import Store
from access_app.paths import APP_VERSION, default_data_directory, resource_root
from access_app.migrations import SCHEMA_VERSION, recognition_signature
from access_app.vision import Vision, decode_image
from access_app.auth import Accounts, AuthError, permitted
from access_app.audit import Audit
from access_app.restrictions import Restrictions
from access_app.admin_routes import register_admin_routes
from access_app.report import render_report
from access_app.visits import Visits
from access_app.visit_routes import register_visit_routes
from access_app.credentials import ResidentCredentials, PinError
from access_app.security import BoundedBody, SecurityHeaders
from access_app.pad import PadEngine, PadSequence
from access_app.pad_trials import PadTrials

ROOT = resource_root()
STATIC = ROOT / "access_app" / "static"


class FrameRequest(BaseModel):
    image: str = Field(min_length=8, max_length=5_600_000)
    camera_id: str = "browser-access"


class AccessReset(BaseModel):
    camera_id: str = Field(default='browser-access', max_length=100)


class Enrollment(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    unit: str = Field(min_length=1, max_length=60)
    building: str = Field(min_length=1, max_length=100)
    consent: bool
    adult_volunteer: bool
    images: list[str] = Field(min_length=3, max_length=5)


class CameraInput(BaseModel):
    label: str = Field(min_length=2, max_length=100)
    role: Literal["access", "observe"]
    source: str = Field(min_length=1, max_length=1000)
    authorized_private_use: bool


class Passage(BaseModel):
    token: str = Field(min_length=10, max_length=100)
    camera_id: str
    direction: Literal["entrada", "salida"]
    crossing_observed: bool
    resident_pin: str = Field(default="", max_length=12)


class PinInput(BaseModel):
    pin: str = Field(min_length=6, max_length=12, pattern=r'^[0-9]+$')
    identity_verified: bool = False


class TrialInput(BaseModel):
    image: str = Field(min_length=8, max_length=5_600_000)
    subject_code: str = Field(min_length=2, max_length=40)
    session: str = Field(min_length=2, max_length=40)
    phase: Literal["exploracion", "prueba"]
    condition: Literal["frontal", "luz_baja", "contraluz", "angulo", "lentes", "varios_rostros", "sin_rostro", "otra"]
    expected_id: str | None = None
    consent: bool
    independent_capture: bool


class PadTrialInput(BaseModel):
    image: str | None = Field(default=None, min_length=8, max_length=5_600_000)
    camera_id: str = Field(default='browser-access', max_length=100)
    subject_code: str = Field(min_length=2,max_length=40)
    session: str = Field(min_length=2,max_length=40)
    phase: Literal['exploracion','prueba']
    presentation: Literal['persona_real','foto_impresa','foto_pantalla','video_pantalla']
    condition: Literal['frontal','luz_baja','contraluz','angulo','lentes','otra']
    consent: bool
    independent_capture: bool


def create_app(data_dir=None, engine=None, pad_engine=None):
    signature = (recognition_signature(ROOT / "models") if engine is None else
                 "injected:" + type(engine).__module__ + ":" + type(engine).__qualname__)
    store = Store(data_dir or default_data_directory(), model_signature=signature)
    experiments = Experiments(store)
    pad_trials = PadTrials(store)
    accounts, audit, restrictions = Accounts(store), Audit(store), Restrictions(store)
    credentials = ResidentCredentials(store)
    if not audit.verify()["valid"]:
        store.db.close()
        raise RuntimeError("La auditoría no supera integridad. Conservá los archivos y restaurá un respaldo verificado")
    # Instalación local: reiniciar el servicio exige un nuevo login, incluso tras cierre abrupto.
    with store.lock, store.db:
        store.db.execute('DELETE FROM sessions')
    visits = Visits(store, restriction_checker=restrictions.active_external)
    hub, passes = CameraHub(), PassTokens()
    retention_days = int(os.environ.get("ACCESO_RETENTION_DAYS", "7"))
    threshold = float(os.environ.get("ACCESO_MATCH_THRESHOLD", "0.50"))
    margin = float(os.environ.get("ACCESO_MATCH_MARGIN", "0.08"))
    visit_retention_days = int(os.environ.get("ACCESO_VISIT_RETENTION_DAYS", "7"))
    if not (1 <= retention_days <= 365 and 1 <= visit_retention_days <= 365 and 0 < threshold < 1 and 0 < margin < 1):
        raise ValueError("Configuración de umbrales o conservación inválida")

    def prune():
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="milliseconds")
        store.prune_events(cutoff)
        long_cutoff = (datetime.now(timezone.utc)-timedelta(days=90)).isoformat(timespec="milliseconds")
        audit.prune(long_cutoff)
        restrictions.prune(long_cutoff)
        with store.lock, store.db:
            store.db.execute("DELETE FROM sessions WHERE expires_at<=?", (time.time(),))
        visits.prune((datetime.now(timezone.utc) - timedelta(days=visit_retention_days)).isoformat(timespec="milliseconds"))

    @asynccontextmanager
    async def lifespan(app):
        prune()
        async def cleanup():
            while True:
                await asyncio.sleep(3600)
                prune()
        task = asyncio.create_task(cleanup())
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        hub.close()

    app = FastAPI(title="Acceso Residencial · Piloto", version=APP_VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # No reflejar imágenes, contraseñas o PIN dentro del detalle de validación.
        return JSONResponse({'detail': [{'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']}
                                        for e in exc.errors()]}, status_code=422)
    app.state.store, app.state.hub = store, hub
    app.state.visits = visits
    app.state.accounts, app.state.audit, app.state.restrictions = accounts, audit, restrictions
    app.state.credentials = credentials
    app.state.pad_sequence = PadSequence()
    app.state.passes = passes
    try:
        app.state.pad = pad_engine if pad_engine is not None else PadEngine(ROOT/'models'/'pad')
        app.state.pad_error = None
    except Exception:
        app.state.pad = None
        app.state.pad_error = 'PAD no disponible. Restaurá models/pad; no se habilitan confirmaciones faciales'
    app.state.audit_error = store.db.execute("SELECT 1 FROM system_metadata WHERE key='audit_failure'").fetchone() is not None
    try:
        app.state.vision = engine if engine is not None else Vision(ROOT / "models")
        app.state.model_error = None
    except Exception:
        app.state.vision = None
        app.state.model_error = "No se pudieron verificar/cargar los modelos. Restaurá la carpeta models."
    app.state.threshold, app.state.margin = threshold, margin
    app.state.inference_lock = threading.RLock()
    app.state.gallery = store.gallery()
    buckets = defaultdict(deque)
    bucket_lock = threading.Lock()

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # El servidor se liga a loopback. Host/Origin también bloquean DNS rebinding.
        if request.url.hostname not in {"localhost", "127.0.0.1"}:
            return JSONResponse({"detail": "Este piloto solo admite acceso local"}, status_code=400)
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
        try:
            content_length = int(request.headers.get("content-length", "0") or 0)
            if content_length < 0:
                raise ValueError("negative length")
        except ValueError:
            return JSONResponse({"detail": "Tamaño de solicitud inválido"}, status_code=400)
        if content_length > 30_000_000:
            return JSONResponse({"detail": "Solicitud demasiado grande"}, status_code=413)
        if request.url.path in {"/api/auth/login", "/api/auth/setup"}:
            key = "auth:"+(request.client.host if request.client else "local")
            now = time.monotonic()
            with bucket_lock:
                bucket = buckets[key]
                while bucket and bucket[0] <= now-60:
                    bucket.popleft()
                if len(bucket) >= 10:
                    return JSONResponse({"detail": "Demasiados intentos; esperá un minuto"}, status_code=429)
                bucket.append(now)
        response = await call_next(request)
        user = getattr(request.state, "user", None)
        excluded = request.url.path == "/api/analyze" or request.url.path.endswith("/analyze")
        if user and request.method in {"POST", "PATCH", "DELETE"} and 200 <= response.status_code < 300 and not excluded:
            try:
                audit.append(user, request.method+" "+request.scope["route"].path,
                             {"resource_path": request.url.path, "status": response.status_code})
            except Exception:
                app.state.audit_error = True
                response.headers["X-Audit-Status"] = "failed"
                try:
                    with store.lock, store.db:
                        store.db.execute("INSERT OR REPLACE INTO system_metadata VALUES ('audit_failure',?)", (
                            json.dumps({"method": request.method, "resource": request.url.path,
                                        "actor_id": user["id"], "recorded_at": datetime.now(timezone.utc).isoformat()}),))
                except Exception:
                    pass  # Un disco sin escritura tampoco puede garantizar persistencia de la alerta.

        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'")
        return response

    def admin(request: Request, authorization: Annotated[str | None, Header()] = None):
        ip = request.client.host if request.client else "local"
        now = time.monotonic()
        with bucket_lock:
            bucket = buckets[ip]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= 180:
                raise HTTPException(429, "Demasiadas solicitudes; esperá un minuto")
            bucket.append(now)
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        try:
            user = accounts.resolve(supplied)
        except AuthError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        request.state.user = user
        request.state.session_binding = hashlib.sha256(supplied.encode()).hexdigest()
        route = request.scope["route"].path
        if not permitted(user, request.method, route):
            raise HTTPException(403, "Tu cuenta necesita cambiar la contraseña" if user["force_change"] else
                                "Tu rol no tiene permiso para esta acción")
        if app.state.audit_error and request.method not in {"GET", "HEAD"} and route not in {
                "/api/audit/reconcile", "/api/auth/logout", "/api/auth/password"}:
            raise HTTPException(503, "La auditoría requiere revisión. No se admiten nuevos cambios")
        return user

    def vision():
        if app.state.vision is None:
            raise HTTPException(503, app.state.model_error)
        return app.state.vision

    def camera(camera_id):
        if camera_id == "browser-access":
            return {"id": camera_id, "role": "access", "label": "Cámara de esta computadora"}
        record = store.camera(camera_id)
        if not record:
            raise HTTPException(404, "Cámara no encontrada")
        return record

    def analyze(image, camera_id, mode, operator_id=None):
        record = camera(camera_id)
        engine = vision()
        with app.state.inference_lock:
            key = (operator_id, camera_id)
            passes.invalidate(camera_id, operator_id)
            h, w = image.shape[:2]
            if mode == "detect" or record["role"] == "observe":
                app.state.pad_sequence.clear(key)
                boxes = engine.boxes(engine.detect(image))
                return {"mode": "detect", "boxes": boxes, "width": w, "height": h,
                        "face_count": len(boxes),
                        "message": "Detección sin identidad", "recognized": False, "door_unlocked": False}
            try:
                template, boxes = engine.template(image)
            except ValueError as exc:
                app.state.pad_sequence.clear(key)
                boxes = engine.boxes(engine.detect(image))
                return {"mode": "recognize", "boxes": boxes, "width": w, "height": h,
                        "face_count": len(boxes),
                        "recognized": False, "message": str(exc), "door_unlocked": False}
            match = identify(template, app.state.gallery, threshold, margin)
            candidate = store.resident(match.resident_id) if match.resident_id else None
            pad_result = {'passed':False,'state':'sin_coincidencia','message':'No hay una coincidencia facial suficiente',
                          'samples':0,'required':3,'validated_locally':False}
            if app.state.pad is None:
                app.state.pad_sequence.clear(key)
                pad_result.update(state='no_disponible',message=app.state.pad_error)
            elif candidate:
                try:
                    score = app.state.pad.predict(image, boxes)
                    pad_result = app.state.pad_sequence.observe(key,candidate['id'],hashlib.sha256(image.tobytes()).hexdigest(),score)
                except Exception:
                    app.state.pad_sequence.clear(key)
                    pad_result.update(state='error',message='No se pudo comprobar PAD; revisar cámara o modelo')
            else:
                app.state.pad_sequence.clear(key)
                try:
                    score=app.state.pad.predict(image,boxes)
                    if score < .95:
                        pad_result.update(state='posible_presentacion' if score<=.20 else 'incierto',
                            message='Posible foto/pantalla o captura incierta: revisar presencialmente')
                except Exception:
                    pad_result.update(state='error',message='No se pudo comprobar PAD')
            resident = candidate if pad_result['passed'] else None
            result = {"mode": "recognize", "boxes": boxes, "width": w, "height": h,
                      "face_count": len(boxes),
                      "recognized": bool(resident), "resident": resident, "reason": match.reason,
                      "similarity": round(match.score, 4) if match.score is not None else None,
                      "message": "Coincidencia experimental" if resident else "Sin identificación suficiente",
                      "door_unlocked": False, "liveness_verified": False,
                      'pad': pad_result, 'face_match_found': bool(candidate)}
            result['message'] = pad_result['message']
            if resident:
                blocked = restrictions.active_for_resident(resident["id"])
                result["pin_configured"] = credentials.configured(resident['id'])
                result["entry_allowed"] = not blocked
                result['entry_pin_required'] = False
                result["restriction_active"] = blocked
                if blocked:
                    result["message"] = "Revisión administrativa: entrada restringida; se puede registrar salida"
                result["pass_token"] = passes.issue(resident["id"], camera_id, operator_id, pad_passed=True)
                result["token_ttl_seconds"] = passes.ttl
            return result

    register_visit_routes(app, visits, admin, camera)
    register_admin_routes(app, accounts, audit, restrictions, admin)

    @app.post('/api/access/reset', dependencies=[Depends(admin)])
    def reset_access(payload: AccessReset, request: Request):
        with app.state.inference_lock:
            key=(request.state.session_binding,payload.camera_id)
            passes.invalidate(payload.camera_id,request.state.session_binding)
            app.state.pad_sequence.clear(key)
        return {'reset': True}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/status", dependencies=[Depends(admin)])
    def status():
        prune()
        return {**store.counts(), "models_ready": app.state.vision is not None,
                "audit_error": app.state.audit_error, "visits": visits.counts(), "visit_retention_days": visit_retention_days,
                "model_error": app.state.model_error, "physical_unlock_enabled": False,
                "liveness_verified": False, 'pad_ready':app.state.pad is not None,'pad_error':app.state.pad_error,
                'pad_validated_locally':False,'entry_pin_required':False,"retention_days": retention_days,
                "threshold": threshold, "margin": margin, "threshold_validated_locally": False,
                "hardcoded_resident_limit": None, "version": APP_VERSION, "schema_version": SCHEMA_VERSION}

    @app.get("/api/residents", dependencies=[Depends(admin)])
    def residents():
        return [{**r, 'pin_configured': credentials.configured(r['id'])} for r in store.residents()]

    @app.post('/api/residents/{resident_id}/pin', dependencies=[Depends(admin)])
    def set_resident_pin(resident_id: str, payload: PinInput):
        if not payload.identity_verified:
            raise HTTPException(400, 'Confirmá la verificación presencial de identidad y autorización')
        try:
            credentials.set(resident_id, payload.pin)
        except PinError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        return {'configured': True, 'pin_disclosed': False}

    @app.post("/api/residents", status_code=201, dependencies=[Depends(admin)])
    def enroll(payload: Enrollment):
        if not payload.consent or not payload.adult_volunteer:
            raise HTTPException(400, "El piloto requiere un adulto voluntario con autorización informada")
        if any(not v.strip() for v in [payload.name, payload.unit, payload.building]):
            raise HTTPException(400, "Completá nombre, unidad y edificio")
        if len({hashlib.sha256(s.encode()).hexdigest() for s in payload.images}) != len(payload.images):
            raise HTTPException(400, "Tomá capturas diferentes, no repitas el mismo archivo")
        engine = vision()
        try:
            with app.state.inference_lock:
                if app.state.pad is None:
                    raise HTTPException(503, app.state.pad_error)
                vectors = [engine.template(decode_image(s))[0] for s in payload.images]
                for encoded in payload.images:
                    frame=decode_image(encoded)
                    if app.state.pad.predict(frame,engine.boxes(engine.detect(frame))) < .95:
                        raise ValueError('Una captura no supera PAD. Repetí el alta presencial con la persona; no usar fotos/pantallas')
                reference = np.array(vectors[0])
                if any(float(np.dot(reference, v)) < threshold for v in vectors[1:]):
                    raise ValueError("Las capturas no son consistentes. Repetí el alta de una sola persona")
                template = unit(np.mean(vectors, axis=0))
                duplicate = identify(template, app.state.gallery, threshold, margin=0.00001)
                if duplicate.resident_id:
                    raise ValueError("Existe una plantilla demasiado parecida. Revisá las altas antes de continuar")
                resident_id = store.add_resident({"name": payload.name.strip(), "unit": payload.unit.strip(),
                    "building": payload.building.strip(), "consent_scope": "Verificación en accesos del piloto",
                    "consent_version": "piloto-1.0"}, template)
                app.state.gallery = store.gallery()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return store.resident(resident_id)

    @app.delete("/api/residents/{resident_id}", dependencies=[Depends(admin)])
    def delete_resident(resident_id: str):
        with app.state.inference_lock, store.lock:
            if visits.host_has_inside_visits(resident_id):
                raise HTTPException(409, "Hay visitas sin salida registrada para este residente. Revisalas antes de la baja")
            if not store.delete_resident(resident_id):
                raise HTTPException(404, "Residente no encontrado")
            experiments.purge_subject(resident_id)
            app.state.gallery = store.gallery()
        return {"deleted": True, "associated_passages_deleted": True}

    @app.post("/api/analyze", dependencies=[Depends(admin)])
    def analyze_frame(payload: FrameRequest, request: Request, mode: Literal["detect", "recognize"] = "recognize"):
        if payload.camera_id != 'browser-access' and camera(payload.camera_id)['role']=='access':
            raise HTTPException(400,'Una fuente del servidor debe analizarse desde su captura, no desde una imagen subida')
        try:
            image = decode_image(payload.image)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return analyze(image, payload.camera_id, mode, request.state.session_binding)

    @app.post("/api/passages", status_code=201, dependencies=[Depends(admin)])
    def confirm_passage(payload: Passage, request: Request):
        if not payload.crossing_observed:
            raise HTTPException(400, "Solo registrar un cruce observado; mirar a la cámara no es un paso")
        if camera(payload.camera_id)["role"] != "access":
            raise HTTPException(400, "Esta cámara solo admite detección sin identidad")
        with app.state.inference_lock, store.lock:
            try:
                resident_id = passes.consume(payload.token, payload.camera_id, request.state.session_binding, require_pad=True)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            if store.resident(resident_id) is None:
                raise HTTPException(409, "La persona ya no está habilitada")
            if payload.direction == "entrada" and restrictions.active_for_resident(resident_id):
                raise HTTPException(409, "Entrada restringida: requiere revisión administrativa. La salida no se bloquea")
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(timespec="milliseconds")
            recent = store.db.execute("SELECT 1 FROM events WHERE resident_id=? AND camera_id=? "
                "AND direction=? AND occurred_at>?", (resident_id, payload.camera_id, payload.direction, cutoff)).fetchone()
            if recent:
                raise HTTPException(409, "Ese paso ya se registró recientemente")
            now = store.add_event(resident_id, payload.camera_id, payload.direction, request.state.user["id"],
                                  pad_verified=True)
        return {"recorded": True, "occurred_at": now, "source": "confirmacion_manual",
                "resident_pin_verified": False, 'pad_check_passed':True, "door_unlocked": False}

    @app.get("/api/events", dependencies=[Depends(admin)])
    def events(limit: int = Query(100, ge=1, le=500), before: int | None = None):
        return store.events(limit, before)

    @app.post("/api/evaluation/trials", status_code=201, dependencies=[Depends(admin)])
    def record_trial(payload: TrialInput):
        try:
            image = decode_image(payload.image)
            model_hash = hashlib.sha256((ROOT / "models" / "manifest.json").read_bytes()).hexdigest()
            with app.state.inference_lock:
                return experiments.record(payload, image, vision(), app.state.gallery,
                                          threshold, margin, model_hash)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/evaluation/report", dependencies=[Depends(admin)])
    def evaluation_report():
        return summarize(experiments.rows())

    @app.get("/api/evaluation/report.html", dependencies=[Depends(admin)])
    def evaluation_html():
        return HTMLResponse(render_report(summarize(experiments.rows())))

    @app.delete("/api/evaluation/trials", dependencies=[Depends(admin)])
    def delete_trials():
        experiments.clear()
        return {"deleted": True}

    @app.post('/api/evaluation/pad/trials', status_code=201, dependencies=[Depends(admin)])
    def record_pad_trial(payload: PadTrialInput):
        if camera(payload.camera_id)['role'] != 'access':
            raise HTTPException(400,'Usá una fuente de acceso autorizada para el ensayo PAD')
        if app.state.pad is None:
            raise HTTPException(503,app.state.pad_error)
        try:
            if payload.camera_id=='browser-access':
                if payload.image is None:
                    raise ValueError('Iniciá la webcam y aportá una captura nueva')
                frame=decode_image(payload.image)
            else:
                frame=hub.frame(payload.camera_id)
            with app.state.inference_lock:
                return pad_trials.record(payload,frame,vision(),app.state.pad,payload.camera_id)
        except ValueError as exc:
            raise HTTPException(400,str(exc)) from exc

    @app.get('/api/evaluation/pad/report', dependencies=[Depends(admin)])
    def pad_report():
        return pad_trials.report()

    @app.delete('/api/evaluation/pad/trials', dependencies=[Depends(admin)])
    def clear_pad_trials():
        pad_trials.clear()
        return {'deleted':True}

    @app.get("/api/cameras", dependencies=[Depends(admin)])
    def cameras():
        return [{**c, "status": hub.streams[c["id"]].status if c["id"] in hub.streams else "desconectada"}
                for c in store.cameras()]

    @app.post("/api/cameras", status_code=201, dependencies=[Depends(admin)])
    def add_camera(payload: CameraInput):
        if not payload.authorized_private_use:
            raise HTTPException(400, "Confirmá autorización sobre la cámara privada y su finalidad")
        try:
            validate_source(payload.source)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"id": store.add_camera(payload.label.strip(), payload.role, payload.source)}

    @app.post("/api/cameras/{camera_id}/connect", dependencies=[Depends(admin)])
    def connect_camera(camera_id: str):
        record = camera(camera_id)
        if camera_id == "browser-access":
            raise HTTPException(400, "La cámara del navegador se inicia desde el panel")
        try:
            hub.connect(record)
        except ValueError as exc:
            raise HTTPException(400, 'Fuente no admitida por la política actual. Usá USB o RTSP privado sin loopback') from exc
        return {"status": "conectando"}

    @app.post("/api/cameras/{camera_id}/analyze", dependencies=[Depends(admin)])
    def analyze_camera(camera_id: str, request: Request, mode: Literal["detect", "recognize"] = "recognize"):
        camera(camera_id)
        try:
            image = hub.frame(camera_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        result = analyze(image, camera_id, mode, request.state.session_binding)
        h, w = image.shape[:2]
        display = cv2.resize(image, (round(w * 960 / max(w, h)), round(h * 960 / max(w, h))))
        ok, jpeg = cv2.imencode(".jpg", display)
        if ok:
            result["image"] = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
        return result

    @app.post("/api/cameras/{camera_id}/disconnect", dependencies=[Depends(admin)])
    def disconnect(camera_id: str):
        camera(camera_id)
        with app.state.inference_lock:
            hub.stop(camera_id)
            passes.invalidate_camera(camera_id)
            app.state.pad_sequence.clear_camera(camera_id)
        return {"status": "desconectada"}

    @app.delete("/api/cameras/{camera_id}", dependencies=[Depends(admin)])
    def delete_camera(camera_id: str):
        hub.stop(camera_id)
        if not store.delete_camera(camera_id):
            raise HTTPException(404, "Cámara no encontrada")
        return {"deleted": True}

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    app.add_middleware(BoundedBody)
    app.add_middleware(SecurityHeaders)
    return app
