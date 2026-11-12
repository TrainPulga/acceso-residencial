"""Límites de transporte antes de parsear JSON; no confía en Content-Length."""
from starlette.responses import JSONResponse

MAX_BODY = 30_000_000


class BoundedBody:
    def __init__(self, app, limit=MAX_BODY):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        try:
            length = int(headers.get(b'content-length', b'0'))
            if length < 0:
                raise ValueError()
        except ValueError:
            return await JSONResponse({'detail': 'Tamaño de solicitud inválido'}, 400)(scope, receive, send)
        if length > self.limit:
            return await JSONResponse({'detail': 'Solicitud demasiado grande'}, 413)(scope, receive, send)
        # Acumula como máximo el límite; la aplicación nunca recibe un cuerpo parcial.
        chunks, total = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            total += len(chunk)
            if total > self.limit:
                return await JSONResponse({'detail': 'Solicitud demasiado grande'}, 413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def secure(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                additions = {
                    b'cache-control': b'no-store', b'x-content-type-options': b'nosniff',
                    b'referrer-policy': b'no-referrer', b'x-frame-options': b'DENY',
                    b'permissions-policy': b'camera=(self), microphone=(), geolocation=()',
                    b'content-security-policy': (b"default-src 'self'; script-src 'self'; style-src 'self'; "
                        b"img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; "
                        b"frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'")}
                headers = [(k, v) for k, v in headers if k.lower() not in additions]
                message['headers'] = headers + list(additions.items())
            await send(message)
        await self.app(scope, receive, secure)
