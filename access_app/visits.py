"""access_app/visits.py — permisos temporales y pasos de visitas confirmados manualmente."""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    request_id: UUID
    name: str = Field(min_length=2, max_length=100)
    kind: Literal["visita", "mantenimiento", "servicio"]
    company: str = Field(default="", max_length=100)
    purpose: str = Field(min_length=2, max_length=250)
    host_id: str | None = Field(default=None, min_length=1, max_length=64)
    host_kind: Literal["residente", "administracion"] = "residente"
    building: str = Field(default="", max_length=100)
    destination: str = Field(default="Áreas comunes", max_length=100)
    authorized_by: str = Field(min_length=2, max_length=100)
    valid_from: datetime
    valid_until: datetime
    authorization_confirmed: bool
    privacy_notice_given: bool
    external_record_id: str | None = Field(default=None, max_length=64)
    external_identity_verified: bool = False


class VisitMovement(BaseModel):
    camera_id: str = Field(default="browser-access", min_length=1, max_length=64)
    identity_checked: bool
    crossing_observed: bool
    restrictions_checked: bool = False


class VisitCancellation(BaseModel):
    reason: str = Field(min_length=3, max_length=250)


class VisitError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def iso(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise VisitError("La fecha debe incluir zona horaria")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")


class Visits:
    def __init__(self, store, clock=lambda: datetime.now(timezone.utc), restriction_checker=None):
        self.store, self.clock, self.restriction_checker = store, clock, restriction_checker

    def _row(self, visit_id):
        row = self.store.db.execute("SELECT * FROM visits WHERE id=?", (visit_id,)).fetchone()
        if row is None:
            raise VisitError("Visita no encontrada", 404)
        return row

    def _public(self, row, include_code=False):
        profile = self.store.open(row["profile"])
        profile.pop("request_hash", None)
        if not include_code:
            profile.pop("reference_code", None)
        result = {**{k: row[k] for k in row.keys() if k not in ("profile", "code_hash")}, **profile}
        status = row["status"]
        now = iso(self.clock())
        if status == "autorizada":
            status = "programada" if now < row["valid_from"] else "vencida" if now >= row["valid_until"] else status
        result["display_status"] = status
        result["authorization_expired_while_inside"] = row["status"] == "dentro" and now >= row["valid_until"]
        result["door_unlocked"] = False
        return result

    def _event(self, visit_id, action, now, actor=None, **details):
        details.update({"evidence": "Declaración manual del operador", "authenticated_operator":
                        actor["id"] if actor else "prueba_tecnica_sin_sesion",
                        "operator_name": actor["name"] if actor else "Prueba técnica", "door_unlocked": False})
        self.store.db.execute("INSERT INTO visit_events(visit_id,occurred_at,action,details) VALUES (?,?,?,?)",
                              (visit_id, now, action, self.store.seal(details)))

    def create(self, payload, actor=None):
        if not payload.authorization_confirmed or not payload.privacy_notice_given:
            raise VisitError("Confirmá la autorización y que se informó el uso de los datos")
        if any(not value.strip() for value in (payload.name, payload.purpose, payload.authorized_by)):
            raise VisitError("Completá nombre, motivo y quién autoriza")
        start, end, now = iso(payload.valid_from), iso(payload.valid_until), iso(self.clock())
        if end <= start or end <= now:
            raise VisitError("El permiso debe finalizar después del inicio y aún estar vigente o programado")
        if payload.external_record_id:
            if not payload.external_identity_verified or self.restriction_checker is None:
                raise VisitError("Verificá manualmente que el registro externo corresponde a esta persona")
            self.restriction_checker(payload.external_record_id)
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            request_hash = hashlib.sha256(json.dumps(payload.model_dump(mode="json", exclude={"request_id"}),
                                                      sort_keys=True).encode()).hexdigest()
            previous = self.store.db.execute("SELECT * FROM visits WHERE request_key=?", (str(payload.request_id),)).fetchone()
            if previous is not None:
                if self.store.open(previous["profile"])["request_hash"] != request_hash:
                    raise VisitError("La misma solicitud no puede crear una autorización distinta", 409)
                return self._public(previous, True)
            if payload.host_kind == "residente":
                host = self.store.resident(payload.host_id)
                if host is None:
                    raise VisitError("Seleccioná un residente registrado como anfitrión", 404)
                host_info = {k: host[k] for k in ("name", "building", "unit")}
            else:
                if payload.host_id is not None or not payload.building.strip() or not payload.destination.strip():
                    raise VisitError("Para administración indicá edificio y destino, sin asociar un residente")
                host_info = {"name": "Administración", "building": payload.building.strip(),
                             "unit": payload.destination.strip()}
            code = "V-"+secrets.token_hex(8).upper()
            profile = {"name": payload.name.strip(), "kind": payload.kind, "company": payload.company.strip(),
                       "purpose": payload.purpose.strip(), "authorized_by": payload.authorized_by.strip(),
                       "host": host_info, "host_kind": payload.host_kind,
                       "reference_code": code, "request_hash": request_hash, "authorization_confirmed": True, "privacy_notice_given": True,
                       "external_record_id": payload.external_record_id,
                       "authorization_method": "declaracion_operador_autenticado", "policy_version": "visitas-2"}
            cursor = self.store.db.execute("INSERT INTO visits(host_id,profile,code_hash,request_key,status,valid_from,"
                "valid_until,created_at,updated_at) VALUES (?,?,?,?,'autorizada',?,?,?,?)", (
                    payload.host_id, self.store.seal(profile), hashlib.sha256(code.encode()).hexdigest(),
                    str(payload.request_id), start, end, now, now))
            visit_id = cursor.lastrowid
            self._event(visit_id, "creada", now, actor)
            return self._public(self._row(visit_id), True)

    def list(self, limit=100, before=None, query="", only_inside=False):
        query = query.strip().casefold()
        with self.store.lock:
            rows = self.store.db.execute("SELECT * FROM visits WHERE (? IS NULL OR id<?) "
                "AND (?=0 OR status='dentro') ORDER BY id DESC", (before, before, int(only_inside)))
            selected, has_more = [], False
            for row in rows:
                record = self._public(row, True)
                text = " ".join([record["name"], record["company"], record["reference_code"],
                                 record["host"]["name"], record["host"]["building"], record["host"]["unit"]])
                if query and query not in text.casefold():
                    continue
                if len(selected) >= limit:
                    has_more = True
                    break
                record.pop("reference_code", None)
                selected.append(record)
            return {"items": selected, "next_before": selected[-1]["id"] if selected and has_more else None}

    def detail(self, visit_id):
        with self.store.lock:
            result = self._public(self._row(visit_id), True)
            result["history"] = [{"occurred_at": r["occurred_at"], "action": r["action"],
                                  **self.store.open(r["details"])} for r in self.store.db.execute(
                "SELECT * FROM visit_events WHERE visit_id=? ORDER BY id", (visit_id,))]
            return result

    def move(self, visit_id, action, payload, camera, actor=None):
        if action not in ("entrada", "salida"):
            raise VisitError("Dirección de movimiento no admitida")
        if not payload.identity_checked or not payload.crossing_observed:
            raise VisitError("Verificá a la persona y confirmá el cruce observado; no alcanza un código")
        if camera["role"] != "access":
            raise VisitError("Seleccioná una cámara/punto de acceso autorizado")
        now = iso(self.clock())
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            row = self._row(visit_id)
            if action == "entrada":
                if not payload.restrictions_checked:
                    raise VisitError("Confirmá que revisaste restricciones y verificaste la identidad")
                external = self.store.open(row["profile"]).get("external_record_id")
                if external and self.restriction_checker and self.restriction_checker(external):
                    raise VisitError("El registro externo asociado tiene una restricción vigente", 409)
                if row["status"] != "autorizada" or row["revoked_at"] is not None:
                    raise VisitError("Este permiso ya se usó o fue cancelado", 409)
                if not row["valid_from"] <= now < row["valid_until"]:
                    raise VisitError("El permiso aún no comenzó o está vencido", 409)
                if row["host_id"] is not None and self.store.resident(row["host_id"]) is None:
                    raise VisitError("El residente anfitrión ya no está registrado", 409)
                self.store.db.execute("UPDATE visits SET status='dentro',entered_at=?,updated_at=? WHERE id=?",
                                      (now, now, visit_id))
            else:
                if row["status"] != "dentro":
                    raise VisitError("No hay una entrada pendiente de salida para esta visita", 409)
                # El vencimiento/cancelación nunca impide registrar la salida observada.
                self.store.db.execute("UPDATE visits SET status='finalizada',left_at=?,updated_at=? WHERE id=?",
                                      (now, now, visit_id))
            self._event(visit_id, action, now, actor, camera_id=camera["id"], camera_label=camera["label"],
                        identity_checked=True, crossing_observed=True)
            return self._public(self._row(visit_id))

    def cancel(self, visit_id, reason, actor=None):
        if len(reason.strip()) < 3:
            raise VisitError("Indicá el motivo de cancelación")
        now = iso(self.clock())
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            row = self._row(visit_id)
            if row["status"] in ("finalizada", "cancelada") or row["revoked_at"] is not None:
                raise VisitError("El permiso ya terminó o fue cancelado", 409)
            status = "dentro" if row["status"] == "dentro" else "cancelada"
            self.store.db.execute("UPDATE visits SET status=?,revoked_at=?,updated_at=? WHERE id=?",
                                  (status, now, now, visit_id))
            self._event(visit_id, "cancelada", now, actor, reason=reason.strip())
            return self._public(self._row(visit_id))

    def host_has_inside_visits(self, host_id):
        with self.store.lock:
            return self.store.db.execute("SELECT 1 FROM visits WHERE host_id=? AND status='dentro' LIMIT 1",
                                         (host_id,)).fetchone() is not None

    def prune(self, before):
        with self.store.lock, self.store.db:
            cursor = self.store.db.execute("DELETE FROM visits WHERE "
                "(status IN ('finalizada','cancelada') AND updated_at<?) OR "
                "(status='autorizada' AND valid_until<?)", (before, before))
            return cursor.rowcount

    def counts(self):
        now = iso(self.clock())
        with self.store.lock:
            return {"inside": self.store.db.execute("SELECT count(*) FROM visits WHERE status='dentro'").fetchone()[0],
                    "authorized_now": self.store.db.execute("SELECT count(*) FROM visits WHERE status='autorizada' "
                        "AND valid_from<=? AND valid_until>?", (now, now)).fetchone()[0]}
