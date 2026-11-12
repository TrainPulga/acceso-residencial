# Correcciones y mitigaciones de seguridad · 0.6 · 17/10/2026

Revisión del código propio y regresiones automatizadas. No es un pentest independiente, certificación de seguridad ni medición de precisión biométrica. El ámbito sigue siendo una instalación local supervisada sin apertura de cerraduras.

## Qué se corrigió

| Hallazgo en 0.5 | Cambio en 0.6 | Cómo se comprueba |
|---|---|---|
| El límite inicial confiaba en Content-Length; un cuerpo sin longitud fiable llegaba al parser | Middleware ASGI cuenta chunks reales y rechaza más de 30 MB antes de entregar el cuerpo a la aplicación | Prueba directa ASGI con chunks, sin longitud y con longitud declarada falsa: 413 y aplicación no invocada |
| Sesiones solo tenían vencimiento absoluto de 8 horas | Inactividad de solicitudes 15 minutos, límite 3 sesiones por cuenta y revocación al iniciar el servicio; máximo absoluto conservado | Reloj controlado, renovación/expiración, límite de sesiones y reinicio; no se espera 8 horas reales |
| Token de coincidencia ligado al operador permitía reutilización en otra sesión del mismo operador | Se liga al hash de la sesión concreta, además de acceso, TTL y uso único | Dos logins del mismo operador: el segundo no consume el token del primero |
| El bloqueo de login dependía de la combinación IP+usuario; el servidor confiaba en cabeceras de proxy | Contador por cuenta y límite IP separado; proxy_headers=False en los dos lanzadores | Fuentes distintas no eluden bloqueo; configuración de servidor revisada |
| Las cámaras admitían loopback y HTTP/HTTPS con superficie de servicios/listas anidadas innecesaria | Solo USB o RTSP/RTSPS de IP RFC1918/ULA; rechazo de loopback, dominios, controles, puertos inválidos y fragmentos | Validación y prueba de una fuente HTTP antigua: error controlado sin abrir stream |
| La comparación de una clave inicial Unicode podía producir error de servidor | Comparación constante entre bytes UTF-8 | Clave incorrecta Unicode devuelve 401 |
| Errores del validador podían reflejar valores enviados, incluidos secretos/capturas | Respuesta 422 devuelve ubicación/mensaje/tipo sin input ni body | PIN inválido identificable no aparece en respuesta |
| Rechazos tempranos no recibían todos los encabezados protectores | Capa externa agrega no-store, nosniff, anti-frame, permisos y CSP con object-src/base-uri restringidos | Se verifican encabezados en 403, 413 y 422 además de HTTP real |
| chmod no configuraba una DACL privada de Windows; base y copias dependían de permisos heredados | DACL de cuenta Windows actual y SYSTEM sin herencia; permisos 700/600 en POSIX; protección de carpetas antes de escribir secretos y rechazo de enlaces | POSIX y enlaces comprobados; llamadas Windows implementadas pero no ejecutadas en este entorno |

La validación de URL no es un firewall ni garantiza que una cámara o decoder comprometidos no intenten otras conexiones. No se afirma aislamiento de red, protección frente a malware local ni bloqueo de todos los ataques de denegación de servicio. Los lanzadores limitan concurrencia a 32, sin convertirlo en una garantía de disponibilidad.

## Qué se mitigó: uso de fotografías o videos

El reconocedor continúa sin PAD validado. **No se corrigió el detector para distinguir una cara viva de una foto** y no se presenta un gesto, parpadeo o movimiento improvisado como prueba fiable.

Se cambia la regla de confirmación de entradas: coincidencia reciente de un solo rostro apto + PIN privado del residente + cruce observado por el operador. La API no admite omitir el PIN. Las salidas siguen asistidas sin PIN y nunca se bloquea un egreso físico. El programa no acciona puertas. Una foto que logre coincidencia no basta por sí sola para confirmar una entrada bajo esta regla; una foto y PIN robados siguen siendo un riesgo.

