# Plan de datos y validación — 0.2

Protocolo propuesto, no experimento realizado ni tamaño de muestra estadísticamente validado. No recopilar datos de vecinos sin autorizaciones. Puede iniciarse con adultos voluntarios en un entorno controlado, sin conectar cerraduras ni cámaras del edificio.

## 1. Definir el caso

Entrevistar al encargado: entidad/localidad, procedimiento de ingreso actual, inconveniente concreto y frecuencia, quién verifica, qué registro existe, costos y alternativa disponible. No tomar «interés» como prueba de inseguridad o rentabilidad. Confirmar con el docente el nuevo recorte antes de prometer un sistema físico completo.

## 2. Preparar y separar participantes y sesiones

Asignar códigos estables V01, V02, etc., sin nombre en los informes. Tener tanto inscritos como no inscritos, ambos informados y voluntarios. No inscribir después a los no inscritos antes de terminar la misma evaluación: cambia la galería. Si cambia, usar sesión nueva.

Como piloto de viabilidad se puede intentar reunir 6–10 inscritos y 3–5 no inscritos, si se consiguen legalmente. Es una meta logística propuesta, no requisito docente ni garantía de potencia estadística. Documentar la cantidad real y ampliar si la incertidumbre impide concluir. Si solo se prueba una persona, declarar que es una demostración funcional, no validación de población.

Tres etapas:

1. **Alta:** tres capturas por inscrito, en su sesión de registro.
2. **Exploración:** sesión distinta; observar condiciones/errores y, si corresponde, ajustar umbral/margen por variables de entorno. Documentar cada configuración y el criterio del ajuste. No usar resultados de prueba reservada para elegirla.
3. **Prueba reservada:** fecha o sesión posterior, galería/configuración fijas; incluir inscritos y no inscritos, sin eliminar errores ni repetir selectivamente hasta acertar. No concluir que una casilla garantiza independencia.

El panel rechaza píxeles idénticos y cambios de configuración/fase dentro de una sesión. No detecta recortes similares, imágenes de la misma ráfaga o declaraciones falsas. Esas fugas necesitan control experimental humano. Separar también cámaras/días cuando sea posible y dejar constancia de qué se separó realmente.

## 3. Capturar evidencia desde la app

1. Registrar participantes voluntarios; no guardar nombres reales si no hacen falta para la práctica controlada.
2. En Control de acceso iniciar **Cámara de esta computadora** y permitir su uso.
3. Entrar a **Evaluación académica** sin detener la cámara.
4. Escribir sesión (ej. exploracion_dia2), etapa y código estable del participante.
5. Elegir la identidad que está realmente frente a la cámara o **Persona no inscrita**. Esta etiqueta debe conocerse antes del resultado.
6. Elegir condición observada y confirmar autorización/captura nueva. Pulsar **Capturar y medir un ensayo**.
7. Repetir según un plan fijado previamente y equilibrado por participante/condición. Registrar todos los intentos, incluidos rechazos y malas capturas.
8. Descargar evidencia JSON al finalizar. No subirla a un repositorio público sin una revisión de minimización y autorizaciones. La base guarda resultados cifrados, no imágenes.

La cámara de ensayo del panel es la webcam del navegador. No se atribuyen resultados a una cámara IP del edificio. Los ensayos no abren puertas ni escriben movimientos. Se conserva la evidencia en la base hasta borrarla; acordar fecha de eliminación y revisar al cierre. Las exportaciones ya descargadas se borran aparte.

## 4. Escenarios

| Escenario | Etiqueta / qué evaluar |
|---|---|
| Inscrito frontal | Identificación correcta, rechazo, asignación equivocada |
| Persona no inscrita | Rechazo o falsa aceptación; no equivale a intruso |
| Iluminación baja/contraluz | Calidad y errores; documentar cámara/distancia y condiciones reales |
| Lentes/ángulo | Variación por condición sin deducir atributos sensibles |
| Sin rostro | Abstención; prueba de robustez, excluida de denominadores de identidad |
| Varios rostros | Recuadros múltiples y abstención de verificación; prueba de robustez, excluida de denominadores de identidad |
| Foto/video autorizado del propio participante | Registrar aparte que PAD no está validado; no mezclar con intentos humanos ni afirmar resistencia |
| Paso observado | Confirmación manual, dirección y hora; comparar con anotación independiente del operador |
| Red/cámara desconectada | Error claro, sin identidad/token falso ni paso automático |

