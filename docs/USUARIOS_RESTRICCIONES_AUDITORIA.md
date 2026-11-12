> Actualización 0.7: el PIN de residentes ya no es obligatorio ni se muestra en el acceso. Se reemplaza por reconocimiento más PAD temporal. El apartado «PIN desde 0.6» se conserva como historial y no describe el flujo actual. Ver PAD_0_7.md.

# Operación local · 0.7

## Primera cuenta y operadores

Cerrar la aplicación anterior y abrir ABRIR_ESCRITORIO.bat desde la carpeta nueva, con la misma cuenta de Windows. Se conserva la carpeta de datos y el motor facial. La actualización agrega esquema 6 con respaldo anterior. No volver a abrir una versión antigua sobre la base actualizada.

Si aún no hay cuentas, copiar la clave inicial del cuadro nativo y crear usuario administrador, nombre y contraseña de al menos 12 caracteres. La clave inicial deja de autorizar APIs cuando se crean cuentas. No hay usuario/contraseña predeterminado. En Usuarios, Administración crea cuentas de Seguridad o de otros administradores; entregar la contraseña temporal por un canal propio. Se exige cambiarla al primer ingreso, y se revocan las sesiones al cambiar/restablecer contraseña o desactivar una cuenta. Sesión máxima: 8 horas, vencimiento tras 15 minutos sin solicitudes; hasta 3 sesiones por cuenta. El panel cierra sesión tras 15 minutos sin interacción humana y el servicio revoca sesiones al reiniciar. No compartir cuentas.

| Operación | Administración | Seguridad |
|---|---|---|
| Consultar residentes, movimientos y restricciones sin motivos privados | Sí | Sí |
| Reconocer en acceso y confirmar pasos observados | Sí | Sí |
| Crear visitas y registrar entrada/salida | Sí | Sí |
| Cancelar visitas | Sí | No |
| Alta/baja de residentes y gestión de fuentes | Sí | No |
| Crear/levantar restricciones | Sí | No |
| Cuentas, evaluación académica, auditoría y respaldos por menú | Sí | No |
| Elegir webcam y conectar fuentes ya configuradas | Sí | Sí |

Las acciones se validan también en servidor, no solo ocultando botones. Un usuario con control de los archivos/clave del sistema operativo está fuera de esa frontera: proteger equipo y cuentas Windows. No se admiten cambios de rol/estado propios; se evita desactivar al último administrador activo.

## Restricciones revisables

No es un buscador público de personas. Administración selecciona un residente registrado o crea un registro manual externo sin rostro, con nombre/referencia, motivo, vigencia y decisión autorizada declarada. Para externos se exige verificar presencialmente identidad; no se consultan internet/antecedentes ni se compara una foto con otras cámaras. Seguridad no recibe el motivo privado.

Una restricción vigente de residente impide confirmar su ingreso aun si apareció después del reconocimiento; la salida sigue permitida. Un permiso de visita solo queda vinculado a un registro externo si el operador selecciona expresamente ese registro y confirma la identidad. No se asocian personas automáticamente por tener nombres parecidos. Antes de registrar entrada hay que revisar restricciones. Corregir un registro incorrecto o finalizar la medida mediante Levantar, dejando motivo. No tratar a un rostro desconocido como amenaza.

## Auditoría e incidencias

Auditoría muestra usuario, fecha y acción; detalles cifrados en la base. Se encadenan firmas HMAC y un marcador local permite detectar cambios o truncación respecto del estado conocido. No es evidencia inmutable ni certificada. El personal de Seguridad no accede a la auditoría administrativa. Los análisis repetidos de cámara no generan un historial nominal de observación.

Si una operación se guardó pero su auditoría falló, se avisa y se bloquean nuevas modificaciones. Administración debe revisar el registro afectado y el estado de almacenamiento. En Auditoría aparece la incidencia y un formulario de conciliación: describir lo comprobado. Esto deja una constancia nueva y habilita operar; no reconstruye la evidencia que faltó. Ante cadena dañada, la conciliación no reemplaza restauración/revisión. Proteger respaldos y reloj del equipo; una falla total de almacenamiento puede impedir guardar también el aviso.

