# Acceso Residencial · Escritorio local 0.7

> **Copia de GitHub:** los lanzadores descargan los tres modelos ONNX en el primer inicio y comprueban su SHA-256. Para preparar los modelos por separado, ejecutá `python descargar_modelos.py`. Los manifiestos y las licencias están en `models/`. El ZIP original de escritorio sí incluye los pesos.

Proyecto Integrador de Ciencia de Datos e IA. Verificación asistida de residentes, control PAD RGB de fotos/pantallas, visitas y registro manual de pasos. Separado de PulguiFly. **No abre cerraduras ni se presenta como un producto de seguridad certificado.**

## Actualizar y abrir en Windows

1. Cerrar completamente la aplicación y la consola anteriores. Extraer TODO el ZIP nuevo en una carpeta nueva.
2. Con Python **3.12** instalado, abrir **ABRIR_ESCRITORIO.bat**. Se admite 3.11–3.13; la primera preparación descarga dependencias y requiere internet.
3. Si ya se usó escritorio 0.3–0.6 con la misma cuenta de Windows, los datos se reutilizan: no importar ni registrar otra vez a las personas. Si se viene de 0.1/0.2, importar su carpeta data completa. Si no hay registros anteriores, elegir No.
4. Si aún no hay cuentas, usar la clave del cuadro nativo para crear el primer administrador con usuario y contraseña de al menos 12 caracteres. Después se ingresa con esa cuenta; la clave inicial no sustituye contraseñas. La actualización y cada reinicio cierran las sesiones previas.
5. Seleccionar una cámara, iniciarla y aceptar el permiso cuando corresponda.

Los datos quedan en **%LOCALAPPDATA%\AccesoResidencial\data**, fuera del programa, o en ACCESO_DATA_DIR si se configuró. Se migra a esquema 6 con respaldo previo, preservando cuentas, residentes, plantillas y visitas. El motor de identidad YuNet/SFace no cambia; PAD tiene pesos y manifiesto separados. **No se pide PIN para entradas ni salidas en 0.7.** Los hashes PIN históricos quedan conservados como datos heredados; no habilitan ni bloquean una verificación.

`ABRIR_ACCESO.bat` conserva el modo navegador, usando la misma ubicación. Cerrar una modalidad antes de abrir la otra. Este ZIP contiene código y modelos; todavía no es un .exe compilado ni un instalador. Hay una receta de compilación Windows y un workflow manual, sin ejecución/validación remota atribuida.

## Verificar un residente y registrar un paso

Elegir la webcam del equipo desde su selector o una fuente de acceso configurada. Presentar un solo rostro, completo y suficientemente iluminado. El programa exige coincidencia facial y **tres capturas diferentes que superen PAD**, separadas temporalmente, con al menos dos segundos entre primera y última. A la cadencia normal se completa en varias capturas; el tiempo efectivo depende del equipo y fuente, sin SLA prometido.

| Estado del panel | Significado y acción |
|---|---|
| Comprobando PAD | Todavía no hay evidencia temporal suficiente; registro deshabilitado |
| Posible foto o pantalla | El modelo indica posible presentación; no habilita registro; revisar presencialmente, sin acusar a nadie |
| Incierto / error / no disponible | No alcanza para verificar; revisar captura, fuente o instalación; no se omite PAD |
| Rostro y PAD superados · piloto | Se habilita preparar un paso observado; no certifica presencia ni identidad infalibles |
| Entrada restringida | La restricción administrativa impide registrar entrada, aunque reconocimiento/PAD hayan superado sus controles |

Cuando corresponda, el operador confirma el cruce observado y elige Entrada o Salida. Reconocer a alguien mirando una cámara no demuestra un cruce. La confirmación exige un token reciente, de un uso, ligado a acceso y sesión, emitido después de PAD; no basta declarar desde el cliente que PAD fue aprobado. Un fotograma posterior que falla invalida el token anterior. Detener una fuente reinicia la comprobación y revoca la evidencia asociada. Las fuentes del servidor no aceptan una imagen subida como si proviniera de esa cámara.

La aplicación nunca bloquea físicamente una salida. Si no se completa la verificación facial/PAD, el personal debe aplicar el procedimiento presencial acordado; no se inventa una identidad ni se evita PAD para crear un registro biométrico. La interfaz no pide PIN al residente.

## Qué protección incorpora y qué falta medir

PAD ejecuta **anti-spoof-mn3**, un clasificador RGB público, con pesos auténticos verificados, licencia MIT y preprocesamiento documentado. Su resultado se combina con consistencia de identidad, calidad, novedad de captura y tiempo. No se usa un parpadeo improvisado ni se confunde un PIN con prueba de vida. El umbral de score 0,95 es una **decisión provisional**, no una precisión del 95 % ni un requisito medido del cliente.

**Está integrado, pero su eficacia local frente a fotos impresas, fotos/videos en pantallas y personas reales todavía no está medida.** Puede aceptar ataques o rechazar personas reales; no garantiza 0 % de suplantaciones. No autentica hardware de cámara, no evita por sí solo cámaras virtuales/inyección en un equipo comprometido y no certifica resistencia a máscaras, deepfakes o ataques desconocidos. El control RGB requiere validación con cada entorno. El guardia conserva la revisión presencial.

Ver **docs/PAD_0_7.md** para arquitectura, límites y protocolo. El panel de Evaluación incorpora captura etiquetada de ensayos PAD, denominadores y exportación JSON. Sin ensayos no se inventan tasas.

## Usuarios, visitas y restricciones

