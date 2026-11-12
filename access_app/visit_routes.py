"""access_app/visit_routes.py — contratos de visitas; todas las acciones requieren clave local."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from access_app.visits import VisitCancellation, VisitCreate, VisitError, VisitMovement


def register_visit_routes(app, visits, admin, camera):
    router = APIRouter(prefix="/api/visits", dependencies=[Depends(admin)])

    def perform(callback, *args):
        try:
            return callback(*args)
        except VisitError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @router.get("")
    def list_visits(limit: int = Query(100, ge=1, le=500), before: int | None = Query(None, ge=1),
                    q: str = Query("", max_length=100), inside: bool = False):
        return perform(visits.list, limit, before, q, inside)

    @router.post("", status_code=201)
    def create_visit(payload: VisitCreate, request: Request):
        return perform(visits.create, payload, request.state.user)

    @router.get("/{visit_id}")
    def detail(visit_id: int):
        return perform(visits.detail, visit_id)

    @router.post("/{visit_id}/entry")
    def entry(visit_id: int, payload: VisitMovement, request: Request):
        return perform(visits.move, visit_id, "entrada", payload, camera(payload.camera_id), request.state.user)

    @router.post("/{visit_id}/exit")
    def exit_visit(visit_id: int, payload: VisitMovement, request: Request):
        return perform(visits.move, visit_id, "salida", payload, camera(payload.camera_id), request.state.user)

    @router.post("/{visit_id}/cancel")
    def cancel(visit_id: int, payload: VisitCancellation, request: Request):
        return perform(visits.cancel, visit_id, payload.reason, request.state.user)

    app.include_router(router)
