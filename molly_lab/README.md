# Molly Security Lab · Lang + Vortex

Aplicación local para ejecutar los dos intérpretes originales desde un editor,
inspeccionar sus tokens, AST y trazas, y reproducir los envíos a WhatsApp/web
simulados. Adaptado del ZIP `Molly_Security_Lab_Real.zip` proporcionado por el autor.

**Ampliación Workbench:** autocompletado y diagnósticos, SDK tipado, bloques
anidados, pruebas persistentes, depuración real y API local HTTP/SQLite.
Consulta [WORKBENCH.md](WORKBENCH.md) para los recorridos completos.

## Iniciar

Requiere Python 3.10 o superior; no instala dependencias.

- Windows: abrir `iniciar.bat`. Se abre el navegador cuando el servidor está listo.
- Terminal: `python server.py --open`, desde esta carpeta.
- Linux/macOS: `sh iniciar.sh`.
- Puerto ocupado: `python server.py --port 8766 --open` o `iniciar.bat --port 8766`.

El servidor escucha únicamente en `127.0.0.1`. Abrir la dirección que imprime;
no abrir `index.html` directamente. Detener con Ctrl+C en la terminal.

## Motores y repositorios

Esta misma carpeta `molly_lab` está integrada en las dos copias de trabajo:

- `molly-lang/molly_lab`, junto al motor con vocabulario inglés.
- `Molly_Boceto_Funcional/molly-boceto/molly_lab`, en el checkout cuyo remoto es
  `andresD1az/molly-vortex`, con vocabulario temporal en español.

El laboratorio detecta la variante del repositorio desde el que arranca y busca
la otra en carpetas cercanas. También funciona con solo una variante instalada;
el selector ofrece únicamente los motores encontrados. Para rutas diferentes:

```powershell
python server.py --english-root "C:\ruta\molly-lang" --vortex-root "C:\ruta\molly-vortex"
```

Alternativamente: `MOLLY_ENGLISH_ROOT` y `MOLLY_VORTEX_ROOT`. Las rutas las configura
el anfitrión; una petición del navegador no puede elegir un archivo Python.

El selector cambia ejemplos, nombres de herramientas, contexto inicial (`acme`
o `mitico`) y motor. Cada variante conserva su borrador mientras la página está
abierta. El texto del código no se traduce automáticamente.

## Flujo real

```text
Editor → POST /api/run → proceso Python independiente
       → demo.make_engine() del repositorio seleccionado
       → Engine.run(código, Context(...))
       → tokens + AST + trace nativos + llamadas de adaptadores
       → respuesta JSON → reproducción visual posterior
```

No se ha reimplementado el lexer, parser, intérprete ni las decisiones de
permisos en JavaScript. Los casos se obtienen de `demo.CASES`, no de una
traducción textual. La versión de Vortex se lee de `pyproject.toml` porque ese
módulo no expone `__version__`.

Cada ejecución importa solo un `molly.py` y su `demo.py` en un proceso nuevo.
Esto evita la colisión de nombres entre repositorios y el estado compartido del
límite de recursión de Python. Los motores originales no se modifican.

Se envuelven los adaptadores sintéticos para contabilizar sus invocaciones
efectivas y registrar el destino de cada mensaje. El pedido configurable
sustituye únicamente el cargador de `current_order` / `pedido_actual`; se
conservan `authorize` y `audience` originales. `counters` cuenta todas las
lecturas efectivas, incluidas estado/catálogo/detalle; `raw_counters` conserva
los contadores de la demo, que no contabiliza todas esas fuentes.

La traza, los errores, los tokens y los nombres del AST se conservan en su
idioma original. Solo la presentación normaliza los eventos para iluminar
los mismos bloques. La vista de flujo es resumida; el orden completo está en
las trazas. Al editar código, contexto o pedido se invalida el resultado previo.

## Qué se simula

- Pedidos y catálogo de prueba.
- WhatsApp y web: listas locales, sin mensajes ni publicaciones externas.
- `draft` / `redactar`: añade un saludo localmente, sin llamar a un LLM.
- Modelo externo: adaptador sintético cuya invocación puede ser bloqueada.
- Contexto: controles del laboratorio que simulan una sesión, no autenticación.

La animación reproduce eventos después de completar `Engine.run`. No pausa
el intérprete real ni representa callbacks en vivo. El escenario con texto
hostil prueba conservación de etiquetas, no la resistencia de un LLM real.

## Historial comprobable

El servidor mantiene las últimas 20 ejecuciones en memoria. `Descargar historial
JSON` exporta resultados, contexto, código y huellas SHA-256 del motor y demo.
Cada entrada se enlaza con la anterior mediante SHA-256. Verificar sin servidor:

```powershell
python verificar.py --history "C:\ruta\molly-lab-history.json"
```

Se comprueba la consistencia del contenido y los enlaces. No hay firmas,
persistencia, sello de tiempo confiable ni custodia externa; alguien puede
reescribir el archivo completo y recalcular las huellas. No equivale a C4 de
la propuesta de investigación. Reiniciar el servidor borra la sesión.

## Verificar integración

`python verificar.py` levanta un servidor temporal local y
comprueba: configuración, página/JS, ocho escenarios por variante, entradas
editadas, contexto denegado, efectos parciales y destinos separados, peticiones
inválidas, historial alterado y timeout del proceso. Con ambas variantes son
34 comprobaciones HTTP, además de las comprobaciones de cadena y timeout.

`python test_studio.py` verifica las nuevas funciones. `verificar.bat` ejecuta
ambos grupos. Las pausas del depurador tienen presupuestos propios, descritos
en WORKBENCH.md; el límite de 6 segundos corresponde a la ejecución normal.

Desde cada raíz: `python -m unittest -q` ejecuta la suite original del lenguaje.

## Límites del laboratorio

Una ejecución normal a la vez y una sesión de depuración independiente,
petición de hasta 60 KB, 6 segundos por proceso normal,
512 MiB de memoria por proceso y respuesta de hasta 2 MiB. En Windows se aplica
un Job Object; en sistemas POSIX se usa `resource`. Si no puede aplicar el
presupuesto, el proceso falla de forma explícita. Esto no convierte al proceso
en un sandbox de seguridad frente a adaptadores Python maliciosos.

Los adaptadores y archivos Python locales siguen siendo confiables. Los
presupuestos contienen la demo; no reparan la expansión de estructuras dentro
de los motores. Los mensajes anteriores a un error no se revierten. Este
laboratorio no demuestra seguridad general, cumplimiento legal ni eficacia
comparativa frente a otras defensas.