Administración configura/reemplaza el PIN tras declarar verificación presencial de identidad/autorización. Seguridad no puede cambiarlo. PIN de 6–12 dígitos, rechazo de repeticiones/secuencias comunes; sal aleatoria y PBKDF2-HMAC-SHA256 con 600.000 iteraciones. El prefijo constante del PIN solo adapta la política del KDF; no agrega entropía. No hay PIN por defecto, recuperación en texto claro ni copia en eventos/auditoría/reportes. Cinco fallas bloquean cinco minutos con contador persistente por residente, conservado entre capturas y reinicios. La baja elimina el hash.

El PIN reduce ataques en línea; un secreto numérico sigue teniendo poca entropía ante robo de la base y ataques fuera de línea. No equivale a una llave criptográfica física, un factor resistente a phishing ni una solución certificada. El operador también puede cometer errores al verificar/autorizar visitantes o restablecer secretos. La aplicación confía en su procedimiento y en la cuenta local autorizada.

## Archivo, contraseñas y dependencias

Los permisos nuevos reducen acceso desde otras cuentas ordinarias. El cifrado sigue usando una clave en el mismo equipo: quien controle esa cuenta, SYSTEM, software malicioso ejecutado allí o un administrador capaz de tomar propiedad puede acceder/modificar datos. No se implementaron DPAPI, TPM, almacenamiento de claves separado, cifrado completo de disco ni protección contra extracción de memoria. Los respaldos incluyen claves y necesitan la misma protección; los exportados WebM/HTML/JSON se guardan donde el operador elige y su protección queda fuera de la retención de la base.

El perfil Qt es efímero y el panel borra PIN y datos al salir; el panel además cierra sesión después de 15 minutos sin interacción de teclado/puntero aunque la cámara continúe. Este cierre visual complementa el vencimiento de servidor; no demuestra presencia humana ni impide mantener activa una sesión robada con solicitudes. Un navegador comprometido o XSS que lograra ejecutarse podría actuar con la sesión; se mantiene CSP y no se usan secretos dentro de HTML generado con innerHTML.

Se consultaron versiones de Python con pip-audit y el lock de herramientas Node con npm audit. Los JSON adjuntos registran los resultados concretos. constraints-seguridad.txt fija las versiones revisadas; preparar.py incluye ese archivo al decidir reinstalación. La consulta no analiza el código propio, binarios nativos Qt/Chromium/FFmpeg, dependencias adicionales de otra plataforma ni vulnerabilidades desconocidas. No se afirma que un resultado sin avisos sea prueba de seguridad o aprobación de esta versión. No se incluye firma digital ni hashes de cada wheel descargado.

## Compatibilidad y aceptación pendiente

La migración de esquema 4 a 5 crea respaldo, conserva cuentas y plantillas, revoca sesiones y agrega credenciales vacías. No inventa PIN para residentes previos. El motor YuNet/SFace no cambia. Los registros anteriores no se reescriben como si hubieran verificado PIN. Los movimientos nuevos que verificaron PIN lo indican en su evidencia, sin guardar el secreto. Las cámaras HTTP anteriores se conservan pero deben reconfigurarse mediante una fuente admitida. No hay downgrade automático.

Antes de uso con el edificio: comprobar arranque/migración y permisos en Windows, realizar el recorrido de roles/PIN/salidas/visitas con datos de prueba autorizados, verificar cámaras reales y reloj, ejecutar PLAN_VALIDACION y evaluar ataques de presentación con un procedimiento acordado. No conectar una cerradura ni sustituir la alternativa presencial basándose únicamente en estas pruebas de software. La auditoría externa, configuración de red/hardware, PAD y errores biométricos siguen pendientes.

## Referencias técnicas de la revisión

- OWASP, Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP, Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Microsoft, SetNamedSecurityInfoW: https://learn.microsoft.com/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow
- Microsoft, SECURITY_INFORMATION y protección de DACL: https://learn.microsoft.com/en-us/windows/win32/secauthz/security-information

Son referencias de implementación; su mención no acredita conformidad integral con sus recomendaciones ni una certificación.
