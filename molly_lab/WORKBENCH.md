# Molly Workbench

## Empezar sin configurar servicios externos

Abre `iniciar.bat`, o ejecuta `python server.py --open`. El servidor arranca
también una API de pedidos en un puerto local libre. Esa API usa SQLite con
datos de Ana y Bruno de prueba. No requiere cuentas, claves externas ni n8n.

El selector **Motor del lenguaje** conserva Lang y Vortex. El selector
**Entorno de ejecución** tiene tres opciones:

| Modo | Lectura del pedido actual | Envío |
|---|---|---|
| Simulado | Texto editable en memoria | Caja de salida en memoria |
| Integración | GET a la API HTTP local | Interceptado, en memoria |
| Operativo local | GET a la API HTTP local | POST al registro SQLite de entregas |

«Operativo local» significa que hay solicitudes y escritura persistente reales
en el servicio incluido. Los canales y pedidos siguen siendo de prueba. No se
conecta a WhatsApp, a una empresa ni a modelos externos. Las fuentes de estado,
catálogo y detalle de la demo conservan sus datos sintéticos originales.

## Ayuda al escribir

- **Ctrl+Espacio** o **Completar código** ofrece herramientas, variables
  inferidas y palabras del vocabulario seleccionado.
- Al escribir una llamada se muestra su firma y tipo de retorno.
- Después de una breve pausa se consulta `/api/analyze`: lexer, parser y
  `Engine.validate()` originales, sin ejecutar el programa ni cargar fuentes.
- Los diagnósticos tienen línea y columna; pulsarlos selecciona esa posición.
- El análisis adicional de tipos y audiencias es parcial y conservador.
  Un aviso no reemplaza la decisión del intérprete. No se hace una demostración
  de seguridad ni una comprobación completa de tipos.
- **Ayuda y SDK** muestra el catálogo de las herramientas instaladas y ejemplos.

La transformación de ejemplo del SDK se llama `uppercase(text)` en Lang y
`mayusculas(text)` en Vortex. Exige texto y conserva las etiquetas mediante
el intérprete original.

## Programar con bloques

En **Bloques** puedes añadir fuentes, transformaciones, valores, asignaciones,
envíos, condiciones, `while` y `for`. Las condiciones tienen ramas principal
y alternativa; los ciclos tienen un cuerpo anidado. Las declaraciones de valor
pueden tener un tipo para permitir reasignación.

Usa ↑ ↓ para ordenar con teclado o arrastra bloques. Los bloques se guardan
como borradores por variante en el almacenamiento local del navegador. Puedes
exportarlos/importarlos en JSON. **Enviar al editor** genera código en el
vocabulario actual; no lo ejecuta. El botón habitual ejecuta ese código con
el motor Python. No hay conversión automática de cualquier programa textual
a bloques ni un editor gráfico de todos los detalles de las expresiones.

Límites del constructor: 80 bloques, 12 niveles de anidamiento. Después se
aplican los límites del lenguaje. Los campos de expresión admiten Molly textual
y reciben los mismos diagnósticos que el resto del programa.

## Guardar y repetir pruebas

En **Pruebas**, el programa, datos de entrada, contexto y modo actuales se
pueden guardar con un nombre. Indica si esperas permiso/rechazo, cuántos envíos
y opcionalmente un fragmento de salida. Una ejecución completada propone sus
valores actuales como punto de partida; puedes cambiarlos antes de guardar.

Cada variante incluye ocho regresiones. Las pruebas personales se guardan
en `.data/cases.json`, con escritura atómica. Se pueden cargar, eliminar,
exportar e importar. **Ejecutar suite** compara los resultados reales e indica
las diferencias de cada prueba. Las suites no admiten el modo operativo.

Las pruebas de integración vuelven a leer el pedido persistido actual; un
cambio de ese pedido puede afectar las expectativas de contenido. Los ejemplos
incluidos de regresión usan el modo simulado para ser reproducibles.

## Pausa real y puntos de interrupción

1. Selecciona simulación o integración; abre **Depuración real**.
2. Opcionalmente escribe números de línea separados por comas.
3. **Iniciar pausa real** arranca un proceso Python y se detiene antes de la
   primera sentencia ejecutable, después del análisis previo.
4. **Ejecutar una instrucción** deja que esa sentencia ocurra y se detiene
   antes de la siguiente. Inspecciona variables, tipos, audiencias, origen,
   contexto de control, contadores y efectos ya ocurridos.
