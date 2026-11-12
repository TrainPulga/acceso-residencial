# Cumplimiento y trazabilidad — 0.7

Estado al 17/10/2026. «Implementado» no significa probado con residentes ni aprobado por el profesor.

La publicación del repositorio y el estado actual del CI se actualizaron después de esta fecha; ver [ESTADO_ENTREGA.md](ESTADO_ENTREGA.md) y [GITHUB_Y_DISTRIBUCION.md](GITHUB_Y_DISTRIBUCION.md). Esta matriz describe requisitos y evidencia del software, no sustituye resultados del experimento de campo.

## Consignas generales aportadas por el estudiante

| Exigencia | Evidencia construida | Falta para cerrar |
|---|---|---|
| Problema real, orientación Industria, aporte individual | Contacto con encargado comunicado por el estudiante; SRS define problema/pregunta/usuarios | Identificar administración argentina, entrevista y aceptación del recorte; confirmar orientación con docente |
| Ciencia de Datos/IA genuina | Procesamiento, YuNet/SFace, representación, rechazo y comparación de decisiones | Ensayos reales y análisis de errores; no basta ejecutar un modelo |
| Datos obtenidos y calidad de elaboración | Altas reales posibles, protocolo y captura de ensayos en panel | Capturas autorizadas en sesiones separadas y etiquetas verificadas |
| Hipótesis, datos y conclusiones coherentes | H1/H2, baseline y métricas con denominadores, configuración y condiciones | Exportar mediciones y escribir conclusiones sin extrapolar al edificio |
| Originalidad | Aplicación e integración al caso y evaluación propia | Documentar decisiones individuales; no atribuir invención de reconocimiento facial |
| Metodología adecuada | PLAN_VALIDACION, separación de fases, bloqueo de duplicados y drift de sesión | Supervisar independencia real y registrar desvíos; confirmar criterios antes de prueba |
| Producto de software | Panel, API, persistencia y modelos incluidos | Ensayo integral con hardware del interesado; el estudiante informó arranque Windows de 0.1 reparada |
| Documentación y defensa | SSOT, fuentes, trazabilidad, protocolo, manual, guion | Repositorio propio, informe final con resultados reales y defensa practicada |
| Responsabilidad legal/social | Cifrado, consentimiento declarado, baja, observación anónima, alcance local | Autorizaciones, procedimiento informado y revisión del responsable para uso real |
| Contenidos del diseño curricular | Datos/imágenes/modelos/postprocesamiento/visualización/informes | No se fuerzan habla, IoT u OCR; confirmar si existe una instrucción docente adicional |

## Requisito → implementación → prueba/evidencia → conclusión posible

| ID | Código | Pruebas técnicas / evidencia de campo |
|---|---|---|
| FR-01 | main.enroll/delete_resident, Store | test_consent_and_adult_required, test_repeated_capture_is_rejected, test_baja_deletes_template_and_associated_events; voluntarios pendientes |
| FR-02 | Vision.detect, main.analyze, overlay | test_actual_models_load_and_reject_empty_scene, test_multiple_faces_visible_but_no_access_identity_or_token; conteos reales pendientes |
| FR-03 | identify, Vision.template | test_unknown_never_becomes_a_resident, test_similar_candidates_require_abstention; tasas humanas pendientes |
| FR-04/05 | PassTokens, confirm_passage | test_match_does_not_record_or_unlock, test_crossing_must_be_observed, test_expired_token, test_pass_token_is_single_use; cruces físicos automáticos fuera de alcance |
| FR-06 | Store.events/prune_events | test_retention_excludes_old_passages, baja; validación de reloj/equipo pendiente |
| FR-07 | validate_source, CameraHub | test_private_sources, test_public_or_invalid_sources_rejected; cámaras reales pendientes |
| FR-08 | main.analyze | test_secondary_camera_never_identifies; detección múltiple de campo pendiente |
| FR-09 | Experiments.record, panel evaluación | test_trials_are_explicit_and_do_not_record_movements, test_invalid_trial_rejected; etiquetas reales pendientes |
| FR-10 | evaluation.metrics/summarize | test_no_measurement_is_not_zero_error, test_wrong_known_is_distinct_from_unknown_acceptance, test_rejection_beats_always_nearest_for_synthetic_unknown; resultado del modelo no medido todavía |
| FR-11 | Experiments.record | test_reused_capture_and_session_configuration_drift_rejected, test_subject_code_cannot_change_ground_truth; similitud de fotos y sesiones requieren revisión humana |
| FR-12 | Experiments.clear/purge_subject | test_delete_resident_also_removes_associated_trial, test_erasing_trials_and_protecting_reports; copias exportadas fuera de la base se gestionan aparte |
| NFR-01 | identify sin cupo fijo | test_no_population_cap_in_comparison usa vectores sintéticos, no demuestra capacidad ilimitada |
| NFR-02/03/04 | iniciar, middleware/admin, Store.seal | test_private_api_requires_key, test_other_origins_and_hosts_are_rejected, test_personal_fields_encrypted_at_rest; auditoría local con cadena HMAC; revisión productiva pendiente |
| NFR-05/06 | manifiesto modelos, ensayos y pytest | Pruebas reales de carga; latencia de personas/cámaras solo al ejecutar ensayos |
| NFR-07/08 | retención, documentación y exclusiones Git | Revisión del paquete sin datos; cerrar política experimental con responsable |

