# Estado 0.7 · 17 de octubre de 2026

## Implementado y alcance vigente

Cámara de acceso seleccionable, reconocimiento de residentes con YuNet/SFace y PAD RGB mediante anti-spoof-mn3. No se pide PIN. Para emitir confirmación se requieren calidad, coincidencia, tres capturas distintas que superen PAD, misma identidad/fuente/sesión y separación temporal. Error, incertidumbre, posible presentación o repetición no habilita registro. Una captura posterior que falla invalida el token anterior. Fuentes del servidor usan su captura, no imágenes subidas atribuidas a ellas.

Alta con control PAD; semáforo textual de comprobación/alerta/incierto/superado; registro manual de pasos con cruce observado, sin apertura de puertas. PAD aporta una clasificación del piloto, no certifica presencia física ni identidad. El campo heredado liveness_verified sigue falso; pad.passed expresa la regla implementada.

Se conservan cuentas, roles, visitas/mantenimiento, restricciones, auditoría, selector webcam, fuentes USB/RTSP privadas, vistas complementarias anónimas, clip manual webcam y evaluación de reconocimiento. Se agrega evaluación PAD por captura, etiquetas humanas, datos cifrados, métricas con denominadores/no evaluables, exportación JSON y borrado. No hay seguimiento nominal entre cámaras.

Esquema 6 con respaldo, sesiones revocadas y datos anteriores conservados. No se modifica el manifiesto/firma de identidad ni se requiere registrar nuevamente todos los rostros. Los hashes PIN heredados se conservan sin controlar el acceso. Pesos PAD y licencia MIT incluidos, sin dependencias Python nuevas ni dataset de terceros.

## Evidencia técnica ejecutada

170 pruebas Python aprobadas (42,66 s) con un aviso de deprecación Starlette/httpx. El módulo PAD incluye 21 casos contando parametrización; se volvió a ejecutar después de ampliar el reporte entre capturas evaluables (21 aprobados en 5,01 s). Hay datos sintéticos de lógica, verificación del contrato/preprocesamiento y ejecución de pesos reales con píxeles artificiales; no son mediciones de personas o ataques humanos.

SHA-384 de los pesos PAD coincide con la huella publicada y se incluye SHA-256 local. Inferencia real del ONNX verificada, sin trasladar métricas del autor al edificio. HTTP real 0.7/esquema 6, sesión, modelos de identidad y PAD cargados, sin PIN obligatorio y cierre controlado comprobados. DOM simulado: roles/login/logout/limpieza, estados PAD, registro sin PIN, selector webcam, observación y clips. 177 IDs únicos y referencias literales verificados. No es render Qt ni cámara real.

Se conservan restricciones de versiones y consulta de dependencias del mismo día: no se agregaron paquetes a los 25 fijados. Los resultados de consultas de vulnerabilidades conocidas no certifican el código propio ni los binarios Qt/FFmpeg.

## Pendiente y límites

Eficacia de PAD con personas presentes, fotos impresas, fotos/videos en pantallas y condiciones del piloto; calibración/prueba independiente; errores de identidad; Windows/renderer/cámaras reales; DACL Windows; capacidad/latencia reales; revisión de instalación y seguridad independiente. Puede haber ataques aceptados y personas reales rechazadas. La secuencia temporal no autentica el hardware ni evita toda inyección de imágenes/cámaras virtuales, máscaras o deepfakes.

No se entrega ejecutable Windows compilado, cerraduras, apertura física, detección automática de dirección/cruce, búsqueda nominal entre cámaras ni garantía de compatibilidad universal o capacidad ilimitada. Sin medición local no se declara la aplicación apta para controlar puertas.

Para el Proyecto Integrador faltan validar problema/interesado/recorte docente, autorizaciones y experimento, informe con resultados reales, repositorio propio limpio y defensa. El software y los tests no equivalen a aprobación académica. PAD_0_7.md explica qué medir; SRS_SSOT y MATRIZ_CUMPLIMIENTO registran el alcance.
