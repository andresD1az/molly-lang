# Verificación de la integración · 20 de octubre de 2026

## Ampliación Workbench

- `test_studio.py`: 8 pruebas nuevas correctas, con subcasos en Lang y Vortex.
  Incluyen diagnóstico sin efectos, contratos del SDK, conservación de etiquetas,
  GET/POST reales, fallos HTTP y reintentos, suites persistentes, importación
  atómica, autenticación de n8n, identidad ligada al anfitrión y respuestas sin
  datos privados, idempotencia local y depuración con puntos de interrupción.
- Depurador en navegador: pausa antes de línea 1 con cero lecturas; un avance
  muestra el pedido con audiencia y una lectura, sin envíos; continuar termina
  con el resultado del motor original.
- Constructor visual: fuente → transformación → envío generado y ejecutado.
  Se añadió un bloque `for` con un envío anidado: el motor produjo cuatro envíos
  (uno inicial y tres iteraciones), coincidentes con las trazas.
- Vortex en navegador (Workbench, puerto 8767): autocompletado de
  `pedido_actual`, generación de tres bloques y ejecución autorizada. Depuración
  verificada antes de línea 1 (cero lecturas), antes de línea 2 (una lectura y
  variable con audiencia `cliente:mitico:ana`) y final (un envío).
- Editor: un programa que envía el pedido a web muestra un aviso de flujo en
  línea/columna antes de ejecutar.
- Pruebas desde interfaz: guardar una prueba personal y ejecutar la suite
  inglesa dio 9/9 resultados correctos.
- Conexión desde interfaz: actualizar el pedido en SQLite y ejecutar integración
  devolvió el texto actualizado por GET HTTP 200. En modo operativo local se
  observó GET 200 y POST 200 al registro persistente de entregas.

La API de pedidos es un servicio HTTP real local con datos de prueba. No se
instaló n8n ni se afirmó haber ejecutado una instancia de n8n: se verificó el
contrato HTTP de la pasarela y las plantillas importables en JSON. El acceso a
un sistema externo se omitió conforme a la indicación del usuario.

Recorrido probado: editor del navegador → `/api/run` → proceso Python →
`demo.make_engine()` y `Engine.run()` originales → JSON → flujo y destinos.

## Evidencia

- `python verificar.py`: 34 comprobaciones HTTP correctas con las dos variantes.
- Ocho escenarios por variante: permitido, web, modelo, otro cliente, rama
  privada, público, sintaxis y tipos. Se comprueban salidas, contadores, tokens,
  AST y huella del archivo del motor utilizado.
- Casos adicionales: cambio de pedido, contexto denegado, dos destinos antes
  de error de tipo, variantes/entradas inválidas y origen HTTP no permitido.
- Exportación: cadena de las últimas 20 entradas consistente; una modificación
  del resultado sin recalcular la cadena es detectada por el verificador.
- Timeout: un proceso que supera el presupuesto es detenido y una ejecución
  posterior puede iniciar normalmente.
- Arranque desde el checkout Vortex: detecta Vortex por defecto, encuentra
  ambos motores y ejecuta el programa nativo con destino `whatsapp_actual`.
- Suites originales: 61/61 en `molly-lang` y 64/64 en `molly-vortex`.
- `node --check app.js` y compilación de los módulos Python: correctos.

## Navegador local

Probado en Brave con backend real en `http://127.0.0.1:8766`:

- Lang: pedido privado al cliente → mensaje sintético y un envío.
- Vortex: cambio de vocabulario/contexto; pedido privado al cliente → mensaje
  en español y traza original `ANÁLISIS`, `LECTURA`, `TRANSFORMACIÓN`, `ENVÍO`.
- Vortex: pedido privado a web → bloqueo y cero envíos.
- Vortex: catálogo público a web → publicación sintética permitida.
- Inspección de AST y tokens originales en sus pestañas.
- Código editado con dos envíos públicos: un mensaje en chat y otro en web,
  destinos separados y dos llamadas efectivas.

No se llamó a servicios de WhatsApp, LLM o publicación web. Las animaciones
reproducen la traza posterior a la ejecución. La cadena de hashes no tiene
firma ni garantiza autenticidad frente a una reescritura completa.
