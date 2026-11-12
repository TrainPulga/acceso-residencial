# Escritorio y compatibilidad · 0.7 · 17/10/2026

Primera etapa del plan acordado. Código de aplicación de escritorio para Windows con ventana Qt propia, reutilizando la interfaz y los modelos del prototipo. El navegador externo no se abre en esta modalidad. No es todavía un instalador ni un .exe Windows compilado/verificado.

## Primera apertura

1. Cerrar la versión anterior, incluida su consola. Extraer todo el ZIP nuevo en una carpeta nueva.
2. Abrir **ABRIR_ESCRITORIO.bat**. Usa Python 3.11–3.13 (recomendado 3.12, ya instalado en el equipo del estudiante). La primera preparación descarga Qt/WebEngine y las dependencias; necesita internet y puede tardar.
3. Al abrir la ventana, elegir si se importan registros anteriores. Seleccionar la carpeta **data** de la versión anterior, su carpeta de programa si contiene data, o un respaldo generado por esta versión. Si no hay registros, elegir No. Cancelar no crea un padrón sustituto.
4. Solo si no existen cuentas, el cuadro nativo permite copiar la clave inicial. Usarla para crear el primer administrador con usuario y contraseña. Luego se ingresa con esa cuenta. Aplicación → Mostrar clave local solo revela la clave antes de crear cuentas; no permite sustituir una contraseña olvidada. La clave copiada se limpia del portapapeles a los 30 segundos si no fue reemplazada.
5. Iniciar la cámara y aceptar el permiso nativo. Solo se permite cámara de video del origen local; micrófono, pantalla y otros orígenes se rechazan.
6. Cerrar la ventana para detener el servicio local. No es necesario mantener una consola abierta durante el uso. El lanzador puede volver a abrirse: reutiliza el entorno mientras las dependencias no cambien.

La ventana comparte la interfaz existente; esta entrega no es un rediseño visual completo. En 0.5 se incorporan cuentas Administración/Seguridad con permisos comprobados por el servidor. La instalación sigue siendo local y no sincroniza equipos.

## Dónde quedan los datos

Windows: **%LOCALAPPDATA%\AccesoResidencial\data**. La opción Aplicación → Abrir carpeta de datos muestra la ubicación efectiva. Si se configura ACCESO_DATA_DIR se usa esa ruta explícita. Las futuras versiones de este mismo programa deben reutilizar esa ubicación.

Programa y datos son independientes. Mover/reemplazar la carpeta del programa no mueve ni borra la carpeta de datos. Cada cuenta de Windows tiene su propia ubicación: cambiar de usuario, PC o ACCESO_DATA_DIR requiere una importación autorizada. No hay sincronización de equipos.

No borrar ni publicar esa carpeta: contiene base cifrada, clave y credencial administrativa. La protección del sistema operativo, disco y respaldos sigue siendo necesaria. Las reglas de conservación siguen vigentes: pasos 7 días de manera provisional; altas hasta baja; ensayos hasta su borrado acordado. «Persistencia» no significa conservación indefinida.

## Importación 0.1/0.2

Se comprueban estructura, integridad y correspondencia de clave/datos. La copia se hace con la API de respaldo de SQLite y se publica al destino solo después de verificarla. El origen permanece intacto. Un destino con contenido nunca se sobrescribe ni se mezcla automáticamente con otro padrón.

Se conservan residentes, claves, plantillas, cámaras, eventos y ensayos presentes. Se agrega versión de esquema y metadatos. Antes de modificar una base anterior se crea un respaldo en **%LOCALAPPDATA%\AccesoResidencial\backups**, o junto a la ubicación elegida si se usa otra ruta.

Las versiones 0.1/0.2 no guardaban firma del motor. Su importación asume que se usaron los modelos y procesamiento originales de esos paquetes, que aquí se mantienen. La ausencia de firma histórica no permite verificar retrospectivamente un motor modificado por terceros. No se afirma compatibilidad con bases de otros sistemas.

## Respaldo y recuperación

Aplicación → Crear respaldo requiere una sesión de Administración y permite elegir una carpeta privada. Se genera una carpeta nueva con snapshot de la base, local.key, admin.token y un manifiesto de hashes. Debe conservarse el conjunto completo: la base sin la clave no se puede recuperar. Los respaldos contienen datos personales recuperables y necesitan la misma protección y política de eliminación.

Para recuperar sin sobrescribir datos:

1. Cerrar todas las instancias.
2. Apartar la carpeta actual data renombrándola, por ejemplo a data_antes_de_recuperar. Conservarla hasta verificar el resultado; no mezclar sus claves con otras.
3. Abrir el escritorio. En la primera apertura seleccionar el respaldo íntegro.
4. Verificar padrón, cámaras y movimientos antes de continuar.

Al importar un respaldo se conservan cuentas y contraseñas, pero se revocan sus sesiones: volver a iniciar sesión. La recuperación conserva el origen. No bajar de versión sobre una base actual: si se necesita volver a una versión anterior, usar su respaldo compatible y conservar aparte los cambios posteriores. Restaurar un respaldo anterior no recupera operaciones realizadas después de su fecha. No se ofrece downgrade automático ni fusión de bases.

## Versiones y compatibilidad

