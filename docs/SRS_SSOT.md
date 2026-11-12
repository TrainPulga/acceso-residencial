# SRS / SSOT — Acceso Residencial

Versión 0.7 · 17/10/2026 · Especificación de trabajo, pendiente de validación docente y del interesado. Fuente de verdad del alcance actual. Adaptación de Datamaq; no declaración de conformidad con todas sus reglas técnicas.

## 1. Contexto, problema y actores

**Hecho comunicado por el estudiante:** un encargado de un grupo de edificios manifestó interés en identificación facial y registro de ingresos/egresos. No están documentados entidad administradora, localidad, procedimiento actual, cantidad de accesos, errores, costos, permisos o aceptación de residentes. No se atribuye el caso a Albano Cozzuol ni a una empresa inventada.

**Problema a investigar:** cómo asistir la verificación de residentes participantes en un acceso y registrar pasos efectivamente observados, evaluando errores y condiciones de captura. El interés del encargado es evidencia de contacto, no prueba de una falla del sistema actual, demanda comercial ni autorización del consorcio.

**Pregunta principal:** ¿qué desempeño ofrece un verificador facial local con rechazo de coincidencias débiles frente a elegir siempre el residente más parecido, usando sesiones independientes y personas no inscritas?

**Objetivo general:** diseñar, construir y evaluar un prototipo local de verificación facial en accesos autorizados y registro asistido de pasos, con evidencia reproducible y límites documentados.

**Objetivos específicos:** caracterizar el procedimiento existente; obtener capturas voluntarias y etiquetas; procesar/controlar calidad de imágenes; extraer representaciones preentrenadas; comparar con una línea base; medir identificación, rechazo, errores y latencia; integrar API, interfaz y persistencia; documentar resultados y privacidad.

**Hipótesis H1, todavía no demostrada:** incorporar umbral y margen reduce aceptaciones de no inscritos frente a la misma búsqueda sin rechazo, a costa posible de rechazos de inscritos. Medir ambos efectos en las mismas capturas; no presentar únicamente la mejora conveniente.

**Hipótesis H2, exploratoria:** iluminación y orientación están asociadas a cambios de rechazo y tiempo. El diseño observacional no demuestra causalidad. Sujeto, cámara, distancia y sesión pueden confundir la comparación.

**Actores propuestos:** adulto voluntario; operador; administración/consorcio como decisor potencial. El software tiene cuentas locales de Administración y Seguridad con permisos separados; no administra cuentas de residentes ni sincronización entre equipos. El estudiante debe poder explicar sus decisiones, aporte, datos, pruebas y limitaciones aun con asistencia de IA.

## 2. Propuesta de valor y Canvas

Beneficio por validar: verificación asistida y trazabilidad en un equipo local, con métricas que ayuden a decidir si la biometría tiene utilidad en ese acceso. No se promete reducir delitos, reemplazar personal, ahorrar dinero ni ser una invención inédita.

| Bloque | Propuesta / estado |
|---|---|
| Segmento | Administraciones y consorcios; interesado concreto todavía sin identificación formal |
| Valor | Piloto medible de verificación y registro asistido, con tratamiento local |
| Canales | Demostración privada y prueba acordada; sin web pública de biometría |
| Relación | Puesta en marcha, capacitación y soporte; hipótesis comercial |
| Ingresos | Posible implementación y mantenimiento; precio y voluntad de pago no medidos |
| Recursos | PC, cámara compatible, modelos, código, autorizaciones y voluntarios |
| Actividades | Caracterización, evaluación, soporte, actualización y gestión de datos |
| Socios | Administración e instalador de seguridad para una etapa física posterior; no hay convenios firmados |
| Costos | Equipo, integración, horas de soporte, energía, licencias y eventual revisión profesional; sin importes inventados |

La rentabilidad requiere medir costo total actual y propuesto en el mismo período. Ahorro neto = costo actual evitable − costo operativo adicional. Recupero solo puede calcularse si ese ahorro es positivo y se conoce la inversión. El MVP local no requiere dominio ni hosting pago.

## 2.1. Ampliación acordada el 17/10/2026

