# Visitas y servicios · 0.5 · 17/10/2026

Módulo operativo asistido. No usa biometría de visitantes, no abre cerraduras y no identifica personas por presentar un código. Todas las operaciones requieren una cuenta activa. Administración y Seguridad pueden crear permisos y registrar pasos; solo Administración los cancela. Cada operación se atribuye a su usuario autenticado.

## Crear una autorización

En **Visitas y servicios**, completar persona, tipo (visita/mantenimiento/servicio), empresa opcional, motivo, responsable que autorizó y período. Elegir quién recibe:

- Un residente ya registrado: el destino se obtiene de su ficha, sin inventar datos.
- Administración / áreas comunes: indicar edificio y sector; permite autorizar mantenimiento sin registrar un residente ficticio.

El operador confirma que verificó la autorización con el responsable y que se informó el tratamiento de datos al visitante. Es una declaración, no una autorización digital emitida desde una cuenta del residente. No se comprueba automáticamente la facultad legal de quien figura como autorizante.

Los campos de fecha usan la zona horaria del equipo. El servidor exige fechas con zona y las normaliza a UTC. La visualización usa hora argentina. Dos horas es solo el valor inicial editable, no una regla del cliente ni un plazo legal. No se crean permisos que ya terminaron ni con fin anterior al inicio.

Se genera una referencia V-… aleatoria. El código permite buscar el registro dentro del panel autenticado: no es una contraseña de apertura, un QR ni prueba de identidad. No hay endpoint público para consultarlo.

## Registrar entrada y salida

Abrir el detalle, elegir un punto de acceso autorizado, verificar presencialmente a la persona y marcar el cruce observado. Registrar Entrada o Salida según corresponda.

Cada autorización admite una sola entrada y una salida. Una nueva visita o jornada necesita otro permiso. El software rechaza entrada antes del inicio, después del vencimiento, cancelada, repetida o después de finalizada. La salida exige una entrada pendiente, pero puede registrarse aunque el permiso haya vencido o se haya cancelado mientras la persona tenía una entrada sin salida.

Las horas son de confirmación del operador. Una referencia o una cara detectada no demuestran un cruce. Para entrada se exige revisar las restricciones. Si el permiso se asoció explícitamente a un registro externo tras verificar identidad, una restricción vigente impide confirmarla. No hay coincidencia automática por nombre o rostro ni bloqueo de salidas. El punto de acceso identifica dónde se declaró el paso; en esta versión no adjunta una fotografía ni una grabación.

## Estados

| Estado | Significado |
|---|---|
| Programada | El período todavía no comenzó |
| Autorizada | Puede evaluarse el ingreso dentro del período; requiere verificación presencial |
| Vencida | Terminó el período sin entrada registrada |
| Sin salida registrada | Se confirmó entrada y aún no se confirmó salida; no es ubicación verificada en tiempo real |
| Finalizada | Se registraron entrada y salida |
| Cancelada | Se revocó antes del ingreso |

Si se cancela estando en estado Sin salida registrada, conserva ese estado y muestra cancelación. No se inventa una salida ni se oculta el registro. Una autorización expirada tampoco confirma que la persona siga físicamente dentro: seguridad debe comprobarlo.

## Consulta e historial

Buscador por nombre, empresa, anfitrión, edificio/unidad o código. La búsqueda es local a registros autorizados; no consulta internet ni bases externas. Paginación, filtro de visitas sin salida y detalle con creación, entrada, salida y cancelación. Nombre, empresa, motivo, código, anfitrión y motivos de cancelación se cifran en la base. Tiempos, estados y claves de relación son metadatos visibles en el archivo SQLite.

Las operaciones nuevas de 0.5 indican el usuario autenticado. Los registros anteriores conservan su atribución histórica; no se inventa retrospectivamente un operador. El nombre de quien autorizó es una declaración del operador. No es una auditoría inmutable ni un registro certificado.

## Errores y conservación

- Reintentar una creación con el mismo request_id y mismos datos devuelve el mismo permiso. Cambiar los datos manteniendo esa clave se rechaza. La interfaz mantiene la clave mientras no se cambie el formulario.
- Entradas simultáneas o clics repetidos no generan dos movimientos. Las transiciones se ejecutan dentro de una transacción SQLite y un bloqueo local.
- Dar de baja a un residente con visitas sin salida registrada se rechaza hasta revisar esos registros y confirmar los egresos observados. La baja elimina sus permisos/historiales asociados cuando ya no hay pendientes; no elimina trabajos de administración sin ese anfitrión.
- Retención propuesta: **7 días** después de finalización/cancelación; permisos sin usar se eliminan 7 días después del vencimiento. Variable ACCESO_VISIT_RETENTION_DAYS, de 1 a 365. No se borran automáticamente registros con entrada sin salida, aunque venza la autorización. Revisarlos periódicamente y acordar su resolución/conservación.
- El borrado se ejecuta al iniciar, cada hora y al consultar el estado general. No elimina copias exportadas ni respaldos; gestionarlos aparte.

Los plazos son decisiones provisionales del piloto; deben acordarse con el responsable. El módulo no sustituye un procedimiento de privacidad aprobado.

## Actualizar desde 0.3/0.4

Cerrar la aplicación anterior, extraer 0.5 en una carpeta nueva y ejecutar ABRIR_ESCRITORIO.bat con la misma cuenta de Windows. Se reutiliza automáticamente %LOCALAPPDATA%\AccesoResidencial\data. No hay que volver a importar ni registrar residentes si esa es la ubicación que se usó.

La base pasa de esquema 2/3 a 4 con respaldo previo y migración transaccional. No cambia el motor YuNet/SFace ni las plantillas guardadas. No abrir 0.3 sobre una base ya actualizada: para una recuperación usar el respaldo de esquema compatible, conservando aparte operaciones posteriores. Datos y programa siguen separados.

## Validación

Pruebas técnicas con datos sintéticos: creación/flujo completo, anfitrión o administración, fechas y zona, permisos futuros/vencidos, identidad/cruce, cámara de observación rechazada, cancelación dentro/fuera, duplicados/idempotencia, concurrencia, baja protegida, cifrado, búsqueda/paginación, conservación, backup/restauración y migración fallida con rollback.

No hay ensayos reales con visitas del edificio ni resultados de seguridad o precisión biométrica incluidos. La nueva pantalla debe probarse en Windows; la apertura y recorrido básico de la versión 0.3 fueron confirmados por el estudiante, sin que eso constituya evaluación formal.
