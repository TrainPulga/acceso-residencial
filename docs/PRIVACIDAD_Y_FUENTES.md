# Privacidad, alcance de cámaras y fuentes

Documento de trabajo, no dictamen jurídico ni consentimiento final. El interés expresado por un encargado no acredita autorización del consorcio o de residentes.

## Acuerdos previos al piloto con personas reales

Identificar entidad y responsable del tratamiento, finalidad exacta, participantes, cámaras y áreas. Acordar consentimiento informado cuando corresponda y una alternativa de acceso. Diferenciar videovigilancia de identificación biométrica: un cartel general de cámaras no debe darse por autorización suficiente para todos los usos.

El piloto se restringe a participantes adultos y puntos de acceso autorizados. Las cámaras de observación solo detectan rostros sin identidad. No se implementan rastreo de recorridos, localización de vecinos en otras cámaras ni identificación de terceros en la calle. Esas finalidades no se incorporan por defecto al consentimiento del acceso.

Definir acceso/supresión de datos, tiempos de conservación y atención de solicitudes. Revisar las obligaciones aplicables a la base y el manual de tratamiento de datos. El responsable debe establecer política, cartelería y controles apropiados antes de operar con residentes, además de la evaluación técnica.

## Medidas del prototipo

- Ejecución local en 127.0.0.1; sin publicación ni API externa de rostros.
- Clave aleatoria solo para la configuración inicial; cuentas locales con roles y sesiones revocables. No hay credencial predeterminada universal.
- Plantillas y campos identificatorios cifrados; no se persisten fotos recibidas para reconocimiento. Los clips manuales exportados son archivos separados.
- Fuentes de cámara cifradas y no devueltas a la interfaz, para no mostrar credenciales.
- Eliminación de identidad/plantilla y pasos asociados al dar de baja.
- Retención provisional de pasos de 7 días, configurable mediante ACCESO_RETENTION_DAYS. No es un plazo legal universal.
- Sin apertura real ni liveness/PAD; no apto para un despliegue de seguridad.

El sistema no protege frente a un administrador del equipo que pueda leer clave y base, malware, copias externas no controladas o fallas del dispositivo. Los roles locales no reemplazan gestión de claves/respaldos, endurecimiento y revisión de seguridad antes del despliegue.

## Referencias consultadas

- AAIP, videovigilancia y manual de tratamiento: https://www.argentina.gob.ar/aaip/datospersonales/responsables/videovigilancia
- Disposición 10/2015, texto actualizado: https://www.argentina.gob.ar/normativa/nacional/disposici%C3%B3n-10-2015-243335/actualizacion
- AAIP, datos personales y biometría: https://www.argentina.gob.ar/node/159936
- Cartelería actualizada: https://www.argentina.gob.ar/node/415298
- YuNet/OpenCV Zoo, modelo y licencia MIT: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- SFace/OpenCV Zoo, modelo y licencia Apache-2.0: https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
- OpenCV, detección y reconocimiento: https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html
- ONVIF Profile T: https://www.onvif.org/profiles/profile-t/

Los modelos se redistribuyen con sus licencias y hashes en models/manifest.json. No se atribuyen los modelos al estudiante ni se trasladan sus métricas de referencia al edificio.

## Ensayos académicos de la versión 0.2

La sección Evaluación académica requiere participación adulta voluntaria y una etiqueta manual. No almacena fotos: conserva cifrados código del participante, sesión, condición, verdad declarada, predicciones, similitud, huella de captura/configuración y latencia. Es información seudonimizada, no anónima. No inferir atributos sensibles.

Los ensayos se conservan en la base activa hasta su eliminación explícita, separadamente de la retención de pasos. Acordar ese plazo y revisar/borrar al cierre del proyecto. Dar de baja a un residente elimina también ensayos donde aparece como etiqueta o predicción. No puede asociarse automáticamente una persona no inscrita a una solicitud de baja: atenderla por su código experimental o borrar el conjunto. Exportaciones JSON y respaldos requieren protección y eliminación propias. El borrado local no acredita la eliminación forense de todas las copias.