## Cámara y clips

En el acceso se elige la webcam disponible o una fuente configurada compatible. Las vistas complementarias solo detectan rostros sin dar nombres; cada fuente debe activarse. La carga crece con el número de cámaras; no hay latencia/capacidad garantizada. No se garantiza compatibilidad universal.

El clip manual solo usa la webcam local activa, sin micrófono, máximo 120 segundos. Requiere confirmar autorización/finalidad y soporte de MediaRecorder en el entorno. Al detenerlo se ofrece guardar WebM; no se envía al servidor ni se adjunta automáticamente a movimientos. Cerrar sesión descarta el clip no exportado. Grabación IP/DVR continua no implementada. Cualquier archivo exportado debe protegerse y eliminarse por separado; las reglas de retención de la base no lo alcanzan. Grabar un clip no constituye detección de vida ni prueba de identidad.

## Recuperación de contraseña sin sesión

Si otro administrador conserva acceso, puede restablecerla desde Usuarios. Si no, cerrar completamente escritorio y modo navegador. El script recuperar_administrador.py exige privilegios de administrador del sistema operativo, una cuenta administradora de la aplicación ya existente, confirmación explícita y genera respaldo antes de modificar. No crea una cuenta sustituta ni muestra contraseñas existentes. Ejecutarlo con el Python del entorno de esta carpeta, desde una terminal elevada; usar --data-dir con la ruta original si la elevación emplea otra cuenta Windows. Se solicita contraseña nueva sin mostrarla; luego se revocan todas las sesiones y se exige cambio al ingresar. El evento de recuperación queda registrado. Este procedimiento requiere acceso autorizado a los datos y su clave; no recupera una clave de cifrado perdida.

## Prueba de aceptación en Windows

Con datos de prueba autorizados: crear Administración y Seguridad; verificar cambio inicial; comprobar que Seguridad no puede gestionar usuarios; seleccionar webcam; realizar reconocimiento y confirmar un paso; probar visitante con anfitrión o mantenimiento común; aplicar/revisar una restricción y comprobar entrada denegada/salida permitida; consultar auditoría como Administración; respaldar; cerrar/reabrir y comprobar persistencia. Probar clip y borrarlo si no se requiere. Después registrar cualquier falla con su mensaje, sin compartir datos personales ni credenciales.

Este recorrido aún requiere ejecución en el equipo del estudiante. Los ensayos de precisión biométrica deben seguir PLAN_VALIDACION.md, con voluntarios y sesiones independientes.

## PIN de residentes desde 0.6

Administración abre Residentes → Configurar PIN (o Cambiar PIN), verifica presencialmente identidad/autorización y acuerda el secreto con la persona. Elegir 6–12 dígitos evitando secuencias obvias. No se comparte por el chat ni se publica. Después de guardarlo no se puede consultar: solo reemplazarlo verificando nuevamente la identidad. Seguridad no puede configurar o cambiar PIN.

En Control de acceso, una coincidencia permite preparar la confirmación. Para Entrada el residente debe ingresar su PIN privado y el operador confirmar el cruce observado. No basta con el rostro, no hay PIN por defecto y la API también exige el secreto. Para Salida no se exige PIN. Tras 5 fallas se bloquea 5 minutos; no reiniciar el contador mediante capturas nuevas. La prueba de vida continúa sin validar. Si alguien olvidó el PIN o hay duda de identidad, seguir un procedimiento presencial autorizado ajeno a una apertura automática: el programa no abre puertas.

Una restricción administrativa sigue impidiendo registrar entrada incluso con PIN correcto. Los visitantes conservan su procedimiento manual de identificación/autorización sin biometría y sin PIN de residente. Este cambio no los convierte en propietarios ni en autorizaciones digitales del anfitrión.
