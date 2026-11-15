"""Small typed connector SDK over either unmodified Molly engine.

Sources are context-bound (zero Molly arguments, matching the current engines).
Transforms have typed arguments. Authority always belongs to host callbacks.
"""
from dataclasses import dataclass, field
from collections.abc import Mapping
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler


def matches(value, kind):
    return {'any': lambda: True, 'str': lambda: type(value) is str,
            'int': lambda: type(value) is int, 'float': lambda: type(value) in (int, float),
            'bool': lambda: type(value) is bool, 'record': lambda: isinstance(value, Mapping),
            'list': lambda: isinstance(value, (list, tuple)), 'null': lambda: value is None}.get(kind, lambda: False)()


@dataclass(frozen=True)
class Parameter:
    name: str
    kind: str = 'any'


@dataclass(frozen=True)
class Tool:
    name: str
    category: str
    run: object
    description: str
    output: str = 'any'
    parameters: tuple = ()
    authorize: object = None
    audience: object = None
    identity: object = None
    processor: str | None = None


class Toolkit:
    def __init__(self):
        self.tools = {}

    def add(self, tool):
        if not tool.name.isidentifier() or tool.name in self.tools:
            raise ValueError('Nombre de herramienta inválido o duplicado')
        if tool.category not in ('source', 'transform', 'sink'):
            raise ValueError('Categoría de herramienta inválida')
        if tool.category == 'source' and (tool.parameters or not tool.authorize or not tool.audience):
            raise ValueError('Las fuentes actuales requieren contexto, authorize y audience; no argumentos Molly')
        if tool.category == 'sink' and not tool.identity:
            raise ValueError('El destino necesita identidad verificada por el anfitrión')
        self.tools[tool.name] = tool
        return self

    def install(self, module, engine):
        for tool in self.tools.values():
            def checked(ctx, *args, t=tool):
                if len(args) != len(t.parameters):
                    raise module.MollyError('Type' if hasattr(module, 'MAX_PROGRAM') else 'Tipo',
                                            t.name + ': número de argumentos incorrecto')
                if any(not matches(v, p.kind) for v, p in zip(args, t.parameters)):
                    raise module.MollyError('Type' if hasattr(module, 'MAX_PROGRAM') else 'Tipo',
                                            t.name + ': el argumento no coincide con el contrato')
                output = t.run(ctx, *args)
                if not matches(output, t.output):
                    raise ValueError('La respuesta no coincide con el contrato')
                return output
            if tool.category == 'source':
                engine.sources[tool.name] = module.Source(checked, tool.authorize, tool.audience)
            elif tool.category == 'transform':
                engine.transforms[tool.name] = module.Transform(checked, len(tool.parameters), tool.processor)
            else:
                engine.sinks[tool.name] = module.Sink(tool.identity, tool.run)
        return engine

    def describe(self):
        return [{'name': t.name, 'category': t.category, 'description': t.description,
                 'output': t.output, 'parameters': [{'name': p.name, 'type': p.kind} for p in t.parameters],
                 'processor': t.processor} for t in self.tools.values()]


def catalog(engine, profile):
    output = []
    for name in engine.sources:
        record = name in ('order_details', 'detalle_pedido')
        output.append({'name': name, 'category': 'source', 'parameters': [],
                       'output': 'record' if record else 'str',
                       'description': 'Lee datos del contexto; autorización antes de la consulta.'})
    for name, t in engine.transforms.items():
        output.append({'name': name, 'category': 'transform', 'output': 'str',
                       'parameters': [{'name': 'value', 'type': 'any'} for _ in range(t.arity)],
                       'processor': t.processor,
                       'description': 'Procesador externo sujeto a permisos.' if t.processor else 'Transformación local; conserva etiquetas.'})
    for name in engine.sinks:
        output.append({'name': name, 'category': 'sink', 'output': 'null',
                       'parameters': [{'name': 'value', 'type': 'any'}],
                       'description': 'Comprueba destinatario y contexto de control antes del envío.'})
    return output


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass
class JsonHTTP:
    """Trusted fixed URL, short timeout, bounded JSON and GET-only retry.

Never construct this URL from a model-produced program. POST is never retried.
"""
    url: str
    token: str
    timeout: float = 0.5
    retries: int = 1
    events: list = field(default_factory=list)

    def call(self, method='GET', body=None, request_id=None):
        headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}
        if request_id:
            headers['Idempotency-Key'] = request_id
        for attempt in range(1 + (self.retries if method == 'GET' else 0)):
            try:
                request = Request(self.url, data=None if body is None else json.dumps(body).encode(),
                                  method=method, headers=headers)
                with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                    raw = response.read(65537)
                    if len(raw) > 65536:
                        raise ValueError('Respuesta HTTP demasiado grande')
                    result = json.loads(raw)
                    self.events.append({'operation': method, 'attempt': attempt + 1, 'status': response.status})
                    return result
            except HTTPError as error:
                self.events.append({'operation': method, 'attempt': attempt + 1, 'status': error.code})
                if error.code < 500 or attempt >= self.retries or method != 'GET':
                    raise RuntimeError('El servicio devolvió un error HTTP') from None
            except (URLError, TimeoutError, socket.timeout):
                self.events.append({'operation': method, 'attempt': attempt + 1, 'status': 'timeout-or-connection'})
                if attempt >= self.retries or method != 'GET':
                    raise RuntimeError('No se pudo completar la conexión') from None