Aplicación de escritorio, conservación de datos entre versiones, visitas y mantenimiento, restricciones con revisión administrativa, selección de cámaras y cuentas con permisos. Ventana/persistencia/respaldos desde 0.3; visitas desde 0.4; cuentas, restricciones, auditoría individual y selector de webcam en 0.5. Son implementaciones técnicas que requieren aceptación y prueba operativa. La identificación nominal entre cámaras no se incorpora al recorte inicial.

Requisitos nuevos: **FR-13** abrir/cerrar en una ventana de escritorio; **FR-14** importar una instalación anterior sin sobrescribirla ni mezclar claves; **FR-15** crear/restaurar respaldos íntegros a un destino vacío; **NFR-09** preservar datos y esquema mediante migración transaccional y respaldo previo; **NFR-10** detectar una base futura o firma facial incompatible, conservando los datos. Evidencia y límites en ESCRITORIO_Y_ACTUALIZACIONES.md y tests/test_updates.py.

## 3. Alcance y exclusiones

Incluye altas/bajas voluntarias, procesamiento de imágenes, YuNet/SFace preentrenados, comparación 1:N con abstención, detección múltiple sin nombres, verificación individual en acceso, registro manual de pasos observados, fuentes privadas compatibles y experimentos etiquetados con exportación.

Una escena con varios rostros puede mostrar varios recuadros. Para verificar identidad en el acceso se exige un solo rostro; no se genera permiso de paso ante una escena ambigua. Esto debe explicarse en la demostración, no presentarse como reconocimiento múltiple.

Fuera del MVP: cerraduras, apertura automática, prueba de vida/PAD validada, inferencia automática de entrada/salida, seguimiento nominal entre cámaras, búsqueda de transeúntes, menores, conexión universal a cualquier cámara, servicio público en internet o garantía de capacidad ilimitada. Son diferencias respecto al deseo inicial del interesado y requieren acordar el recorte; no se declaran resueltas.

## 4. Datos y método

Dos fuentes distintas: modelos oficiales redistribuidos con licencia/hash; capturas nuevas de adultos voluntarios autorizados. Los modelos públicos no constituyen datos del edificio. El piloto guarda plantillas cifradas y descarta las imágenes de operación; los ensayos guardan resultados/etiquetas seudonimizados y cifrados, sin fotos. El evaluador offline opcional usa imágenes locales autorizadas y necesita una conservación separada.

Flujo: problema → autorizaciones → captura → control de calidad → descriptor → galería → candidato/rechazo → revisión humana → paso confirmado o ensayo experimental → métricas → conclusiones. No se entrena una red desde cero; el aporte de Ciencia de Datos está en protocolo, procesamiento, comparación abierta, control de errores, validación y análisis.

Cada ensayo contiene código de participante, sesión, etapa, condición, etiqueta manual, predicción, línea base, similitud, latencia de procesamiento, huella de captura y de configuración/padrón/modelos. Los códigos no vuelven anónimos los datos. El código de participante debe ser estable, sin nombres, y los desconocidos también necesitan códigos distintos.

La línea base comparte detector, calidad y descriptor: cambia solamente la decisión de rechazar. No demuestra superioridad frente a otra arquitectura, operadores, llaves o tarjetas. No se fuerza OCR, habla, IoT, forecasting o MTBF/MTTR al no existir necesidad en este recorte.

## 5. Requisitos funcionales y criterios de aceptación

