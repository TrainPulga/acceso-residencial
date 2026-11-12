"""Segundo secreto del residente; no equivale a PAD ni garantiza identidad."""
import re
import time

from access_app.auth import password_hash, verify_password


class PinError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class ResidentCredentials:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock

    def configured(self, resident_id):
        with self.store.lock:
            return self.store.db.execute('SELECT 1 FROM resident_credentials WHERE resident_id=?', (resident_id,)).fetchone() is not None

    def set(self, resident_id, pin):
        if not re.fullmatch(r'[0-9]{6,12}', pin) or len(set(pin)) == 1 or pin in {'123456', '654321', '12345678', '123456789', '1234567890'}:
            raise PinError('Usá un PIN de 6–12 dígitos, evitando repeticiones y secuencias obvias')
        with self.store.lock, self.store.db:
            if not self.store.resident(resident_id):
                raise PinError('Residente no encontrado', 404)
            # Se agrega un prefijo constante para reutilizar el KDF sin rebajar su costo.
            self.store.db.execute('INSERT OR REPLACE INTO resident_credentials VALUES (?,?,0,0)',
                                 (resident_id, password_hash('resident-pin:'+pin)))

    def verify(self, resident_id, pin):
        now = self.clock()
        error = None
        with self.store.lock, self.store.db:
            row = self.store.db.execute('SELECT * FROM resident_credentials WHERE resident_id=?', (resident_id,)).fetchone()
            if not row:
                raise PinError('Administración debe configurar el PIN antes de registrar entradas', 409)
            if row['blocked_until'] > now:
                raise PinError('PIN temporalmente bloqueado. Revisión presencial y reintento en cinco minutos', 429)
            if not verify_password('resident-pin:'+pin, row['pin_hash']):
                failures = (row['failures'] if row['blocked_until'] == 0 else 0)+1
                self.store.db.execute('UPDATE resident_credentials SET failures=?,blocked_until=? WHERE resident_id=?',
                                     (failures, now+300 if failures >= 5 else 0, resident_id))
                error = PinError('PIN incorrecto. Volvé a verificar el rostro para reintentar', 403)
            else:
                self.store.db.execute('UPDATE resident_credentials SET failures=0,blocked_until=0 WHERE resident_id=?', (resident_id,))
        if error:
            raise error  # Después de confirmar los contadores, no revertirlos con rollback.
