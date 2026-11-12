# Orientación para agentes de revisión y desarrollo

Este repositorio corresponde a un Proyecto Integrador individual de Ciencia de Datos e IA. Leé primero `README.md` y `docs/GUIA_EVALUACION.md`; para especificación, trazabilidad y evidencia ampliada, consultá `docs/SRS_SSOT.md`, `docs/MATRIZ_CUMPLIMIENTO.md` y `docs/ESTADO_ENTREGA.md`.

## Reglas de interpretación

- Evaluá la implementación en el código y la evidencia disponible. Una descripción en Markdown, un test sintético o un pipeline exitoso no prueban funcionamiento con residentes, cámara física, ataques ni aceptación del edificio.
- Mantené separados: detección de rostros, comparación de identidad, control PAD, observación de un cruce y apertura física. El sistema no controla cerraduras.
- Los modelos de identidad y PAD son preentrenados. No atribuyas al estudiante su entrenamiento ni afirmaciones de precisión que no estén respaldadas por ensayos locales.
- No infieras que un rostro desconocido es intruso, que un score PAD es una probabilidad calibrada, ni que un paso observado automáticamente se deduce de una coincidencia.
- No inventes interesados, autorización, datos, resultados, requisitos docentes, cifras de rendimiento ni viabilidad comercial. Cuando falte evidencia, indicá qué dato hace falta.
- Los resultados empíricos y archivos locales de participantes son sensibles. No solicites, reproduzcas ni agregues al repositorio fotos, videos, bases, exportaciones identificables, claves o credenciales.
- La asistencia de IA está prevista y documentada en `docs/ENTREVISTA_Y_DEFENSA.md`; no sustituyas la explicación del aporte individual por una afirmación genérica de autoría.

## Reproducción de las comprobaciones

Usá Python 3.12 y seguí el bloque de reproducción de `README.md`. Los pesos ONNX se descargan mediante `python descargar_modelos.py`, que valida hashes. Las pruebas de interfaz requieren Node compatible con `package.json` y `npm ci --ignore-scripts && npm test`. El workflow `.github/workflows/tests.yml` corre en Ubuntu y Windows.

La ejecución de tests es una comprobación de software, no un piloto biométrico. El workflow de empaquetado `.github/workflows/windows-package.yml` es manual y no debe describirse como compilación publicada salvo que exista una ejecución verificable.

## Cambios

Antes de modificar el flujo de identificación, PAD, permisos, persistencia cifrada, auditoría o migraciones, inspeccioná los módulos correspondientes y sus pruebas. Añadí o ajustá pruebas de regresión y actualizá SRS/matriz/estado cuando cambie un requisito o su evidencia. No alteres datos de aplicación del usuario: se guardan fuera del repositorio.