| ID | Requisito verificable | Criterio |
|---|---|---|
| FR-01 | Alta/baja de adulto voluntario | Requiere autorización declarada y 3–5 capturas distintas; baja elimina plantilla, pasos y ensayos asociados de la base activa |
| FR-02 | Detectar rostros visibles | API devuelve recuadros y cantidad, incluyendo cero o varios; comprobación con escenas reales pendiente |
| FR-03 | Identificar o abstenerse | Un solo rostro apto; umbral y margen; desconocido/ambigüedad no generan token |
| FR-04 | Registrar un paso observado | Token vigente, de un uso, del mismo acceso y sesión; la confirmación exige reconocimiento y secuencia PAD; no se exige PIN; confirmación humana y dirección obligatorias; sin escritura automática por mera coincidencia |
| FR-05 | Explicitar límites físicos | Nunca acciona cerradura; estado de PAD/apertura falso |
| FR-06 | Historial | Fecha/hora UTC, visualización argentina, paginación y eliminación asociada |
| FR-07 | Ingesta de fuentes compatibles | USB o RTSP/RTSPS de IP privada autorizado; sin HTTP/loopback; error de conexión explícito, sin descubrimiento de dispositivos |
| FR-08 | Observación sin identidad | Aunque se pida reconocer, una cámara de observación solo devuelve detección |
| FR-09 | Ensayos etiquetados | Captura explícita con autorización, etiqueta y sesión; no usa la predicción como verdad ni crea movimientos |
| FR-10 | Evidencia exportable | JSON con conteos, denominadores, línea base, condiciones y configuración; cero observaciones produce tasa nula, no 0 % |
| FR-11 | Coherencia experimental | Rechaza captura idéntica, cambio de padrón/configuración/fase dentro de una sesión y reutilización de código con otra etiqueta |
| FR-12 | Supresión experimental | Borrado explícito de ensayos y depuración de los asociados a un residente dado de baja; exportaciones externas se gestionan aparte |

## 6. Requisitos no funcionales

| ID | Requisito y verificación |
|---|---|
| NFR-01 | Sin cupo artificial: no hay condición de máximo; medir desempeño al tamaño real antes de comprometer capacidad |
| NFR-02 | Operación local: servidor ligado a loopback, sin API de rostros externa; instalación inicial requiere internet |
| NFR-03 | Acceso restringido: cuentas, sesiones, permisos por rol, comprobación de origen/host y límite de solicitudes; no equivale a seguridad auditada |
| NFR-04 | Datos personales cifrados: Fernet para perfiles, plantillas, fuentes y ensayos; proteger también clave, disco y copias |
| NFR-05 | Calidad medible: mediana/p95 de procesamiento por sesión; latencia integral y objetivo operativo pendientes de medir/acordar |
| NFR-06 | Reproducibilidad: dependencias directas fijadas, modelos con hashes, configuración en reporte y suite ejecutable; sin garantía de reproducción de biometría sin datos autorizados |
| NFR-07 | Conservación: pasos 7 días como propuesta configurable; altas hasta baja; ensayos hasta eliminación explícita acordada, con revisión al cierre del proyecto |
| NFR-08 | Trazabilidad: cada FR enlaza código, prueba técnica y evidencia de campo pendiente en MATRIZ_CUMPLIMIENTO.md |

No se inventan disponibilidad 99,9 %, tiempos p95, capacidad o precisión objetivo del cliente. Hay que acordarlos antes del experimento confirmatorio. Las reglas técnicas de Datamaq se adoptan proporcionalmente; no se declara Pyright estricto, cobertura total ni Clean Architecture canónica sin implementarlos y verificarlos.

## 7. Arquitectura y contratos

Monolito local por módulos: `main.py` (API y orquestación), `domain.py` (comparación y tokens), `vision.py` (modelos/imagen), `store.py` (persistencia), `cameras.py` (fuentes), `experiments.py` (ensayos) y `evaluation.py` (métricas), con frontend estático. SQLite evita un servicio adicional; FastAPI/Pydantic validan contratos; OpenCV ejecuta los modelos en CPU; Fernet protege campos locales. La ventana Qt reutiliza el frontend con un servicio HTTP ligado a loopback. Los datos se guardan por usuario; esquema y firma facial se versionan. La orquestación aún contiene reglas y consultas; no es la estructura de cuatro círculos de la plantilla.

Tablas: residents(id, profile cifrado, template cifrado, consentimiento/alta); cameras(id, label, role, source cifrada, autorización); events(id, fecha, resident_id FK, cámara, dirección, evidencia); evaluation_trials(id, record cifrado). No hay tabla de recorridos ni fotos.

API: `/api/status`, `/api/residents`, `/api/analyze`, `/api/passages`, `/api/events`, `/api/cameras`, `/api/evaluation/trials`, `/api/evaluation/report`. Todas esas operaciones requieren sesión y autorización por rol; solo estado de configuración y alta inicial/login son públicos con sus comprobaciones propias. Validación de imagen, hashes de modelos, bloqueo de inferencia y transacciones locales. La evidencia experimental no habilita pasos.

