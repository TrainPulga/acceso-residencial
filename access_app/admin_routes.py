"""access_app/admin_routes.py — configuración inicial, cuentas, auditoría y restricciones."""
from datetime import datetime
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from access_app.auth import AuthError
from access_app.visits import VisitError


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=256)


class AccountInput(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "seguridad"] = "seguridad"


class Setup(AccountInput):
    setup_key: str = Field(min_length=10, max_length=200)


class AccountUpdate(BaseModel):
    role: Literal["admin", "seguridad"]
    active: bool


class NewPassword(BaseModel):
    password: str = Field(min_length=12, max_length=256)
    current_password: str = Field(default="", max_length=256)


class RestrictionInput(BaseModel):
    resident_id: str | None = Field(default=None, max_length=64)
    name: str = Field(default="", max_length=100)
    reference: str = Field(default="", max_length=150)
    reason: str = Field(min_length=3, max_length=500)
    valid_from: datetime
    valid_until: datetime
    authorized_decision: bool
    identity_verified: bool = False


class Reason(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def register_admin_routes(app, accounts, audit, restrictions, guard):
    def perform(callback, *args):
        try:
            return callback(*args)
        except (AuthError, VisitError) as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @app.get("/api/auth/status")
    def setup_status():
        return {"setup_required": accounts.setup_required()}

    @app.post("/api/auth/setup", status_code=201)
    def setup(payload: Setup, request: Request):
        result = perform(accounts.setup, payload.setup_key, payload.username, payload.name, payload.password)
        request.state.user = result["user"]
        return result

    @app.post("/api/auth/login")
    def login(payload: Login, request: Request):
        result = perform(accounts.login, payload.username, payload.password, request.client.host if request.client else "local")
        request.state.user = result["user"]
        return result

    private = APIRouter(dependencies=[Depends(guard)])

    @private.get("/api/auth/me")
    def me(request: Request):
        return request.state.user

    @private.post("/api/auth/logout")
    def logout(request: Request):
        accounts.logout(request.headers.get("authorization", "").removeprefix("Bearer "))
        return {"logged_out": True}

    @private.post("/api/auth/password")
    def own_password(payload: NewPassword, request: Request):
        perform(accounts.set_password, request.state.user["id"], payload.password, payload.current_password, False)
        return {"changed": True, "login_required": True}

    @private.get("/api/users")
    def users():
        return accounts.users()

    @private.post("/api/users", status_code=201)
    def create_user(payload: AccountInput):
        return perform(accounts.create, payload.username, payload.name, payload.password, payload.role)

    @private.patch("/api/users/{user_id}")
    def update_user(user_id: str, payload: AccountUpdate, request: Request):
        return perform(accounts.update, user_id, request.state.user["id"], payload.role, payload.active)

    @private.post("/api/users/{user_id}/password")
    def reset_password(user_id: str, payload: NewPassword, request: Request):
        if user_id == request.state.user["id"]:
            raise HTTPException(400, "Para tu contraseña usá Cambiar mi contraseña")
        perform(accounts.set_password, user_id, payload.password)
        return {"changed": True, "sessions_revoked": True}

    @private.get("/api/audit")
    def audit_rows(limit: int = Query(100, ge=1, le=500), before: int | None = Query(None, ge=1)):
        with audit.store.lock:
            incident = audit.store.db.execute("SELECT value FROM system_metadata WHERE key='audit_failure'").fetchone()
        return {"integrity": audit.verify(), "items": audit.rows(limit, before),
                "incident": json.loads(incident[0]) if incident else None}

    @private.post("/api/audit/reconcile")
    def reconcile(payload: Reason, request: Request):
        if len(payload.reason.strip()) < 10:
            raise HTTPException(400, "Documentá la revisión con al menos diez caracteres")
        with audit.store.lock:
            incident = audit.store.db.execute("SELECT value FROM system_metadata WHERE key='audit_failure'").fetchone()
            if not incident:
                raise HTTPException(409, "No hay una incidencia de auditoría pendiente")
            if not audit.verify()["valid"]:
                raise HTTPException(409, "La cadena necesita restauración/revisión antes de conciliar")
            audit.append(request.state.user, "CONCILIACION_MANUAL", {
                "incident": json.loads(incident[0]), "review_reason": payload.reason.strip(),
                "caution": "Esta revisión no reconstruye evidencia ausente ni certifica la operación anterior"})
            with audit.store.db:
                audit.store.db.execute("DELETE FROM system_metadata WHERE key='audit_failure'")
            app.state.audit_error = False
        return {"reviewed": True, "missing_evidence_reconstructed": False}

    @private.get("/api/restrictions")
    def restriction_rows(request: Request, q: str = Query("", max_length=150),
                         before: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=500)):
        return restrictions.list(q, request.state.user["role"] == "admin", limit, before)

    @private.post("/api/restrictions", status_code=201)
    def create_restriction(payload: RestrictionInput, request: Request):
        return perform(restrictions.create, payload, request.state.user)

    @private.post("/api/restrictions/{record_id}/release")
    def release_restriction(record_id: str, payload: Reason, request: Request):
        return perform(restrictions.release, record_id, payload.reason, request.state.user)

    app.include_router(private)
