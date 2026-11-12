# Evaluar sin inventar precisión

**Actualización 0.2:** la forma más accesible es la sección Evaluación académica del panel. El protocolo vigente está en [PLAN_VALIDACION.md](PLAN_VALIDACION.md). Este documento conserva la alternativa offline con imágenes voluntarias locales. Las cifras históricas de pruebas técnicas al final corresponden a 0.1; la verificación actual está en VERIFICACION_TECNICA.json.

Los modelos preentrenados no garantizan el resultado en este edificio. El umbral publicado por un fabricante en otro benchmark no es una probabilidad ni una garantía de seguridad. El prototipo fija umbral/margen **provisionales** de 0,50/0,08 para una demostración sin cerradura.

## Datos propios necesarios

Participantes adultos voluntarios y autorizados. Dar de alta a algunos y reservar otros como no inscritos. Evitar muestras públicas de desconocidos, rostros de redes sociales o datos de residentes que no participan. Conservar únicamente lo acordado, usando identificadores como P01 en los experimentos y almacenando la correspondencia por separado.

Capturar alta y pruebas en sesiones diferentes. Una misma foto, recorte o variante no puede aparecer en ambas. Separar calibración/prueba antes de ajustar parámetros. Variar iluminación, distancia, orientación y accesorios de forma documentada. Para evaluar apertura física habría que estudiar también ataques con fotos/videos y personas parecidas; el MVP no implementa PAD ni autoriza aperturas.

## Estructura del manifiesto

El siguiente JSON es **un ejemplo de formato, no un dataset ni resultados**. Las rutas deben corresponder a archivos de voluntarios autorizados en la máquina local:

```json
{
  "consent_confirmed": true,
  "gallery": [
    {"id": "P01", "session": "alta-dia1", "images": ["alta/P01_a.jpg", "alta/P01_b.jpg", "alta/P01_c.jpg"]}
  ],
  "probes": [
    {"id": "T01", "expected_id": "P01", "session": "prueba-dia2", "image": "prueba/P01.jpg"},
    {"id": "T02", "expected_id": null, "session": "prueba-dia2", "image": "prueba/no_inscrito.jpg"}
  ]
}
```

Ejecutar:

```
python evaluar_piloto.py RUTA/manifest.json --output RUTA/evaluacion.json
```

El script rechaza imágenes idénticas entre muestras, exige IDs y sesiones coherentes y calcula resultados **solo de las capturas aportadas**. No acredita por sí solo independencia entre sesiones ni consentimiento válido: requiere diseño y supervisión del experimento. El manifiesto y las fotos contienen datos personales; no subirlos a un repositorio público.

## Métricas que importan

- Identificación correcta de inscritos, rechazos y asignaciones a la persona equivocada.
- Aceptación indebida de personas no inscritas, con denominador de intentos y tamaño de galería explícitos.
- Rechazos por imagen no apta, personas múltiples, ambigüedad y desconocidos.
- Latencia mediana/p95 bajo cámaras y cargas concretas, incluyendo captura/transmisión en la prueba integral.
- Por separado: falsos eventos/direcciones, pasos omitidos y duplicados cuando se implemente cruce automático.
- Usabilidad y procedimiento alternativo de acceso, comparados con la solución actual.

No usar solo exactitud global con predominio de casos fáciles. Cero errores en una muestra pequeña no significa riesgo cero. Las distintas capturas de una persona no son sujetos independientes: estimar incertidumbre agrupando por participante/sesión. No mezclar el conjunto usado para elegir el umbral con la prueba final.

Para evaluar diferencias de desempeño, empezar por condiciones de captura y dispositivos. No inferir etnia, salud u otros atributos sensibles desde el rostro. Cualquier análisis adicional de grupos necesita justificación, datos voluntarios y autorización adecuada.

## Pruebas técnicas de esta entrega

38 casos automatizados aprobados en Python 3.12/Linux: autenticación, origen/host, consentimiento declarado, borrado, cifrado, desconocidos/ambigüedad con vectores sintéticos, permisos de paso de un solo uso, duplicados, retención y fuentes privadas. Dos modelos auténticos cargados, escena vacía rechazada y grafo de reconocimiento/alineación ejecutado con píxeles artificiales sin identidad humana.

Las pruebas con vectores sintéticos comprueban el software, **no** el reconocimiento de humanos. No se hicieron todavía pruebas con vecinos, cámaras IP del edificio, cerraduras o anti-suplantación. El lanzador Windows debe verificarse en la computadora del estudiante.