Configuración real: variables ACCESO_DATA_DIR, ACCESO_RETENTION_DAYS, ACCESO_MATCH_THRESHOLD y ACCESO_MATCH_MARGIN; `.env.example` es referencia, no se carga automáticamente. La ruta predeterminada es %LOCALAPPDATA%/AccesoResidencial/data en Windows. Claves aleatorias en data privada, nunca en Git. La clave local solo sirve para crear el primer administrador. Después se usan cuentas y sesiones; no registrar contraseñas, imágenes ni fuentes en logs. Hay RBAC y auditoría local de acciones; TLS y monitoreo productivo distribuido no se implementan en este piloto de loopback.

## 8. Validación, criterios de cierre y defensa

Ver PLAN_VALIDACION.md. Separar alta, exploración/calibración y prueba; fijar parámetros antes de la prueba. Medir errores por inscritos/no inscritos, capturas no aptas, condiciones y latencia, con denominadores. Pruebas sintéticas verifican lógica; no acreditan precisión biométrica ni permiten estimar tasas del edificio.

El cierre académico requiere: validación del problema con el interesado; aprobación del recorte por el docente; datos reales autorizados; informe final del experimento y sus limitaciones; repositorio propio sin datos personales; demostración reproducible y defensa del aporte individual. H1 puede no confirmarse y aun así generar una conclusión válida, si el método es correcto. La aprobación depende de la cátedra.

## 9. Responsabilidad y riesgos

Errores de coincidencia/rechazo; suplantación con fotos/videos; sesgos por condiciones, dispositivos y participantes; etiquetas equivocadas; repetición de muestras; claves perdidas; cámaras incompatibles; ausencia de dirección de cruce. Mantener alternativa humana. No inferir atributos sensibles desde el rostro ni tratar un no reconocido como intruso. Antes de uso real se necesita revisión del responsable, autorizaciones y evaluación legal/técnica específica.

## 10. Gestión y fuentes

Plan propuesto desde 15/10 hasta mediados de noviembre: caracterización y permisos; captura exploratoria; fijación de parámetros y prueba independiente; análisis y correcciones; informe/defensa. Fechas concretas en PLAN_VALIDACION.md, ajustables al calendario oficial.

Fuentes: contexto maestro del estudiante; plantilla y guía Datamaq recuperadas el 15/10/2026 (URLs/hashes en FUENTES_CONSIGNAS.json). La página institucional devolvió 403 y no se pudo contrastar su contenido completo. No se afirma que sus exigencias vigentes sean idénticas al resumen. Ver privacidad y fuentes oficiales en PRIVACIDAD_Y_FUENTES.md. Documento inicial anterior sustituido por esta SSOT.

## 11. Visitas y servicios: ampliación 0.4

**FR-16:** crear permiso temporal no biométrico para una persona, con anfitrión registrado o administración/áreas comunes, motivo, responsable y fechas con zona; autorización/información de datos declaradas obligatorias.

**FR-17:** registrar una entrada y salida manual por permiso en punto de acceso autorizado; verificación de persona/cruce obligatoria; no aceptar entrada futura, vencida, cancelada o repetida. No impide egreso físico ni acciona puertas.

**FR-18:** cancelar con motivo sin inventar salidas; si hay entrada sin salida, conservarla y permitir registrar egreso aunque venza/cancele el permiso.

**FR-19:** consultar con sesión autorizada, filtros, búsqueda por registros internos, paginación, código de referencia e historial cifrado; sin identificación de visitantes por rostro ni consulta pública.

**FR-20:** conservar/eliminar permisos por política propuesta, proteger bajas con visitas pendientes y preservar datos mediante backup/migración. Los registros nuevos atribuyen el operador a su cuenta autenticada; los históricos no cambian su atribución original.

**NFR-11:** transacciones e idempotencia evitan duplicar una creación reenviada o entradas concurrentes. **NFR-12:** migración del esquema 2 a 3 con respaldo y rollback; no cambia la firma facial.

Módulos: visits.py y visit_routes.py. Tablas nuevas visits y visit_events; campos personales y detalles cifrados. Contratos /api/visits y /api/visits/{id} con acciones entry/exit/cancel, todos protegidos. Retención configurable ACCESO_VISIT_RETENTION_DAYS, provisional 7 días para finalizadas/canceladas o vencidas sin uso; una entrada sin salida no se elimina automáticamente. Respaldos y bajas se gestionan según el protocolo. Hay autenticación por operadores individuales desde 0.5. No hay QR, confirmación digital del anfitrión ni automatización de cruce.

