# Repositorio y distribución

Repositorio público del estudiante: [TrainPulga/acceso-residencial](https://github.com/TrainPulga/acceso-residencial). La rama principal publica código, modelos licenciados, pruebas, documentación y workflows; no incluye datos personales, credenciales, entornos de Python ni clips reales.

El repositorio está publicado como código fuente para que el profesor pueda consultar archivos, historia y workflows. No subir el ZIP como único contenido. En futuras actualizaciones comprobar que no se copien `data`, `backups`, `.env`, videos, claves ni informes con datos personales. La carpeta de datos del escritorio está fuera del programa y no debe adjuntarse.

El workflow tests.yml ejecutó correctamente en el commit `6b67b70d586c1d920d1424b2173809f63c42da65` el 12/11/2026: [ejecución de GitHub Actions](https://github.com/TrainPulga/acceso-residencial/actions/runs/43315212789). Pasaron los jobs Python 3.12 en Ubuntu y Windows; el job Windows instaló dependencias de escritorio. Ambos jobs descargaron los modelos con verificación de hash, ejecutaron `pytest` y `npm test` con Node 24. Esto valida el pipeline automatizado para ese commit; no verifica cámara/renderer físico ni desempeño con personas.

windows-package.yml es manual: Actions → Preparar escritorio Windows → Run workflow. Intenta compilar con crear_ejecutable.py y adjuntar la carpeta dist completa como artefacto. Esa receta requiere prueba en Windows, incluyendo el renderer Qt, cámara, recursos y permisos. No produce un instalador firmado ni demuestra funcionamiento solo por terminar una compilación. Esta entrega incluye código fuente, no un .exe Windows generado.

Para pruebas locales de Python: instalar requirements-dev.txt, ejecutar `python descargar_modelos.py` y luego `python -m pytest -q`. Para el DOM simulado: Node compatible con package.json, `npm ci --ignore-scripts` y `npm test`. Node/jsdom solo son herramientas de desarrollo y no se necesitan para abrir la aplicación de escritorio. El smoke de interfaz no sustituye usar webcam, RTSP ni Qt en el equipo destino.

La memoria final debe registrar datos/método/resultados reales, límites, aporte individual y uso de herramientas/asistencia según la política docente. No incluir fotografías de vecinos en un repositorio público como evidencia. Los modelos públicos y su licencia no autorizan publicar datos biométricos del edificio.
