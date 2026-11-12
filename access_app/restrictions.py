"""access_app/restrictions.py — decisiones administrativas revisables, sin rostros externos."""
import uuid
from datetime import datetime, timezone

from access_app.store import utcnow
from access_app.visits import VisitError, iso


class Restrictions:
    def __init__(self, store):
        self.store = store

    def create(self, payload, actor):
        start, end, now = iso(payload.valid_from), iso(payload.valid_until), utcnow()
        if end <= start or end <= now:
            raise VisitError("La restricción necesita un período futuro/vigente con fin posterior al inicio")
        if not payload.authorized_decision or not payload.reason.strip():
            raise VisitError("Confirmá la decisión autorizada e indicá su motivo documentado")
        with self.store.lock, self.store.db:
            if payload.resident_id:
                person = self.store.resident(payload.resident_id)
                if not person:
                    raise VisitError("Residente no encontrado", 404)
                name, reference = person["name"], person["building"]+" · "+person["unit"]
            else:
                name, reference = payload.name.strip(), payload.reference.strip()
                if len(name) < 2 or len(reference) < 2 or not payload.identity_verified:
                    raise VisitError("Para un registro externo verificá identidad e indicá nombre y referencia interna")
            profile = {"name": name, "reference": reference, "reason": payload.reason.strip(),
                       "authorized_decision": True, "created_by_name": actor["name"],
                       "type": "residente" if payload.resident_id else "externo_manual"}
            record_id = uuid.uuid4().hex
            self.store.db.execute("INSERT INTO restrictions(id,resident_id,profile,valid_from,valid_until,created_at,created_by) "
                "VALUES (?,?,?,?,?,?,?)", (record_id, payload.resident_id, self.store.seal(profile), start, end, now, actor["id"]))
            return self.get(record_id, True)

    def get(self, record_id, admin=False):
        with self.store.lock:
            row = self.store.db.execute("SELECT * FROM restrictions WHERE id=?", (record_id,)).fetchone()
            if not row:
                raise VisitError("Restricción no encontrada", 404)
            profile = self.store.open(row["profile"])
            if not admin:
                profile = {k: profile[k] for k in ("name", "reference", "type")}
            now = utcnow()
            state = "levantada" if row["released_at"] else "programada" if now < row["valid_from"] else \
                    "vencida" if now >= row["valid_until"] else "vigente"
            return {**{k: row[k] for k in row.keys() if k != "profile"}, **profile, "state": state}

    def list(self, query="", admin=False, limit=100, before=None):
        with self.store.lock:
            found = []
            for row in self.store.db.execute("SELECT id FROM restrictions WHERE (? IS NULL OR rowid<?) "
                "ORDER BY rowid DESC", (before, before)):
                item = self.get(row["id"], admin)
                if query.casefold() not in (item["name"]+" "+item["reference"]).casefold():
                    continue
                item["cursor"] = self.store.db.execute("SELECT rowid FROM restrictions WHERE id=?", (item["id"],)).fetchone()[0]
                found.append(item)
                if len(found) >= limit+1:
                    break
            return {"items": found[:limit], "next_before": found[limit-1]["cursor"] if len(found)>limit else None}

    def active_for_resident(self, resident_id):
        now = utcnow()
        with self.store.lock:
            return self.store.db.execute("SELECT 1 FROM restrictions WHERE resident_id=? AND released_at IS NULL "
                "AND valid_from<=? AND valid_until>? LIMIT 1", (resident_id, now, now)).fetchone() is not None

    def active_external(self, record_id):
        item = self.get(record_id)
        if item["type"] != "externo_manual":
            raise VisitError("Seleccioná un registro externo verificado")
        return item["state"] == "vigente"

    def release(self, record_id, reason, actor):
        if len(reason.strip()) < 3:
            raise VisitError("Indicá el motivo de levantar la restricción")
        with self.store.lock, self.store.db:
            item = self.get(record_id, True)
            if item["released_at"]:
                raise VisitError("La restricción ya fue levantada", 409)
            row = self.store.db.execute("SELECT profile FROM restrictions WHERE id=?", (record_id,)).fetchone()
            profile = self.store.open(row["profile"])
            profile.update({"release_reason": reason.strip(), "released_by_name": actor["name"]})
            self.store.db.execute("UPDATE restrictions SET profile=?,released_at=?,released_by=? WHERE id=?",
                                  (self.store.seal(profile), utcnow(), actor["id"], record_id))
            return self.get(record_id, True)

    def prune(self, cutoff):
        with self.store.lock, self.store.db:
            referenced = {self.store.open(v["profile"]).get("external_record_id") for v in
                          self.store.db.execute("SELECT profile FROM visits")}
            old = self.store.db.execute("SELECT id FROM restrictions WHERE valid_until<? AND "
                                        "(released_at IS NULL OR released_at<?)", (cutoff, cutoff)).fetchall()
            self.store.db.executemany("DELETE FROM restrictions WHERE id=?",
                                      [(r["id"],) for r in old if r["id"] not in referenced])
