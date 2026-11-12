"""access_app/cameras.py — fuentes privadas autorizadas; no descubre redes ni cámaras."""
import ipaddress
import os
import re
import threading
import time
from urllib.parse import urlparse

import cv2

os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
if hasattr(cv2, "setLogLevel"):
    cv2.setLogLevel(0)


def validate_source(source):
    if source.startswith("usb:"):
        if not re.fullmatch(r'usb:[0-9]{1,2}', source):
            raise ValueError('Usá usb:0, usb:1, etc.')
        try:
            index = int(source[4:])
        except ValueError as exc:
            raise ValueError("Usá usb:0, usb:1, etc.") from exc
        if index < 0 or index > 63:
            raise ValueError("Índice USB inválido")
        return index
    if any(ord(c) < 33 for c in source) or len(source) > 1000:
        raise ValueError('Fuente inválida: no usar espacios ni caracteres de control')
    parsed = urlparse(source)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.hostname or parsed.fragment:
        raise ValueError("Usá USB o RTSP/RTSPS de una IP privada. HTTP y listas de reproducción están deshabilitados")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError('Puerto de cámara inválido') from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('Puerto de cámara inválido')
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise ValueError("Usá la IP privada de la cámara/grabador, no un dominio público") from exc
    local = any(ip in ipaddress.ip_network(n) for n in
              (["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] if ip.version == 4 else ["fc00::/7"]))
    if not local:
        raise ValueError("Este piloto solo admite cámaras de la red privada autorizada")
    return source


class Stream:
    def __init__(self, source):
        self.source, self.frame, self.updated = validate_source(source), None, 0
        self.status = "conectando"
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop_flag.is_set():
            cap = None
            try:
                if isinstance(self.source, int):
                    cap = cv2.VideoCapture(self.source)
                else:
                    cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG,
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
                if not cap.isOpened():
                    raise RuntimeError("sin_conexion")
                self.status = "conectada"
                while not self.stop_flag.is_set():
                    ok, frame = cap.read()
                    if not ok:
                        break
                    with self.lock:
                        self.frame, self.updated = frame, time.monotonic()
                    self.stop_flag.wait(0.03)
            except Exception:
                self.status = "sin_conexion"
            finally:
                if cap is not None:
                    cap.release()
                self.status = "sin_conexion"
                self.stop_flag.wait(3)

    def snapshot(self):
        with self.lock:
            if self.frame is None or time.monotonic() - self.updated > 5:
                raise ValueError("Sin imagen reciente. Revisá conexión, credenciales y formato")
            return self.frame.copy()


class CameraHub:
    def __init__(self):
        self.streams = {}
        self.lock = threading.RLock()

    def connect(self, camera):
        with self.lock:
            if camera["id"] not in self.streams:
                self.streams[camera["id"]] = Stream(camera["source"])

    def frame(self, camera_id):
        with self.lock:
            stream = self.streams.get(camera_id)
            if not stream:
                raise ValueError("Conectá primero la cámara")
        return stream.snapshot()

    def stop(self, camera_id):
        with self.lock:
            stream = self.streams.pop(camera_id, None)
            if stream:
                stream.stop_flag.set()

    def close(self):
        for camera_id in list(self.streams):
            self.stop(camera_id)