- APP_VERSION identifica el programa. PRAGMA user_version identifica el esquema SQLite.
- Migraciones en transacción: fallos de esquema revierten sus cambios; el respaldo anterior se conserva.
- Base futura: se rechaza y no se baja su versión ni se reemplaza el padrón.
- Firma facial: combina hashes de los modelos y versión de la representación/alineado. Cambios incompatibles se rechazan antes de operar con las plantillas anteriores; no se borran ni convierten silenciosamente.
- Se conservan YuNet/SFace y su procesamiento de 0.2. Agregar pantallas, visitas o permisos no exige cambiar ese motor.
- Cada actualización futura necesita pruebas y, cuando cambie el esquema, su migración propia. Esta infraestructura no promete compatibilidad automática con cualquier modificación.

## Verificaciones y límites de esta entrega

Ver VERIFICACION_TECNICA.json para los resultados ejecutados. Se probaron migración desde esquema antiguo simulado con datos sintéticos, reapertura, respaldo de base abierta, recuperación, rechazo de clave incorrecta, destino ocupado, respaldo alterado, esquema futuro y firma facial distinta. Las pruebas sintéticas no son mediciones de biometría.

Se importó el módulo Qt y se verificaron sus APIs y políticas de permisos; el servicio HTTP real se probó con inicio/cierre. No se ejecutó un renderer Qt ni se validaron ventana/webcam en Windows desde este entorno. La política de cámara requiere además permisos del sistema y compatibilidad del dispositivo. No se deshabilita el sandbox del motor web.

El bloqueo de instancia protege aperturas del escritorio de esta versión. Las versiones anteriores no conocen ese bloqueo: deben cerrarse antes de importar/usar la instalación. Tampoco hay coordinación multiusuario distribuida.

## Ejecutable independiente: siguiente validación

**CREAR_EJECUTABLE_WINDOWS.bat** contiene una receta de compilación con PyInstaller para ejecutarla en Windows. Genera una carpeta dist/AccesoResidencial con .exe y dependencias; compartir únicamente el .exe no alcanza. El objetivo es que esa distribución funcione sin Python externo. Debe comprobarse en un Windows limpio, incluyendo Qt/WebEngine, permisos de cámara, respaldos, licencias y recursos antes de considerarla entregable.

La receta no fue ejecutada en Windows aquí. No se incluye un binario compilado ni un instalador firmado en este ZIP. No atribuirles una prueba aprobada.

## Pendientes del plan

Visitas/autorizaciones temporales están implementadas desde 0.4. Restricciones revisables, usuarios/permisos y auditoría individual se incorporan en 0.5 con esquema 4, conservando el motor facial. Ver VISITAS_Y_SERVICIOS.md y USUARIOS_RESTRICCIONES_AUDITORIA.md. La migración desde esquemas anteriores crea un respaldo y no vuelve a registrar rostros. No hay apertura física, PAD validado ni búsqueda nominal de personas entre cámaras. La sección de evaluación académica anterior se conserva.

Fuentes técnicas: documentación oficial Qt for Python QWebEnginePage, QWebEnginePermission y Qt/PyInstaller, y metadatos oficiales PyPI de PySide6 6.12.0 y PyInstaller 6.22.3, consultados el 17/10/2026.

## Actualización de seguridad 0.6

Esquema 4 → 5 con respaldo. Se conservan cuentas, residentes, plantillas, visitas y cámaras; se revocan sesiones. Se agrega actividad de sesiones y credenciales PIN derivadas con sal. Los residentes anteriores no reciben un PIN inventado: Administración lo configura con ellos antes de registrar entradas. Las salidas siguen disponibles.

Los archivos de datos y cada respaldo nuevo reciben permisos privados. En Windows se usan DACL de la cuenta Windows actual y SYSTEM; no es un secreto separado del equipo ni reemplaza proteger su cuenta/disco. Si el destino no admite esos permisos, no se completa el respaldo. El código Windows requiere prueba nativa allí; aquí se comprobó la política POSIX y se conservaron las pruebas de interfaz Qt sin renderer. No usar una cuenta Windows compartida para datos personales reales.

HTTP/HTTPS y direcciones loopback dejan de admitirse como cámaras. La configuración previa se conserva para no perderla, pero su conexión se rechaza con un error controlado. Configurar la alternativa RTSP/RTSPS privada del fabricante con Administración. No hay conversión universal de URLs.

Ver SEGURIDAD_0_6.md y el procedimiento de PIN en README. No bajar de versión sobre la base actualizada; no existe downgrade automático.

## PAD 0.7

Misma cuenta Windows y carpeta de datos: actualización a esquema 6 con respaldo, sin volver a registrar rostros ni cambiar la firma de identidad. Se agrega tabla cifrada de ensayos PAD y se revocan sesiones. No se pide PIN. Los hashes previos se conservan como datos heredados sin controlar accesos. El ONNX PAD tiene manifiesto separado y se incluye con licencia MIT. No se agregan dependencias. La detección complementaria sigue sin nombres.

Al elegir fuente de acceso, el software exige una secuencia que supere reconocimiento/PAD antes de emitir confirmación. PAD ausente/error/incertidumbre no permite confirmar por rostro. Validación de cámaras/Windows y eficacia con fotos/pantallas/personas pendientes. No volver a una versión anterior sobre la base 6. Ver PAD_0_7.md.