Pruebas y operación en VISITAS_Y_SERVICIOS.md. Esto complementa al núcleo de visión/validación, no sustituye el experimento de IA con datos autorizados. No se declara completada la consigna académica ni la aprobación del profesor.

## 12. Ampliación 0.5: cuentas, restricciones y auditoría

| ID | Requisito / criterio |
|---|---|
| FR-21 | Configuración inicial con clave local; posteriormente cuentas Administración/Seguridad, sesiones revocables y cambio obligatorio de contraseña temporal |
| FR-22 | Administración gestiona cuentas; Seguridad no puede modificar padrón/cámaras/cuentas/restricciones ni consultar evaluación/auditoría; el servidor exige esos permisos |
| FR-23 | Restricción revisable de residente o registro externo manual, motivo y vigencia autorizados; baja con motivo; impedir entrada activa, permitir salida |
| FR-24 | Registrar operador autenticado en pasos de residentes e historial de visitas nuevos; no inventar atribución de registros anteriores |
| FR-25 | Auditar operaciones de escritura con detalles cifrados y cadena HMAC; detectar alteraciones/pérdidas frente al marcador local; ante fallo bloquear cambios y permitir revisión/conciliación explícita |
| FR-26 | Selector de webcam y vista anónima de fuentes complementarias activadas manualmente; sin seguimiento nominal |
| FR-27 | Informe HTML de ensayos realmente existentes, sin porcentajes fabricados; descarga autorizada a Administración |
| FR-28 | Clip manual opcional de webcam local, sin audio y hasta 120 segundos; descarga explícita; cancelación al cerrar sesión; no grabación continua IP/DVR |
| NFR-13 | Contraseñas PBKDF2-HMAC-SHA256 con sal aleatoria y 600.000 iteraciones; sesiones de 8 horas guardadas como hash; bloqueo temporal por intentos fallidos |
| NFR-14 | Migración a esquema 4 con respaldo, conservación de plantillas/cuentas y revocación de sesiones al importar una copia |

Módulos nuevos: auth.py, audit.py, restrictions.py, admin_routes.py y report.py. Tablas users, sessions, login_attempts, restrictions, audit_log; events agrega operator_id. No se agregan fotos ni una base biométrica de personas externas. Nombres de usuario y metadatos de relación/tiempo permanecen visibles en SQLite; perfiles, motivos y detalles se cifran. Cifrar no protege frente al acceso conjunto al archivo y su clave.

Conservación provisional: auditoría y restricciones finalizadas 90 días; no eliminar una restricción externa referenciada por visitas conservadas. Alta de cuentas hasta baja administrativa; las cuentas desactivadas se conservan como referencia de acciones. Estas políticas deben acordarse antes de uso real. No son plazos legales. Clips e informes descargados son archivos separados y requieren su propia gestión/eliminación. La cadena local no es inmutable frente a control del sistema operativo. Las comprobaciones de software no validan uso biométrico, antisuplantación ni cierre académico.

## 13. Correcciones de seguridad 0.6

**FR-29 (histórico 0.6, sustituido por FR-30 en 0.7):** antes se exigían rostro, PIN y cruce observado; no hay omisión del PIN ni valor por defecto. Administración lo configura/restablece tras confirmar verificación presencial. No bloquea registrar salidas, no abre cerraduras ni acredita PAD.

**NFR-15:** sesiones con vida máxima 8 horas, inactividad de solicitudes 15 minutos, máximo 3 por usuario y revocación al reiniciar; bloqueo de login por cuenta además de límite por IP; token de coincidencia ligado a sesión concreta. El panel cierra además por inactividad humana, sin equipararla a la verificación de presencia.

**NFR-16:** límite de 30 MB medido sobre chunks antes del JSON, incluso sin Content-Length fiable; JPEG/PNG con límites de resolución; errores de validación sin valores sensibles; encabezados de seguridad también en rechazos. Los lanzadores ignoran cabeceras proxy y limitan concurrencia HTTP a 32. No es una protección absoluta contra DoS local.

