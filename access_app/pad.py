"""PAD RGB anti-spoof-mn3 + evidencia temporal. No certifica presencia real."""
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import threading
import time

import cv2
import numpy as np

REAL_THRESHOLD = 0.95  # Regla provisional explícita; no precisión medida ni probabilidad de identidad.


class PadEngine:
    def __init__(self, directory):
        directory = Path(directory)
        manifest = json.loads((directory/'manifest.json').read_text())
        model = directory/'anti-spoof-mn3.onnx'
        data = model.read_bytes()
        if manifest['file'] != model.name or hashlib.sha256(data).hexdigest() != manifest['sha256']:
            raise RuntimeError('Modelo PAD incompleto o modificado')
        if hashlib.sha384(data).hexdigest() != manifest['sha384_upstream']:
            raise RuntimeError('El modelo PAD no coincide con la huella publicada')
        self.metadata = {'model': manifest['model'], 'sha256': manifest['sha256'], 'threshold': REAL_THRESHOLD}
        self.net = cv2.dnn.readNetFromONNX(str(model))
        self.lock = threading.RLock()

    @staticmethod
    def prepare(image, boxes):
        if len(boxes) != 1:
            raise ValueError('PAD requiere exactamente un rostro')
        b = boxes[0]
        x, y = math.floor(b['x']), math.floor(b['y'])
        right, bottom = math.ceil(b['x']+b['w']), math.ceil(b['y']+b['h'])
        h, w = image.shape[:2]
        if min(b['w'], b['h']) < 80 or x < 0 or y < 0 or right > w or bottom > h:
            raise ValueError('Rostro pequeño o recortado para PAD')
        rgb = cv2.cvtColor(image[y:bottom, x:right], cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (128, 128), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        # Contrato del ONNX original, no del IR convertido de OpenVINO.
        normalized = (rgb-np.array([151.2405,119.5950,107.8395],np.float32))/np.array([63.0105,56.4570,55.0035],np.float32)
        return np.ascontiguousarray(normalized.transpose(2,0,1)[None])

    def predict(self, image, boxes):
        tensor = self.prepare(image, boxes)
        with self.lock:
            self.net.setInput(tensor)
            output = np.asarray(self.net.forward()).reshape(-1)
        if output.shape != (2,) or not np.isfinite(output).all() or np.any(output < 0) or np.any(output > 1) or abs(float(output.sum())-1) > .001:
            raise ValueError('Salida PAD inválida; no se habilita la verificación')
        return float(output[0])  # Clase 0: bona fide; clase 1: presentación.


class PadSequence:
    required = 3
    minimum_span = 2.0
    minimum_interval = .6
    max_gap = 6.0

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.windows = {}
        self.lock = threading.RLock()

    def clear(self, key):
        with self.lock:
            self.windows.pop(key, None)

    def clear_camera(self, camera_id):
        with self.lock:
            self.windows = {k:v for k,v in self.windows.items() if k[1] != camera_id}

    def observe(self, key, resident_id, fingerprint, real_score):
        now = self.clock()
        with self.lock:
            self.windows = {k:v for k,v in self.windows.items() if now-v['updated'] <= self.max_gap}
            old = self.windows.get(key)
            if old is None or old['resident'] != resident_id:
                old = {'resident':resident_id,'updated':now,'frames':deque(maxlen=self.required),'seen':deque(maxlen=32)}
                self.windows[key] = old
            old['updated'] = now
            frames = old['frames']
            state, message = 'pendiente', 'Mantené un solo rostro visible mientras se comprueba PAD'
            if not math.isfinite(real_score) or not 0 <= real_score <= 1:
                frames.clear()
                state, message = 'error', 'No se pudo comprobar PAD'
            elif real_score < REAL_THRESHOLD:
                frames.clear()
                state = 'posible_presentacion' if real_score <= .20 else 'incierto'
                message = ('Posible foto o pantalla: revisar presencialmente' if state == 'posible_presentacion' else
                           'PAD incierto: mejorar captura y revisar presencialmente')
            elif fingerprint in old['seen']:
                frames.clear()
                state, message = 'captura_repetida', 'Captura repetida: se necesitan imágenes nuevas'
            elif frames and now-frames[-1][0] < self.minimum_interval:
                state, message = 'pendiente', 'Esperando separación temporal entre capturas'
            else:
                frames.append((now, fingerprint))
            old['seen'].append(fingerprint)
            accepted = (state == 'pendiente' and len(frames) == self.required and
                        frames[-1][0]-frames[0][0] >= self.minimum_span)
            if accepted:
                state, message = 'apto', 'Comprobación PAD superada en secuencia · piloto por validar'
            return {'passed':accepted,'state':state,'message':message,'samples':len(frames),
                    'required':self.required,'validated_locally':False}