Administración gestiona cuentas, padrón, fuentes, restricciones, respaldos y evaluación. Seguridad puede operar accesos y visitas, consultar los registros permitidos y conectar las fuentes configuradas. El servidor exige los permisos; las contraseñas temporales requieren cambio inicial. Sesiones máximas de ocho horas, quince minutos sin solicitudes y cierre adicional del panel sin interacción humana; hasta tres por cuenta y revocación al reinicio.

Visitas y mantenimiento tienen responsable/anfitrión o destino de administración, vigencia, verificación presencial y entrada/salida manuales. No se registran rostros de visitantes. Una referencia no acredita identidad ni abre puertas. La cancelación no oculta una entrada sin salida. Restricciones revisables necesitan decisión autorizada, motivo y vigencia. Los registros externos son manuales sin biometría, y solo se asocian a visitas mediante verificación explícita. Un desconocido no equivale a intruso.

Auditoría cifra detalles, atribuye operaciones a la cuenta y verifica una cadena HMAC local. Ante fallo de registro, se bloquean modificaciones hasta revisión explícita; la conciliación no reconstruye evidencia faltante. No es un registro inmutable frente a control del SO y claves. Ver **docs/USUARIOS_RESTRICCIONES_AUDITORIA.md** y **docs/VISITAS_Y_SERVICIOS.md**.

## Cámaras elegibles

- Webcam local seleccionada mediante el navegador/Qt.
- USB del servidor (`usb:0`, `usb:1`, etc.).
- RTSP/RTSPS de IP privada autorizada, con ruta y credenciales del fabricante.

Ejemplo de formato, no cámara real: `rtsp://USUARIO:CLAVE@192.168.1.100:554/RUTA_DEL_FABRICANTE`.

No hay compatibilidad universal. Analógicas requieren DVR/capturadora; algunas marcas necesitan SDK no integrado. No hay descubrimiento ONVIF. HTTP/HTTPS, dominios y loopback no se admiten como fuentes en este piloto. Se conservan las fuentes HTTP antiguas, pero no se conectan: reconfigurarlas como RTSP compatible. Validar la URL no equivale a aislar la red.

Las cámaras complementarias solo detectan rostros sin nombres ni seguimiento de recorridos, con vistas activadas a pedido. No existe búsqueda nominal entre cámaras. El clip manual exportable es de webcam local, sin audio y hasta dos minutos; no hay grabación continua IP/DVR. Las imágenes de reconocimiento/PAD no se persisten; los clips solo se guardan cuando se solicita la exportación.

## Datos, actualizaciones y responsabilidad

Perfiles, plantillas, fuentes, detalles de visitas/auditoría y ensayos se cifran con Fernet. Base y claves tienen permisos privados de SO; se rechazan enlaces de secretos. La implementación DACL necesita prueba real en Windows. Proteger cuenta Windows, disco y respaldos: quien controle el equipo y la clave puede acceder/modificar datos. No publicar data, claves, respaldos, clips o resultados personales en GitHub.

Pasos: retención provisional siete días. Visitas: siete días tras finalización/cancelación o vencimiento sin uso; no se borran entradas pendientes. Auditoría/restricciones finalizadas: noventa días provisionales, protegiendo referencias todavía conservadas. Altas hasta baja; ensayos de identidad/PAD hasta eliminación explícita acordada. No son plazos legales obligatorios. Los ensayos PAD usan códigos sin vínculo automático al padrón: atender solicitudes por código o borrar el conjunto. Exportaciones/copias tienen gestión propia.

Antes de participantes reales, el responsable debe acordar finalidad, autorizaciones, alternativa presencial, conservación y atención de derechos. Las casillas registran declaraciones, no acreditan por sí solas un consentimiento válido. Solo adultos voluntarios en este piloto. Ver **docs/PRIVACIDAD_Y_FUENTES.md** y **docs/ESCRITORIO_Y_ACTUALIZACIONES.md**.

## Evaluación y documentación académica

El módulo previo compara decisiones de identificación con una línea base sin rechazo; continúa midiendo reconocimiento, no seguridad PAD. El módulo nuevo mide PAD por captura con etiqueta humana (persona/foto impresa/foto en pantalla/video), fuente, condición, sesión/fase y score. Son experimentos distintos; no sumar sus tasas ni presentar el clasificador por captura como la decisión temporal completa de acceso. Registrar también fallos y capturas no aptas. Las instrucciones están en PLAN_VALIDACION.md y PAD_0_7.md.

SRS_SSOT.md y MATRIZ_CUMPLIMIENTO.md enlazan requisitos, implementación y evidencia. Faltan aprobación del recorte por el docente, documentación del interesado, experimento autorizado, informe con resultados reales, repositorio propio y defensa. La plantilla Datamaq se adapta y no se declara conformidad literal total ni aprobación académica.

## Verificación técnica y organización

Instalar `requirements-dev.txt` y ejecutar `python -m pytest -q`. Las pruebas verifican flujos con datos sintéticos y carga/inferencia de modelos reales; **no son ensayos con personas ni demuestran eficacia antisuplantación**. Ver VERIFICACION_TECNICA.json. Node/jsdom son herramientas de desarrollo opcionales: `npm ci --ignore-scripts` y `npm test`; no se necesitan para abrir el escritorio.

- `access_app/`: API, lógica, PAD, fuentes, persistencia, panel y evaluación.
- `models/`: identidad y `pad/` con pesos, hashes y licencias.
- `tests/`: lógica, seguridad, modelos, cámara y DOM simulado.
- `docs/`: SSOT, operación, protocolo y estado real.

No hay cupo artificial de residentes, pero capacidad/latencia dependen del equipo y no se demostraron ilimitadas. La consulta de dependencias y sus restricciones de versiones se conserva desde 0.6; no se añadieron paquetes para PAD. La cadena de suministro/binarios nativos y la operación Windows/cámaras del edificio todavía requieren validación.