5. **Continuar** ejecuta hasta un punto de interrupción o hasta terminar.
6. **Detener** termina el proceso. No revierte efectos anteriores.

Se utiliza `sys.settrace()` sobre la función `execute()` del intérprete real;
no se reimplementa la evaluación ni se convierte una traza terminada en una
pausa ficticia. Se avanza por sentencias, no por cada subexpresión o llamada
Python. Las ramas y los cuerpos de los ciclos también generan pausas.
Los valores de la inspección se presentan con profundidad y tamaño acotados.

Límites: una sesión activa, 180 segundos por sesión y 7 segundos por avance.
Si una instrucción falla, el resultado del error aparece sin ejecutar las
posteriores. Al finalizar, el resultado se muestra en el flujo principal.

## Pruebas de conexión en caliente

En **Conexión y n8n**, cambia el pedido y pulsa **Guardar pedido en la API
local**. Después ejecuta el programa en integración: el texto mostrado debe
venir de esa consulta HTTP, no del campo del pedido simulado.

Puedes provocar HTTP 500, una respuesta lenta o un contrato incorrecto. La
tabla indica método, intento y estado. El cliente tiene un timeout corto y
reintenta una vez las lecturas; nunca reintenta automáticamente los POST.
La API de entregas usa claves de idempotencia para evitar duplicar una misma
entrega identificada. Autorizaciones y audiencias originales siguen activas:
un bloqueo de lectura ocurre antes de consultar la API, y un envío prohibido
no llama al endpoint de entregas.

## n8n, cuando quieras utilizarlo

No se instala ni se inicia n8n automáticamente. Descarga la plantilla de la
variante desde **Conexión y n8n** e impórtala en tu instancia. Usa un disparador
manual y un nodo HTTP Request, configurados según las opciones documentadas:

- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
- https://docs.n8n.io/workflows/export-import/

La plantilla requiere n8n ejecutándose en el mismo equipo y acceso al puerto
del laboratorio. Dentro de Docker, `127.0.0.1` apunta al contenedor: ese caso
requiere configurar explícitamente la red; el laboratorio no cambia su enlace
local ni abre puertos públicos por su cuenta.

Configura una credencial **Header Auth** con nombre de cabecera
`Authorization` y valor `Bearer <token>`. El botón **Mostrar credencial local**
permite obtenerla; cambia al reiniciar el servidor y no se incluye en los ZIP,
las plantillas ni el historial. La URL descargada refleja el puerto actual.

`POST /api/integration/run` usa la identidad de Ana fijada por el anfitrión
autenticado; ignora identidades enviadas en el JSON. Devuelve estado,
contadores, identificador y huella, **sin devolver pedido, outbox, código,
errores detallados ni trazas privadas**. Las acciones protegidas permanecen
dentro de Molly. Un nodo n8n posterior no recibe esos datos para reenviarlos
sin sus etiquetas.

Un `request_id` opcional permite recuperar el resultado de una petición ya
realizada. Se conservan hasta 200 resultados de integración en memoria; las
entregas operativas locales se identifican también en SQLite. Reutilizar el
identificador con otro programa produce conflicto. Esto no implementa una
garantía universal de ejecución exactamente una vez para servicios externos.

## Estructura

- `sdk.py`: contratos tipados, registro y cliente HTTP acotado.
- `editor_support.py`: diagnósticos sin ejecución, sobre el AST original.
- `debugger.py`: pausa real dentro del proceso del intérprete.
- `orders_api.py`: servicio HTTP con pedidos y entregas SQLite.
- `studio.py`: API de pruebas, conexión, n8n y sesiones de depuración.
- `studio.js`, `studio.css`: herramientas de la interfaz.
- `test_studio.py`: pruebas de integración de las funciones nuevas.
- `examples/sdk_example.py`: ejemplo de registro de conectores.
- `integrations/`: plantillas n8n con puerto predeterminado 8765.
- `.data/`: datos locales de esta instalación; excluidos de Git y del paquete.

## Verificar

`verificar.bat` ejecuta los controles HTTP originales y la suite nueva.
También puedes usar `python verificar.py` y `python test_studio.py`.
Las suites originales de ambos lenguajes siguen ejecutándose desde cada raíz
con `python -m unittest -q`. No se modifican sus motores para habilitar el SDK,
los bloques, los conectores o el depurador.
