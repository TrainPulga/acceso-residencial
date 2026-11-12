"""access_app/audit.py — registro local cifrado y encadenado; no auditoría externa certificada."""
import hashlib
import hmac
import json

from access_app.store import utcnow


class Audit:
    def __init__(self, store):
        self.store = store
        self.key = hashlib.sha256((store.directory/"local.key").read_bytes()+b"audit-v1").digest()

    def _signature(self, occurred_at, actor_id, action, details, previous):
        data = json.dumps([occurred_at, actor_id, action, details.hex(), previous], separators=(",", ":")).encode()
        return hmac.new(self.key, data, hashlib.sha256).hexdigest()

    def append(self, user, action, details=None):
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            row = self.store.db.execute("SELECT signature FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
            anchor = self.store.db.execute("SELECT value FROM system_metadata WHERE key='audit_anchor'").fetchone()
            previous = row[0] if row else anchor[0] if anchor else "0"*64
            now = utcnow()
            payload = self.store.seal({"operator": {k: user[k] for k in ("id", "username", "name", "role")},
                                       **(details or {})})
            signature = self._signature(now, user["id"], action, payload, previous)
            cursor = self.store.db.execute("INSERT INTO audit_log(occurred_at,actor_id,action,details,previous_hash,signature) "
                "VALUES (?,?,?,?,?,?)", (now, user["id"], action, payload, previous, signature))
            self.store.db.execute("INSERT OR REPLACE INTO system_metadata VALUES ('audit_tip',?)", (signature,))
            return cursor.lastrowid

    def verify(self):
        with self.store.lock:
            anchor = self.store.db.execute("SELECT value FROM system_metadata WHERE key='audit_anchor'").fetchone()
            previous = anchor[0] if anchor else "0"*64
            count = 0
            for row in self.store.db.execute("SELECT * FROM audit_log ORDER BY id"):
                expected = self._signature(row["occurred_at"], row["actor_id"], row["action"], row["details"], previous)
                if row["previous_hash"] != previous or not hmac.compare_digest(row["signature"], expected):
                    return {"valid": False, "checked": count, "error": "Cadena de auditoría modificada o incompleta"}
                count += 1
                previous = row["signature"]
            tip = self.store.db.execute("SELECT value FROM system_metadata WHERE key='audit_tip'").fetchone()
            valid = tip is None or hmac.compare_digest(tip[0], previous)
            return {"valid": valid, "checked": count,
                    "error": None if valid else "Falta el final de la auditoría respecto al marcador local"}

    def rows(self, limit=100, before=None):
        with self.store.lock:
            return [{"id": r["id"], "occurred_at": r["occurred_at"], "action": r["action"],
                     **self.store.open(r["details"])} for r in self.store.db.execute(
                "SELECT * FROM audit_log WHERE (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?", (before, before, limit))]

    def prune(self, cutoff):
        with self.store.lock, self.store.db:
            last = None
            for row in self.store.db.execute("SELECT id,signature,occurred_at FROM audit_log ORDER BY id"):
                if row["occurred_at"] >= cutoff:
                    break
                last = row
            if last:
                self.store.db.execute("DELETE FROM audit_log WHERE id<=?", (last["id"],))
                self.store.db.execute("INSERT OR REPLACE INTO system_metadata VALUES ('audit_anchor',?)", (last["signature"],))
