# Repositorio y distribución

El ZIP contiene el código, modelos licenciados, pruebas, documentación y workflows. No contiene datos personales, credenciales, entornos de Python ni clips reales. No se creó ni se publicó un repositorio nuevo desde esta entrega; debe usarse un repositorio propio del estudiante, no el de su compañera.

Crear un repositorio vacío y subir el contenido de la carpeta Acceso_Residencial, incluyendo .github y .gitignore. Evitar subir el ZIP como único contenido: el profesor necesita consultar el código y documentación. Comprobar antes que no se haya copiado data, backups, .env, videos, claves ni informes con datos personales. La carpeta de datos del escritorio está fuera del programa y no debe adjuntarse.

El workflow tests.yml prepara Python 3.12 y ejecuta pytest en Linux/Windows; también ejecuta la comprobación de interfaz con Node/jsdom. Las pruebas de políticas Qt solo se ejecutan cuando está disponible PySide6. Aquí no se ejecutaron workflows remotos; no presentar un archivo YAML como CI aprobada.

windows-package.yml es manual: Actions → Preparar escritorio Windows → Run workflow. Intenta compilar con crear_ejecutable.py y adjuntar la carpeta dist completa como artefacto. Esa receta requiere prueba en Windows, incluyendo el renderer Qt, cámara, recursos y permisos. No produce un instalador firmado ni demuestra funcionamiento solo por terminar una compilación. Esta entrega incluye código fuente, no un .exe Windows generado.

Para pruebas locales de Python: instalar requirements-dev.txt y ejecutar python -m pytest -q. Para el DOM simulado: Node compatible con package.json, npm ci --ignore-scripts y npm test. Node/jsdom solo son herramientas de desarrollo y no se necesitan para abrir la aplicación de escritorio. El smoke de interfaz no sustituye usar webcam, RTSP ni Qt en el equipo destino.

La memoria final debe registrar datos/método/resultados reales, límites, aporte individual y uso de herramientas/asistencia según la política docente. No incluir fotografías de vecinos en un repositorio público como evidencia. Los modelos públicos y su licencia no autorizan publicar datos biométricos del edificio.
