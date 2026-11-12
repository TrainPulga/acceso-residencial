# Guía de evaluación del Proyecto Integrador

## Resumen comprobable

Acceso Residencial es un prototipo local de escritorio para asistir la verificación de adultos residentes voluntarios y el registro manual de pasos que un operador observa. El caso parte del interés que el estudiante comunicó haber recibido de un encargado de edificios. Aún deben verificarse el procedimiento actual, la necesidad concreta, las condiciones de uso y la autorización de la administración.

La pregunta de Ciencia de Datos compara una regla SFace con umbral y margen —que puede abstenerse— contra una línea base que siempre elige el vecino más próximo. El proyecto también integra un clasificador PAD RGB preentrenado para explorar fotos y pantallas. Sus pesos/modelos no fueron entrenados por el estudiante y **no se midió eficacia local con personas**.

## Criterios de la evaluación final

La matriz completa está en [MATRIZ_CUMPLIMIENTO.md](MATRIZ_CUMPLIMIENTO.md). Esta tabla separa lo que el repositorio permite revisar de la evidencia que todavía debe producir el proyecto.

| Criterio comunicado por el estudiante | Evidencia revisable | Situación que no debe darse por demostrada |
|---|---|---|
| Originalidad del trabajo | Integración del problema, reglas, evaluación y prototipo; decisiones en `SRS_SSOT.md` | No se afirma que reconocimiento facial o PAD sean invenciones nuevas |
| Lógica del planteo | Problema/pregunta/H1 y alcance en `SRS_SSOT.md`; procedimiento en `PLAN_VALIDACION.md` | El problema operativo y la aceptación del interesado requieren entrevista/documentación |
| Adecuación de la metodología | Separación de sesiones, baseline, denominadores y criterios en `PLAN_VALIDACION.md` y `PAD_0_7.md` | El protocolo todavía no equivale a experimento ejecutado |
| Calidad de elaboración con los datos obtenidos | Evaluadores `evaluar_piloto.py`, panel de ensayos, esquemas de métricas y pruebas | No hay resultados humanos ni de ataques locales cargados en el repo |
| Coherencia entre hipótesis, datos y conclusiones | H1/H2, condiciones de refutación y límites en SRS y evaluación | No hay conclusión empírica que permita aceptar H1/H2 |
| Documentación aportada | SRS/SSOT, matriz, privacidad, seguridad, actualización, plan de datos y defensa | El informe final con datos, resultados y aporte individual sigue pendiente |

## Recorrido de código y evidencia

| Qué revisar | Ubicación |
|---|---|
| Requisitos funcionales/no funcionales, hipótesis y arquitectura | `docs/SRS_SSOT.md` |
| Requisito → implementación → prueba → límite | `docs/MATRIZ_CUMPLIMIENTO.md` |
| Evaluación de identificación y métricas | `access_app/evaluation.py`, `evaluar_piloto.py`, `docs/PLAN_VALIDACION.md` |
| PAD, reglas temporales y experimentos separados | `access_app/pad.py`, `access_app/pad_trials.py`, `docs/PAD_0_7.md` |
| Persistencia, cifrado, auditoría y usuarios | `access_app/store.py`, `access_app/security.py`, `access_app/auth.py`, pruebas en `tests/` |
| Aplicación de escritorio y operación | `escritorio.py`, `access_app/static/`, `docs/ESCRITORIO_Y_ACTUALIZACIONES.md` |
| Estado y limitaciones de esta versión | `docs/ESTADO_ENTREGA.md`, `docs/VERIFICACION_TECNICA.json` |
| Participación humana, autorización y defensa | `docs/PLAN_VALIDACION.md`, `docs/PRIVACIDAD_Y_FUENTES.md`, `docs/ENTREVISTA_Y_DEFENSA.md` |

Las pruebas por archivo se encuentran bajo `tests/`. La suite completa se reproduce con los comandos de `README.md`. La ejecución de GitHub Actions del commit publicado `6b67b70d586c1d920d1424b2173809f63c42da65` pasó en Ubuntu y Windows; verifica la suite Python y el smoke de frontend, no una instalación/cámara física ni desempeño biométrico.

## Lectura de resultados

- `expected_id: null` representa una persona no inscrita; no significa que sea intrusa.
- Un rechazo de calidad/captura debe distinguirse de una identificación correcta, una identidad equivocada y una falsa aceptación de no inscrito.
- El score PAD no es probabilidad calibrada ni puede interpretarse como porcentaje de seguridad.
- PAD por captura y la secuencia temporal del flujo de acceso son experimentos distintos; no combinar sus tasas sin un experimento de punta a punta.
- Los datos de prueba sintéticos verifican reglas y contratos, no reconocen a personas. Los pesos reales cargados con imágenes artificiales solo prueban la ruta de inferencia.
- Una tasa observada de cero en una muestra pequeña no demuestra que el riesgo sea cero ni permite generalizar al edificio.

## Pendientes antes de una conclusión académica o un uso real

1. Documentar entrevista, interesado, procedimiento actual y aprobación del recorte por el docente.
2. Acordar autorizaciones, finalidad, alternativa presencial, conservación y eliminación antes de convocar participantes adultos.
3. Ejecutar el protocolo con sesiones separadas y registrar todas las condiciones, errores, intentos no evaluables y resultados negativos.
4. Elaborar el informe con denominadores, incertidumbre y límites; explicar aporte individual y uso de IA según las reglas de la cátedra.
5. Probar en Windows con cámaras reales y revisar privacidad/seguridad para el entorno concreto.

La publicación del código y el CI aprobado mejoran la reproducibilidad técnica. No reemplazan esos pendientes ni implican aprobación docente, certificación de seguridad, viabilidad comercial o permiso para controlar puertas.
