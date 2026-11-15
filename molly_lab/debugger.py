"""Break before real execute() instructions using CPython tracing in the worker."""
import json
from pathlib import Path
import sys


def preview(value, depth=0):
    if depth > 3:
        return '…'
    if value is None or type(value) in (bool, int, float):
        return value
    if isinstance(value, str):
        return value[:250] + ('…' if len(value) > 250 else '')
    if isinstance(value, (list, tuple)):
        return [preview(v, depth + 1) for v in value[:8]] + (['…'] if len(value) > 8 else [])
    if hasattr(value, 'items'):
        return {str(k): preview(v, depth + 1) for k, v in list(value.items())[:8]}
    return '<' + type(value).__name__ + '>'


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


class Debugger:
    def __init__(self, module, engine, counters, deliveries, breakpoints=()):
        self.file = str(Path(module.__file__).resolve())
        self.line = next(i for i, line in enumerate(Path(self.file).read_text(encoding='utf-8').splitlines(), 1)
                         if line.strip() == 'if node.kind == "bind":')
        self.engine, self.counters, self.deliveries = engine, counters, deliveries
        self.breakpoints = set(breakpoints)
        self.continuing = False
        self.type_of = getattr(module, 'type_of', getattr(module, 'tipo_de', None))

    def trace(self, frame, event, arg):
        if event != 'line' or frame.f_code.co_filename != self.file or frame.f_code.co_name != 'execute' or frame.f_lineno != self.line:
            return self.trace
        node = frame.f_locals.get('node')
        if node is None or self.continuing and node.token.line not in self.breakpoints:
            return self.trace
        scope = frame.f_locals.get('scope')
        variables = {}
        while scope is not None:
            for name, slot in scope.slots.items():
                if name not in variables:
                    v = slot.value
                    variables[name] = {'data': preview(v.data), 'type': self.type_of(v.data),
                                       'audience': None if v.audience is None else sorted(v.audience),
                                       'origin': list(v.origin)}
            scope = scope.parent
        pc = frame.f_locals.get('pc')
        emit({'debug_event': 'paused', 'line': node.token.line, 'column': node.token.column,
              'instruction': node.kind, 'name': node.token.text, 'variables': variables,
              'pc': None if pc is None or pc.audience is None else sorted(pc.audience),
              'trace': self.engine.trace[-300:], 'counters': dict(self.counters),
              'deliveries': list(self.deliveries)})
        command = json.loads(sys.stdin.readline())
        if command.get('command') not in ('step', 'continue'):
            raise SystemExit('debugger-stopped')
        self.continuing = command['command'] == 'continue'
        return self.trace

    def start(self):
        sys.settrace(self.trace)

    def stop(self):
        sys.settrace(None)