## Adaptación de Datamaq: límites explícitos

Se recuperaron y leyeron la plantilla backend y la guía. Se cubren contexto, alcance, Canvas, FR/NFR, datos, arquitectura, configuración, secretos, pruebas, trazabilidad y convenciones de publicación. No hay mensajería externa ni cobros porque no aportan al MVP. La gobernanza de múltiples agentes es opcional y no se implementa.

No se cumplen aún las reglas técnicas más estrictas de esa plantilla: cuatro círculos canónicos, repositorios totalmente tipados, Pyright estricto, Ruff y todos sus guanteletes AST. El contexto maestro solicita adaptar y evitar sobreingeniería; esta es una adaptación declarada. Si el docente exige esas reglas literalmente, constituyen trabajo adicional y hay que confirmar esa exigencia. No se oculta como «100 % cumplido».

La página institucional no pudo consultarse por 403. La aprobación y cualquier exigencia adicional quedan pendientes; este archivo no sustituye la rúbrica oficial.

## Actualización de escritorio 0.3

FR-13: ventana propia y cierre controlado (`escritorio.py`, `runtime.py`); servicio HTTP real comprobado, renderer/webcam Windows pendientes. FR-14/15 y NFR-09/10: importación, respaldo, reapertura, recuperación, no sobrescritura, esquema futuro y firma incompatible en `tests/test_updates.py`. Políticas de cámara/origen en `tests/test_desktop_policy.py`; no son pruebas de renderizado ni hardware. Modelo original conservado. Visitas incorporadas en 0.4; restricciones y usuarios/permisos en 0.5. No se presenta la prueba de hardware ni el proyecto académico como completos.

## Actualización de visitas 0.4

FR-16–20 y NFR-11/12: `visits.py`, `visit_routes.py` y `tests/test_visits.py`. Se verifican autorización/destino, fechas, entrada/salida, cancelación sin ocultar pendientes, concurrencia/idempotencia, cifrado, filtros, bajas, retención y recuperación/migración. El interesado aún no validó el procedimiento real y faltan pruebas con personal del edificio. Usuarios/permisos y restricciones se incorporan en 0.5. Esta ampliación conserva modelo y datos anteriores.

## Actualización 0.5

| Requisito | Implementación | Evidencia técnica y límite |
|---|---|---|
| FR-21/22, NFR-13 | auth.py, admin_routes.py, middleware, escritorio.py | tests/test_accounts_and_restrictions.py y test_desktop_policy.py: roles, claves con sal, sesiones, bloqueo, cambio/reset, respaldo solo admin. No auditoría de penetración externa |
| FR-23 | restrictions.py, main.confirm_passage, visits.py | Restricción durante la vigencia, nueva comprobación al paso, egreso permitido, enlace externo explícito. Revisión del procedimiento con interesado pendiente |
| FR-24 | store.add_event, visits._event | Atribución real a cuenta autenticada, token de paso vinculado al operador. No reconstruye autor de datos históricos |
| FR-25 | audit.py, middleware, admin_routes.py | Cadena, truncación, retención con ancla, incidencia y conciliación. No registro certificado ni prueba contra control total del equipo |
| FR-26 | static/app.js, cameras.py | tests/frontend_smoke.cjs simula selector, permisos visuales y detección anónima. No webcam/RTSP real |
| FR-27 | report.py, ruta report.html | Reporte vacío sin precisión inventada, permiso admin; resultados de personas pendientes |
| FR-28 | app.js MediaRecorder, escritorio download handler | DOM con MediaRecorder simulado verifica exportación y descarte; captura/descarga WebM real en Qt Windows pendiente |
| NFR-14 | migrations.py, backups.py | Migraciones anteriores preservadas; recuperación mantiene cuentas/datos y elimina sesiones previas |

