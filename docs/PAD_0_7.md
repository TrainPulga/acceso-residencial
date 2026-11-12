# Control de fotos y pantallas · PAD RGB 0.7

## Requisito y estado real

El requisito vigente es reconocer residentes con una cámara seleccionable y comprobar posibles presentaciones de fotos/pantallas, con supervisión de seguridad. Un PIN no sustituye ese control y ya no es obligatorio en el acceso. Se conserva el resto de protecciones de cuentas, API, archivos y respaldos de 0.6.

Está implementado un clasificador PAD real y una regla temporal que condicionan las confirmaciones. **No hay aún resultados de eficacia con personas, fotos o pantallas reales del piloto.** Las pruebas de lógica y ejecución de pesos no acreditan que se detecten todas las fotos o videos. No se declara el software apto para accionar una cerradura ni certificado antisuplantación.

## Modelo y contrato verificables

Se incorpora anti-spoof-mn3 desde Open Model Zoo, bajo MIT. Pesos ONNX originales, tamaño 12.270.179 bytes; se verificó su SHA-384 contra model.yml publicado. El paquete incluye SHA-256 local, fuentes y licencia en models/pad. Su incorporación no modifica el manifiesto ni la representación YuNet/SFace de identidad: las plantillas anteriores continúan siendo compatibles.

El preprocesamiento toma el recorte rectangular de un solo rostro apto, lo convierte de BGR a RGB, redimensiona a 128×128, normaliza por canal según contrato publicado y forma un tensor NCHW float32. La salida original tiene dos clases, bona fide y presentación. Se rechazan regiones pequeñas/recortadas, múltiples rostros, salidas no finitas o un contrato de salida inválido. No se reinterpreta el score como probabilidad calibrada de presencia física o identidad. El modelo se ejecuta en OpenCV DNN CPU existente; no hay servicio externo de rostros ni dependencia nueva.

## Regla de operación y cierre ante fallos

Para emitir un token de confirmación se exige:

1. Un solo rostro que supere calidad y encuentre coincidencia no ambigua en el padrón autorizado.
2. Score bona fide de al menos **0,95** en tres capturas diferentes de la misma identidad y fuente/sesión.
3. Separación de al menos **0,6 segundos** entre muestras admitidas, con **dos segundos o más** entre primera y última y ventana máxima sin actualización de **seis segundos**.

Son parámetros de diseño **provisionales**, no requisitos medidos del cliente ni una precisión del 95 %. Necesitan exploración y prueba reservada. La cadencia normal del panel es aproximadamente 1,5 segundos más procesamiento; no se promete verificación instantánea. La separación temporal no se considera un mecanismo criptográfico de frescura de cámara.

El servidor invalida el token anterior al analizar la captura siguiente y solo emite otro si vuelve a cumplirse la regla. Una repetición exacta de píxeles, duda, score insuficiente, cambio de identidad, ausencia/modelo dañado o error no habilita confirmación. Tokens ligados a cámara y sesión, de un uso y con vigencia de veinte segundos. Reiniciar/detener la fuente descarta la comprobación. La desconexión de una fuente del servidor revoca su evidencia en las sesiones. No se acepta una imagen subida como captura de una cámara de acceso del servidor.

El endpoint de paso exige el token emitido por el servidor después de PAD: declarar `passed=true` o enviar un PIN desde un cliente no lo reemplaza. Las restricciones administrativas se vuelven a comprobar para entrada. La salida física no se bloquea: la aplicación no acciona puertas. Si no se completa PAD, no inventa un movimiento biométrico y el guardia aplica el procedimiento presencial/alternativo acordado.

Los movimientos nuevos indican en su evidencia que la secuencia PAD superó la regla del piloto. Los históricos no se reescriben como si hubieran sido verificados. `pad.passed`/`pad_check_passed` representan esa regla; el campo heredado `liveness_verified` sigue falso para no prometer una presencia física comprobada o certificada. `pad_validated_locally` también permanece falso hasta realizar y documentar el experimento; no cambia automáticamente por acumular pruebas de software.

## Cámara seleccionable

La elección de cámara se conserva: webcam del equipo, USB del servidor y RTSP/RTSPS privado compatible. La misma regla PAD se aplica a fuentes de acceso de ambas modalidades. Las cámaras de observación siguen detectando sin dar nombres ni rastrear recorridos. No hay integración universal con cualquier DVR/SDK ni descubrimiento ONVIF. Las fuentes HTTP no se habilitan como atajo.

El software recibe píxeles: **no autentica el dispositivo físico**, no distingue con garantía una cámara virtual y no protege una estación comprometida. Su calidad y desempeño pueden cambiar entre cámaras, resolución, compresión, distancia e iluminación. Tener selector no hace equivalentes a todas las cámaras. Verificar la fuente real forma parte de la instalación, sin exigir una marca única para desarrollar el prototipo.

## Interpretación del panel

Pendiente significa esperar capturas. Incierto o no disponible significa que no se pudo verificar, sin acusación. Posible foto/pantalla es una alerta del clasificador que requiere revisión presencial, no prueba de fraude. Superado habilita preparar un paso observado en el piloto, sin certificar identidad infalible ni cruce. El guardia sigue confirmando lo que ocurrió y el sistema no realiza aperturas automáticas.

