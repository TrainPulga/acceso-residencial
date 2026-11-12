"""access_app/auth.py — cuentas locales, hashes lentos y sesiones revocables."""
import hashlib
import hmac
import re
import secrets
import time
import uuid

from access_app.store import utcnow

ITERATIONS = 600_000
IDLE_SECONDS = 15*60


class AuthError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def password_hash(password):
    if not 12 <= len(password) <= 256:
        raise AuthError("La contraseña debe tener entre 12 y 256 caracteres")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        method, iterations, salt, digest = stored.split("$")
        if method != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 2_000_000:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, TypeError):
        return False


SECURITY_ROUTES = {
    ("GET", "/api/status"), ("GET", "/api/residents"), ("GET", "/api/events"),
    ("GET", "/api/cameras"), ("GET", "/api/visits"), ("GET", "/api/visits/{visit_id}"),
    ("GET", "/api/restrictions"), ("GET", "/api/auth/me"),
    ("POST", "/api/auth/password"), ("POST", "/api/auth/logout"),
    ("POST", "/api/analyze"), ("POST", "/api/passages"), ("POST", "/api/visits"),
    ('POST','/api/access/reset'),
    ("POST", "/api/visits/{visit_id}/entry"), ("POST", "/api/visits/{visit_id}/exit"),
    ("POST", "/api/cameras/{camera_id}/connect"), ("POST", "/api/cameras/{camera_id}/analyze"),
    ("POST", "/api/cameras/{camera_id}/disconnect"),
}


def permitted(user, method, route):
    if user["force_change"] and route not in {"/api/auth/me", "/api/auth/password", "/api/auth/logout"}:
        return False
    return user["role"] == "admin" or (method, route) in SECURITY_ROUTES


class Accounts:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock
        self.dummy = password_hash(secrets.token_urlsafe(24))

    def setup_required(self):
        with self.store.lock:
            return self.store.db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None

    def public(self, row):
        return {"id": row["id"], "username": row["username"], **self.store.open(row["profile"]),
                "role": row["role"], "active": bool(row["active"]), "force_change": bool(row["force_change"])}

    def _new_user(self, username, name, password, role, force_change=False):
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,40}", username) or not name.strip():
            raise AuthError("Usá un usuario de 3–40 letras/números y completá el nombre")
        if role not in ("admin", "seguridad"):
            raise AuthError("Rol no admitido")
        if self.store.db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise AuthError("Ese nombre de usuario ya existe", 409)
        user_id = uuid.uuid4().hex
        self.store.db.execute("INSERT INTO users(id,username,profile,password_hash,role,force_change,created_at) "
            "VALUES (?,?,?,?,?,?,?)", (user_id, username, self.store.seal({"name": name.strip()}),
                                       password_hash(password), role, int(force_change), utcnow()))
        return self.public(self.store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def _session(self, user):
        token = secrets.token_urlsafe(32)
        expiry = self.clock()+8*3600
        self.store.db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash IN "
            "(SELECT token_hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT -1 OFFSET 2)",
            (user['id'], user['id']))
        self.store.db.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                              (hashlib.sha256(token.encode()).hexdigest(), user["id"], expiry, self.clock()))
        return {"token": token, "user": user, "expires_at": expiry}

    def setup(self, key, username, name, password):
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            if not self.setup_required():
                raise AuthError("La configuración inicial ya se completó", 409)
            if not hmac.compare_digest(key.encode(), self.store.admin_token.encode()):
                raise AuthError("Clave de configuración incorrecta", 401)
            return self._session(self._new_user(username, name, password, "admin"))

    def create(self, username, name, password, role):
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            return self._new_user(username, name, password, role, True)

    def login(self, username, password, source):
        # Por cuenta: cambiar la IP no reinicia el contador. La API aplica además un límite por IP.
        key = hashlib.sha256(("account:"+username.strip().lower()).encode()).hexdigest()
        now = self.clock()
        with self.store.lock:
            blocked = self.store.db.execute("SELECT * FROM login_attempts WHERE key=?", (key,)).fetchone()
            if blocked and blocked["blocked_until"] > now:
                raise AuthError("Demasiados intentos. Esperá cinco minutos", 429)
            row = self.store.db.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
            valid = verify_password(password, row["password_hash"] if row else self.dummy)
            if not row or not valid or not row["active"]:
                with self.store.db:
                    failures = (blocked["failures"] if blocked and blocked["blocked_until"] == 0 else 0)+1
                    self.store.db.execute("INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)",
                        (key, failures, now+300 if failures >= 5 else 0))
                raise AuthError("Usuario o contraseña incorrectos", 401)
            with self.store.db:
                self.store.db.execute("DELETE FROM login_attempts WHERE key=?", (key,))
                self.store.db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
                return self._session(self.public(row))

    def resolve(self, token):
        if not token or len(token) > 200:
            raise AuthError("Ingresá con tu usuario y contraseña", 401)
        with self.store.lock, self.store.db:
            row = self.store.db.execute("SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id "
                "WHERE s.token_hash=? AND s.expires_at>? AND s.last_seen_at>? AND u.active=1",
                (hashlib.sha256(token.encode()).hexdigest(), self.clock(), self.clock()-IDLE_SECONDS)).fetchone()
            if not row:
                raise AuthError("Sesión vencida o revocada. Volvé a ingresar", 401)
            self.store.db.execute('UPDATE sessions SET last_seen_at=? WHERE token_hash=?',
                (self.clock(), hashlib.sha256(token.encode()).hexdigest()))
            return self.public(row)

    def logout(self, token):
        with self.store.lock, self.store.db:
            self.store.db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def users(self):
        with self.store.lock:
            return [self.public(r) for r in self.store.db.execute("SELECT * FROM users ORDER BY username")]

    def update(self, user_id, actor_id, role, active):
        if user_id == actor_id:
            raise AuthError("No cambies tu propio rol/estado desde esta opción")
        with self.store.lock, self.store.db:
            self.store.db.execute("BEGIN IMMEDIATE")
            old = self.store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not old:
                raise AuthError("Usuario no encontrado", 404)
            admins = self.store.db.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]
            if old["role"] == "admin" and old["active"] and (role != "admin" or not active) and admins <= 1:
                raise AuthError("Debe quedar al menos un administrador activo", 409)
            self.store.db.execute("UPDATE users SET role=?,active=? WHERE id=?", (role, int(active), user_id))
            self.store.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            return self.public(self.store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def set_password(self, user_id, password, current=None, force_change=True):
        with self.store.lock, self.store.db:
            row = self.store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                raise AuthError("Usuario no encontrado", 404)
            if current is not None and not verify_password(current, row["password_hash"]):
                raise AuthError("Contraseña actual incorrecta", 401)
            self.store.db.execute("UPDATE users SET password_hash=?,force_change=? WHERE id=?",
                                  (password_hash(password), int(force_change), user_id))
            self.store.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