El ensayo del modelo y el informe académico siguen siendo necesarios: estas pantallas no reemplazan el componente de Ciencia de Datos/IA.

## Correcciones de seguridad 0.6

| Requisito | Implementación | Evidencia / pendiente |
|---|---|---|
| FR-29, NFR-18 | credentials.py, main.Passage/set_resident_pin, formulario PIN | Entrada sin PIN rechazada, hash sin secreto visible, rol/identidad, bloqueo entre capturas, baja y cambio; no PAD humano validado |
| NFR-15 | auth.py, main, runtime, app.js | Inactividad/vida máxima, máximo sesiones, bloqueo sin depender de IP, token de sesión y revocación al reinicio; inactividad humana del frontend implementada, uso real pendiente |
| NFR-16 | security.py, vision.decode_image, runtime/iniciar | Chunks sin encabezado/con longitud falsa rechazados antes de aplicación, formatos controlados y error sin secreto, cabeceras en rechazo; no pentest independiente |
| NFR-17 | file_security.py, Store, backups.py | POSIX 700/600 y enlaces rechazados; DACL Windows implementada pero ejecución real allí pendiente |
| NFR-18/migración | migrations.py esquema 5, test_schema4_upgrade | Cuentas/plantillas preservadas, sesiones revocadas, PIN sin valor por defecto; respaldos conservados |
| Fuente privada acotada | cameras.validate_source/main.connect_camera | HTTP, loopback, puertos inválidos y controles rechazados; fuente HTTP previa da error controlado; RTSP del edificio pendiente |
| Dependencias | constraints y AUDITORIA_DEPENDENCIAS*.json | Consulta de versiones conocidas; no certifica binarios nativos, todas las plataformas ni ausencia de futuras vulnerabilidades |

Pruebas: tests/test_security_hardening.py y smoke DOM de PIN. Estas medidas no reemplazan datos reales, evaluación docente, informe/defensa ni una auditoría de seguridad independiente.

## PAD 0.7: alcance vigente

| Requisito | Implementación | Evidencia / límite |
|---|---|---|
| FR-30 | PadEngine, PadSequence, analyze, PassTokens | tests/test_pad.py: contrato RGB, pesos auténticos, inferencia real sin personas, secuencia/repetición/tiempo/identidad, rechazo/incierto/ausencia, revocación; eficacia real sin medir |
| FR-31 | analyze_camera, frame/reset/disconnect | Fuente del servidor usa su captura; imagen subida no suplanta su origen; desconexión invalida evidencia; webcam/RTSP real Windows pendiente |
| FR-32 | renderPad/present/passButtons | DOM simulado muestra alerta/apto y no pide PIN; no es prueba de render Qt ni de comportamiento humano |
| FR-33 | enroll, PadTrials, rutas/reportes/JSON | PAD fallido impide alta; etiquetas/consentimiento/duplicados/fases, denominadores y no evaluables; backup y borrado; datos reales pendientes |
| NFR-19 | models/pad/manifest, migrations esquema 6 | Identidad conserva manifiesto/firma anteriores; pesos PAD verificados contra SHA-384 publicado, SHA-256 local y licencia; migración conserva datos y cierra sesiones |

FR-29 de 0.6 deja de ser la regla de operación: no hay PIN obligatorio ni campo PIN en la interfaz vigente. Las pruebas técnicas no demuestran resistencia a todas las suplantaciones ni habilitan despliegue de cerraduras.
