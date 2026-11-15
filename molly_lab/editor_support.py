"""Diagnostics over the real parser/validator; no execution or adapter reads."""
from worker import analyze, install_sdk


def diagnose(m, demo, info, request):
    code = request.get('code', '')
    if not isinstance(code, str) or len(code) > 12000:
        raise ValueError('Código no válido')
    engine, counters, _ = demo.make_engine()
    install_sdk(m, engine, info['id'])
    ctx = m.Context(request.get('tenant', info['tenant']), request.get('subject', 'ana'))
    tokens, errors = m.lex_all(code)
    parser = m.Parser(tokens)
    program = parser.parse(raise_errors=False)
    errors += parser.errors
    if not errors:
        try:
            engine.validate(program)
        except m.MollyError as error:
            errors += error.errors if isinstance(error, m.MollyErrors) else [error]
    diagnostics = [{**e.as_dict(), 'severity': 'error'} for e in errors]
    tools = {t['name']: t for t in info['tools']}
    variables = {}
    literal = getattr(m, 'literal_value', getattr(m, 'valor_literal', None))
    type_of = getattr(m, 'type_of', getattr(m, 'tipo_de', None))
    types = {'cronica': 'str', 'instante': 'int', 'lapso': 'float', 'dualidad': 'bool',
             'linea': 'list', 'capsula': 'record', 'multiverso': 'set', 'particula': 'char', 'vacio': 'null'}

    def warn(node, text, severity='warning'):
        diagnostics.append({'severity': severity, 'phase': 'Editor', 'message': text,
                            'line': node.token.line, 'column': node.token.column})

    def merge(labels):
        audience = None
        known = True
        for a, k in labels:
            known &= k
            if a is not None:
                audience = a if audience is None else audience & a
        return audience, known

    def infer(node, env):
        if node.kind == 'literal':
            return types.get(type_of(literal(node.token)), type_of(literal(node.token))), None, True
        if node.kind == 'variable':
            return env.get(node.token.text, ('unknown', None, False))
        children = [infer(c, env) for c in node.children]
        audience, known = merge([(a, k) for _, a, k in children])
        if node.kind == 'call':
            name = node.token.text
            t = tools.get(name, {})
            if name in engine.sources:
                source = engine.sources[name]
                if not source.authorize(ctx):
                    warn(node, f'El contexto actual no está autorizado para consultar {name}.')
                a = source.audience(ctx)
                return t.get('output', 'unknown'), a, True
            for i, (child, parameter) in enumerate(zip(children, t.get('parameters', []))):
                actual, expected = child[0], parameter['type']
                if actual not in ('unknown', 'any') and expected != 'any' and actual != expected:
                    warn(node, f'{name}: argumento {i + 1} requiere {expected}; se infiere {actual}.')
            processor = t.get('processor')
            if processor and known and audience is not None and processor not in audience:
                warn(node, f'Las etiquetas conocidas no permiten el procesador {processor}.')
            return t.get('output', 'unknown'), audience, known
        if node.kind == 'record':
            return 'record', audience, known
        if node.kind in ('list', 'set'):
            return node.kind, audience, known
        if node.kind == 'binary':
            if node.token.kind in ('==', '!=', '<', '>', '<=', '>=', 'in', 'en', 'and', 'or', 'y', 'o'):
                return 'bool', audience, known
            if node.token.kind == '+' and any(t == 'str' for t, _, _ in children):
                return 'str', audience, known
            if children and all(t in ('int', 'float') for t, _, _ in children):
                return ('float' if node.token.kind == '/' or any(t == 'float' for t, _, _ in children) else 'int'), audience, known
        return 'unknown', audience, known

    def block(nodes, env, pc=(None, True)):
        for n in nodes:
            typ, audience, known = infer(n.children[0], env) if n.children else ('unknown', None, False)
            if n.kind == 'bind':
                declared = types.get(n.extra, n.extra)
                if declared and typ not in ('unknown', 'any', declared, 'null') and not (declared == 'float' and typ == 'int'):
                    warn(n, f'Se declara {declared}, pero se infiere {typ}.')
                env[n.token.text] = (declared or typ, *merge([(audience, known), pc]))
            elif n.kind == 'assign':
                env[n.token.text] = (typ, *merge([(audience, known), pc]))
            elif n.kind == 'send' and n.token.text in engine.sinks:
                a, k = merge([(audience, known), pc])
                identity = engine.sinks[n.token.text].identity(ctx)
                if k and a is not None and identity not in a:
                    warn(n, f'El flujo conocido no permite enviar a {identity}.')
            if n.branches:
                inner_pc = merge([(audience, known), pc])
                for branch in n.branches:
                    block(branch, dict(env), inner_pc)
                # Conservative after any branch: don't promise a previous variable label.
                for key in env:
                    env[key] = (env[key][0], None, False)
        return env

    if not errors:
        block(program, variables)
    return {'valid': not errors, 'diagnostics': diagnostics[:40],
            'variables': [{'name': name, 'type': v[0], 'audience': None if v[1] is None else sorted(v[1]),
                           'label_known': v[2]} for name, v in variables.items()],
            'tokens': [vars(t) for t in tokens], 'reads': 0,
            'note': 'Análisis estático parcial; el intérprete conserva la decisión final.'}