## Visitas y servicios 0.4

Se registran nombres, empresa opcional, destino, motivo, responsable declarado, vigencia y pasos manuales sin capturar rostros de visitantes. Perfil/código e historial detallado cifrados; metadatos de tiempo, estado y relaciones no son campos cifrados. Se informa finalidad y tratamiento según el procedimiento que establezca el responsable; la casilla no acredita por sí sola un procedimiento legal válido.

Retención propuesta: 7 días tras finalización/cancelación o vencimiento sin ingreso, configurable. No se borran automáticamente entradas sin salida registrada: requieren revisión y resolución para no ocultar pendientes. La baja de anfitrión se bloquea mientras haya pendientes; luego elimina visitas/historial asociados de la base activa. Respaldos requieren su propia conservación/supresión. No se afirma que los 7 días sean un plazo legal obligatorio ni que el historial sea una auditoría certificada.

## Cuentas, restricciones y clips 0.5

Perfiles de operadores, motivos de restricciones y detalles de auditoría se cifran. Usuarios de inicio de sesión, roles, hashes de contraseñas, tiempos y relaciones permanecen como metadatos visibles. Contraseñas derivadas con sal; no se guardan contraseñas recuperables. La clave inicial no permite eludir las cuentas creadas. Restricciones externas se registran manualmente sin foto/plantilla y sin consulta pública de personas. La asociación a una visita exige selección y verificación explícitas.

Conservación provisional de auditoría y restricciones terminadas: 90 días; referencias externas de visitas conservadas se protegen del borrado. La auditoría no es inmutable frente a quien controla equipo y clave. Clips WebM manuales de webcam, sin audio y hasta 2 minutos, requieren autorización y soporte del entorno. Se descargan fuera de la base y necesitan conservación/supresión propia, igual que JSON/HTML y respaldos. No sirven como PAD ni autorizan seguimiento entre cámaras.

## Seguridad y PIN 0.6

Se agrega un secreto del residente, almacenado como derivación con sal y costo PBKDF2. No se devuelven PIN legibles ni se los añade a auditoría/reportes. Se suprimen junto con la baja del residente. Cada entrada requiere el PIN además del rostro y confirmación humana. Es una mitigación de uso indebido de una coincidencia y no acredita prueba de vida, ausencia de sesgos o capacidad física de acceso.

Sesiones con inactividad, expiración y revocación, permisos privados del SO para base/claves/copias y cabeceras/límites reforzados. El software sigue sin proteger frente al control del mismo usuario del sistema operativo o las claves. Fuentes admitidas: USB y RTSP/RTSPS privado, sin HTTP/loopback. Las cámaras autorizadas y su red deben evaluarse con el responsable; la validación de una URL no es aislamiento de red. Ver SEGURIDAD_0_6.md.

## PAD RGB 0.7

Se procesan recortes faciales transitorios para clasificación de presentación. No se guardan fotos ni recortes; la secuencia conserva temporalmente identificador, tiempos y huellas de imágenes, no una grabación. No se crea un historial de observación nominal entre cámaras. El PAD no infiere atributos sensibles y una alerta no demuestra mala intención.

Los ensayos PAD guardan cifrados código de participante, sesión, fase, tipo de presentación declarado, condición, fuente interna, score, resultado y huella/configuración. Son datos seudonimizados, no anónimos. Se conservan hasta eliminación explícita acordada; la tabla no vincula automáticamente códigos al padrón. Atender supresión por código o borrar el conjunto. Exportaciones JSON se protegen/eliminan aparte. Solo material de adultos voluntarios autorizado, incluidas fotos/videos del propio participante usados para ensayar suplantación. No usar fotos de terceros sin permiso ni publicar estos datos como evidencia pública.

En 0.7 no se pide PIN para el acceso: el apartado 0.6 es histórico. Se conservan hashes heredados por compatibilidad, sin autorizar entradas. Se mantienen cuentas y permisos, y los controles de integridad/retención. PAD no sustituye autorización, alternativa presencial ni evaluación técnica/legal del responsable.
