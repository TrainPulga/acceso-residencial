"""access_app/domain.py — comparación abierta y confirmaciones de paso del piloto."""
import math
import secrets
import threading
import time
from dataclasses import dataclass


def unit(vector):
    values = tuple(float(v) for v in vector)
    norm = math.sqrt(sum(v * v for v in values))
    if not values or not all(math.isfinite(v) for v in values) or norm < 1e-9:
        raise ValueError("Vector facial inválido")
    return tuple(v / norm for v in values)


@dataclass(frozen=True)
class Match:
    resident_id: str | None
    score: float | None
    reason: str


def identify(vector, gallery, threshold=0.50, margin=0.08):
    """Similitudes coseno; nunca son porcentajes de probabilidad."""
    vector = unit(vector)
    ranked = []
    for resident_id, template in gallery:
        template = unit(template)
        if len(vector) != len(template):
            raise ValueError("Dimensiones de modelo incompatibles")
        ranked.append((sum(a * b for a, b in zip(vector, template)), resident_id))
    ranked.sort(reverse=True)
    if not ranked:
        return Match(None, None, "sin_residentes")
    score, resident_id = ranked[0]
    if score < threshold:
        return Match(None, score, "sin_coincidencia")
    if len(ranked) > 1 and score - ranked[1][0] < margin:
        return Match(None, score, "coincidencia_ambigua")
    return Match(resident_id, score, "coincidencia_experimental")


class PassTokens:
    """Cada coincidencia autoriza una sola confirmación manual, durante 20 s."""
    def __init__(self, ttl=20, clock=time.monotonic):
        self.ttl, self.clock = ttl, clock
        self.items = {}
        self.lock = threading.Lock()

    def issue(self, resident_id, camera_id, operator_id=None, pad_passed=False):
        with self.lock:
            now = self.clock()
            self.items = {k: v for k, v in self.items.items() if v[2] > now}
            token = secrets.token_urlsafe(24)
            self.items[token] = (resident_id, camera_id, now + self.ttl, operator_id, pad_passed)
            return token

    def consume(self, token, camera_id, operator_id=None, require_pad=False):
        with self.lock:
            value = self.items.pop(token, None)
            if not value or value[2] <= self.clock() or value[1] != camera_id or value[3] != operator_id:
                raise ValueError("Coincidencia vencida o ya utilizada. Volvé a verificar.")
            if require_pad and not value[4]:
                raise ValueError('La coincidencia no tiene comprobación PAD válida')
            return value[0]

    def invalidate(self, camera_id, operator_id):
        with self.lock:
            self.items = {k:v for k,v in self.items.items() if (v[1],v[3]) != (camera_id,operator_id)}

    def invalidate_camera(self, camera_id):
        with self.lock:
            self.items = {k:v for k,v in self.items.items() if v[1] != camera_id}