**NFR-17:** datos y respaldos con permisos privados de SO, rechazo de enlaces de claves/base; no protege contra quien controla la cuenta Windows/SYSTEM, malware de esa cuenta o toma de propiedad por un administrador privilegiado. Se mantiene el cifrado Fernet y no se promete protección de claves frente al propio equipo.

**NFR-18:** PIN derivado con PBKDF2-HMAC-SHA256, sal independiente y 600.000 iteraciones; 5 fallas bloquean 5 minutos con contador persistente por residente. Migración esquema 5 conserva plantillas/cuentas, revoca sesiones y no inventa credenciales. Baja de residente elimina su hash PIN. El PIN no se incorpora a eventos, auditoría ni reportes. No se afirma un factor resistente a phishing ni se equipara a una prueba biométrica de vida.

Módulos security.py, file_security.py y credentials.py; tabla resident_credentials, columna sessions.last_seen_at y restricciones de versiones en constraints-seguridad.txt. tests/test_security_hardening.py aporta regresiones técnicas; SEGURIDAD_0_6.md separa correcciones, mitigaciones y riesgos restantes. La validación de biometría, red/cámaras y Windows del edificio sigue pendiente.

## 14. PAD 0.7: alcance vigente que sustituye el PIN obligatorio

La petición del estudiante prioriza detección de fotos/pantallas, cámara seleccionable y supervisión de seguridad. No se usa el PIN como solución a presentación de fotos. Los campos/credenciales heredados se conservan por compatibilidad pero no controlan el flujo 0.7.

**FR-30:** ejecutar un modelo PAD RGB anti-spoof-mn3 con pesos/licencia/contrato verificados y exigir tres capturas diferentes de una misma identidad con score sobre umbral provisional, separación temporal y vigencia. Resultado incierto, sospechoso, repetido, múltiple, modelo ausente o error no habilita confirmación. Una nueva captura que falla revoca el token anterior.

**FR-31:** permitir seleccionar webcam o fuente USB/RTSP compatible; el análisis de una fuente de acceso del servidor usa su captura, no una imagen aportada como si fuera esa fuente. Observar no identifica personas. Detener/reiniciar fuente invalida su evidencia de sesión.

**FR-32:** mostrar a Seguridad pendiente/posible foto o pantalla/incierto/superado con lenguaje de revisión, sin confundir score con certeza, persona desconocida con intruso o PAD con cruce de puerta. Confirmar pasos sigue siendo manual. El programa no bloquea una salida física.

**FR-33:** alta de residentes con capturas que superen PAD además de calidad/consistencia; registrar ensayos PAD aparte, etiquetados por humano, cifrados, sin fotos, con reporte/exportación y eliminación explícita. Los ensayos son por captura y NO prueban la regla temporal completa ni presencia física. Medir aceptaciones de ataques y rechazos de personas reales con denominadores; separar no evaluables y fases.

**NFR-19:** no modificar firma/plantillas de identidad al agregar PAD; manifiesto independiente en models/pad. Esquema 6 agrega pad_trials, respalda y revoca sesiones al migrar. Sin paquetes Python nuevos; se usa OpenCV DNN existente. No hay opción de cliente para declarar PAD válido u omitirlo.

Pregunta adicional: ¿qué tasas de aceptación de fotos/pantallas y rechazo de personas reales presenta el clasificador en cámaras y condiciones del piloto? Todavía no hay respuesta medida. El umbral 0,95, tres muestras, intervalo mínimo 0,6 s, ventana máxima 6 s y span mínimo 2 s son parámetros de diseño provisionales, no resultados/consignas del profesor ni precisión prometida. La consistencia temporal es una barrera auxiliar; no vuelve criptográficamente confiable la captura.

Implementación: pad.py, pad_trials.py, main.py, domain.PassTokens y panel; evidencia en tests/test_pad.py y frontend_smoke.cjs. La evaluación de identidad anterior se mantiene separada. Hipótesis/afirmaciones sobre seguridad integral no se consideran demostradas por ejecutar un modelo preentrenado ni por tests sintéticos. Ver PAD_0_7.md para validación requerida, límites y fuentes.