No se usan parpadeos o giros de cabeza improvisados como sustituto del modelo ni se afirma que un movimiento descarte un video. La secuencia temporal es auxiliar: un atacante puede cambiar píxeles al mover una foto y un video puede aportar capturas distintas; el PAD debe evaluarse también frente a eso.

## Protocolo de datos y evidencia académica

Usar únicamente participantes adultos voluntarios y fotos/videos propios autorizados. Separar alta de reconocimiento, exploración y prueba reservada por sesión; anotar cámara real, ubicación, resolución, compresión, iluminación, distancia y cualquier incidencia. Fijar la política antes de prueba reservada. Si cambia cámara/modelo/umbral, usar otra sesión y documentar la modificación; no elegir el umbral mirando únicamente la prueba final.

Preparar intentos de persona presente, foto impresa, foto en pantalla y video en pantalla. Variar condiciones según recursos reales y registrar todos los intentos, incluidos fallos. Las impresiones y pantallas también pueden producir rechazo de calidad; eso no demuestra que el clasificador haya detectado el ataque. No seleccionar solo los casos en que acierta. Documentar participantes, sesiones y cantidades efectivamente obtenidas, sin inventar independencia estadística.

### Ensayos por captura desde el panel

En Evaluación académica → Ensayos antisuplantación, seleccionar la fuente de acceso e iniciarla. Completar código de participante sin nombre, sesión, fase, condición y lo que está realmente frente a la cámara. La etiqueta es humana y anterior al resultado, nunca la predicción del modelo. Guardar un ensayo y exportar JSON al terminar. Las fuentes del servidor se muestrean desde su stream; la webcam aporta una captura actual del panel.

Cada ensayo guarda cifrados score, etiqueta, aptitud, fuente interna, código, configuración, huella de imagen y tiempo, sin foto. Duplicados exactos y cambios de fase/configuración dentro de una sesión se rechazan. Los códigos seudonimizan, no anonimizan. El cambio de dispositivo USB del navegador requiere anotar otra sesión: el identificador genérico browser-access no documenta por sí solo qué hardware se usó.

El reporte muestra ataques aceptados/total de ataques, personas reales rechazadas/total de personas reales, capturas no evaluables y resultados por tipo de presentación. Incluye tasas operativas con no evaluables y tasas separadas entre capturas evaluables; denominador cero produce `null`, nunca un falso 0 %. No se denominan resultados certificados ISO. Las capturas no evaluadas no cuentan como demostración de detección correcta. Las incidencias técnicas que impidan guardar un ensayo deben registrarse aparte; no ocultarlas reintentando hasta acertar.

**Estas tasas son de una captura, no de la regla temporal completa de acceso.** La evaluación de reconocimiento anterior también continúa siendo distinta. No sumar ni multiplicar automáticamente las tasas para inventar una seguridad conjunta.

### Prueba independiente del flujo completo

Registrar aparte cada intento completo, desde comienzo hasta resultado, para persona presente y cada medio de presentación. Anotar código de intento/persona, sesión/cámara, medio real presentado, condición, calidad, resultado final y tiempo observado. Incluir presentaciones movidas, videos y cambios de persona, sin convertir el protocolo en una promesa frente a todos los ataques. El guardia no debe confirmar como real un cruce que no sucedió; se pueden probar bloqueos sin escribir movimientos falsos.

Comparar cantidades y tasas por intento completo, con denominadores separados para ataques y personas reales, y documentar correlación entre repeticiones de la misma persona/medio. Un piloto pequeño con cero aceptaciones de ataques no prueba riesgo cero ni generalización. No usar los tests sintéticos o las métricas originales del autor como sustituto de estos datos.

## Privacidad, límites y pendientes

No se guardan recortes ni imágenes de reconocimiento/PAD. El estado temporal contiene identificador, tiempos y huellas, no una grabación. Los ensayos se conservan hasta borrado explícito acordado; las exportaciones se gestionan aparte. Los códigos no están vinculados automáticamente al padrón: atender supresión por código o borrar el conjunto. No subir imágenes/resultados identificables a un repositorio público.

Persisten riesgos de falsa aceptación/rechazo, impresiones/pantallas no cubiertas por el entrenamiento, máscaras, deepfakes e inyección de imágenes o compromiso del equipo. Este modelo fue entrenado fuera del edificio; un buen resultado de su autor no demuestra adaptación local. El PAD pasivo RGB no ofrece garantía universal y no reemplaza revisión profesional de un despliegue físico.

Pendientes concretos: ensayo en Qt Windows/cámaras reales, corpus autorizado, calibración y prueba independiente, revisión del procedimiento con el encargado, criterios de aceptación acordados y documentación de resultados/limitaciones. No se da por cerrada la consigna académica ni la seguridad productiva.

## Fuentes

- Contrato y huella publicada: https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/public/anti-spoof-mn3/model.yml
- Documentación del modelo y licencia: https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/public/anti-spoof-mn3/README.md
- Autor y pipeline: https://github.com/kprokofi/light-weight-face-anti-spoofing
- NIST, evaluación de PAD software y límites de generalización: https://www.nist.gov/publications/face-analysis-technology-evaluation-fate-part-10-performance-passive-software-based

Licencia MIT original incluida; no se redistribuye el dataset de entrenamiento. No hay afiliación ni certificación de Intel/OpenVINO/NIST.