El ensayo multifacial no identifica a todos ni mide si cruzaron. Para una evaluación formal de detección (precision/recall por rostro e IoU) hacen falta recuadros anotados manualmente. La cantidad en pantalla no sustituye esa anotación; no se incluye una métrica de detección inventada.

## 5. Métricas y baseline

Para inscritos: correctos, rechazados y asignados a otra identidad, cada uno con denominador de intentos individuales de inscritos. Para no inscritos: aceptados indebidamente / intentos individuales de no inscritos. Incluir mala captura de una persona en las tasas operativas; reportar además calidad. Escenas sin rostro o con varios se muestran separadamente como robustez; no inflar rechazo de desconocidos con escenas vacías.

Comparar contra **SFace + vecino más cercano sin rechazo**, manteniendo la misma calidad de imagen. La comparación estudia la regla de decisión; no compara redes neuronales distintas ni acredita ahorro respecto de portería. Si hay una imagen no apta, ambos se abstienen y eso queda explícito.

Mediana y p95 son de procesamiento en el servidor; no incluyen captura, HTTP o pantalla. Para latencia integral, medir independientemente desde presentación del rostro hasta visualización, con equipo/cámara/red documentados. No inventar un SLA.

JSON incluye conteos, tasas, condiciones, configuración, tamaño/huella de galería, hash de modelos, latencias y registros seudonimizados. Wilson 95 % es descriptivo por intento y no corrige correlación entre capturas de una persona. Para inferencia de población, aumentar participantes y usar estimaciones agrupadas por persona/sesión; no presentar esos intervalos como garantía de seguridad.

## 6. Criterios de conclusión

No fijamos «99 % de precisión» sin fundamento ni declaramos rentable el sistema. Antes de prueba reservada, acordar qué tasas/tiempos serían aceptables para un piloto y por qué. Si no hay criterio del cliente, informar resultados descriptivos y la imposibilidad de recomendar despliegue.

H1 se evalúa mostrando falsas aceptaciones y rechazos de ambos métodos, también si empeoran. No eliminar resultados negativos. Con pocos voluntarios, concluir solo para las sesiones observadas. Sin PAD, integración física y validación específica, no recomendar apertura automática aunque el experimento no arroje errores.

## 7. Cronograma de trabajo propuesto

| Período | Resultado esperado, no realizado |
|---|---|
| 15–18 octubre | Identificar administración, entrevista y confirmar recorte con docente |
| 19–25 octubre | Autorizaciones, voluntarios, altas y exploración |
| 26 octubre–1 noviembre | Fijar parámetros y ejecutar prueba reservada |
| 2–8 noviembre | Analizar evidencia, condiciones/errores y corregir defectos de software |
| 9–mediados de noviembre | Informe, repositorio limpio, demostración y ensayo de defensa |

Si los permisos no llegan, conservar el alcance de laboratorio con voluntarios y explicitar que no es una validación en el edificio. No inventar datos para sostener el cronograma.

## Ampliación 0.7: evaluar PAD separadamente

El clasificador PAD está integrado, pero no validado con personas/cámaras del piloto. Ejecutar el protocolo de PAD_0_7.md: personas presentes, fotos impresas y fotos/videos en pantallas autorizados, condiciones variadas, sesiones de exploración y prueba separadas. El panel guarda ensayos etiquetados de UNA captura, por webcam o fuente de acceso seleccionada. Su reporte no mide la decisión temporal completa; el ensayo de secuencias/confirmación debe anotarse aparte con el protocolo. No atribuir al modelo las tasas publicadas en su dataset original ni usar pruebas sintéticas como eficacia local.
