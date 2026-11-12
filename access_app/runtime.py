"""access_app/runtime.py — servidor local con inicio y cierre controlados."""
import socket
import threading
import time

import uvicorn


class LocalServer:
    def __init__(self, app):
        self.app = app
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.origin = "http://127.0.0.1:"+str(self.sock.getsockname()[1])
        self.server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning", access_log=False,
                                                  proxy_headers=False, limit_concurrency=32, timeout_keep_alive=5))
        self.failure = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        try:
            self.server.run(sockets=[self.sock])
        except BaseException as exc:
            self.failure = exc

    def start(self, timeout=15):
        self.thread.start()
        deadline = time.monotonic()+timeout
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() >= deadline:
                self.stop()
                raise RuntimeError("No se pudo iniciar el servicio local de la aplicación") from self.failure
            time.sleep(.025)
        return self.origin

    def stop(self):
        self.server.should_exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=8)
        self.sock.close()
        if not self.thread.is_alive():
            self.app.state.store.db.close()
