"""Workbench services: saved suites, local integration and actual debugger IPC."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import uuid

from orders_api import OrdersAPI
from profiles import LAB


class DebugSession:
    def __init__(self, root, variant, data):
        self.id = uuid.uuid4().hex
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.state = {'debug_event': 'starting'}
        self.proc = subprocess.Popen([sys.executable, '-I', str(LAB / 'worker.py'), str(root), variant],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', cwd=LAB,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        def read():
            for line in self.proc.stdout:
                try:
                    self.queue.put(json.loads(line))
                except ValueError:
                    self.queue.put({'worker_error': 'Invalid debugger response'})
            self.queue.put({'worker_error': 'Worker exited'})
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        self.proc.stdin.write(json.dumps({**data, 'action': 'debug'}) + '\n')
        self.proc.stdin.flush()
        self.timer = threading.Timer(180, self.close)
        self.timer.daemon = True
        self.timer.start()

    def advance(self, command=None):
        with self.lock:
            if command:
                if self.state.get('debug_event') != 'paused' or command not in ('step', 'continue'):
                    raise ValueError('La sesión no está pausada o el comando no es válido')
                self.proc.stdin.write(json.dumps({'command': command}) + '\n')
                self.proc.stdin.flush()
            try:
                value = self.queue.get(timeout=7)
            except queue.Empty:
                self.close()
                raise RuntimeError('El depurador superó el tiempo activo de ejecución') from None
            if 'worker_error' in value:
                self.close()
                raise RuntimeError('El proceso del depurador no pudo completar la ejecución')
            self.state = value
            if value['debug_event'] == 'finished':
                self.timer.cancel()
                self.proc.wait(timeout=2)
                self.release_pipes()
            return {'session': self.id, **value}

    def close(self):
        if hasattr(self, 'timer'):
            self.timer.cancel()
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        self.release_pipes()
        self.state = {'debug_event': 'cancelled'}

    def release_pipes(self):
        self.reader.join(timeout=1)
        for pipe in (self.proc.stdin, self.proc.stdout):
            if pipe and not pipe.closed:
                pipe.close()


class Studio:
    def __init__(self, server, data_dir=None):
        self.server = server
        self.data_dir = Path(data_dir or LAB / '.data')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.orders = OrdersAPI(self.data_dir)
        self.lock = threading.RLock()
        self.cases_file = self.data_dir / 'cases.json'
        self.cases = json.loads(self.cases_file.read_text(encoding='utf-8')) if self.cases_file.exists() else []
        self.debug = None
        self.token = secrets.token_urlsafe(32)
        self.replays = {}
        self.replay_lock = threading.Lock()

    def close(self):
        if self.debug:
            self.debug.close()
        self.orders.shutdown()
        self.orders.server_close()

    def prepare(self, data):
        data = dict(data)
        data.pop('_connection', None)
        mode = data.get('mode', 'simulated')
        if mode not in ('simulated', 'integration', 'operational'):
            raise ValueError('Modo no disponible')
        if data.get('fault', 'none') not in ('none', 'timeout', 'http500', 'invalid'):
            raise ValueError('Fallo de prueba no disponible')
        if mode != 'simulated':
            data['_connection'] = {**self.orders.description(), 'token': self.orders.token,
                                   'run_id': uuid.uuid4().hex}
        return data

    def seeds(self):
        rows = []
        expected = {'allowed': (True, 1, 1), 'web': (False, 0, 1), 'model': (False, 0, 1),
                    'other': (False, 0, 0), 'branch': (False, 0, 1), 'public': (True, 1, 1),
                    'syntax': (False, 0, 0), 'types': (True, 1, 1)}
        for variant, c in self.server.configs.items():
            for key, (ok, sends, reads) in expected.items():
                rows.append({'id': f'seed-{variant}-{key}', 'name': f'{variant} · {key}', 'builtin': True,
                    'request': {'variant': variant, 'code': c['presets'][key]['code'], 'mode': 'simulated',
                                'tenant': c['tenant'], 'subject': 'ana', 'order_text': c['default_order']},
                    'expected': {'ok': ok, 'sends': sends, 'reads': reads, 'external_model': 0}})
        return rows

    def validate_case(self, row):
        if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not 0 < len(row['name']) <= 100:
            raise ValueError('Nombre de prueba no válido')
        req = row.get('request', {})
        if not isinstance(req, dict) or req.get('variant') not in self.server.configs:
            raise ValueError('Variante de prueba no válida')
        if not isinstance(req.get('code'), str) or len(req['code']) > 12000:
            raise ValueError('Código de prueba no válido')
        if req.get('mode', 'simulated') not in ('simulated', 'integration'):
            raise ValueError('Las suites no realizan envíos operativos')
        expected = row.get('expected', {})
        if not isinstance(expected, dict) or type(expected.get('ok')) is not bool:
            raise ValueError('La prueba necesita un resultado esperado booleano')
        for key in ('sends', 'reads', 'external_model'):
            if key in expected and (type(expected[key]) is not int or not 0 <= expected[key] <= 10000):
                raise ValueError('Contador esperado no válido')
        if 'contains' in expected and (not isinstance(expected['contains'], str) or len(expected['contains']) > 3000):
            raise ValueError('Texto esperado no válido')
        keys = ('variant', 'code', 'mode', 'tenant', 'subject', 'order_text', 'fault')
        return {'id': uuid.uuid4().hex, 'name': row['name'], 'builtin': False,
                'request': {k: req[k] for k in keys if k in req}, 'expected': dict(expected)}

    def save_cases(self, rows):
        if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
            raise ValueError('Importa entre 1 y 50 casos')
        validated = [self.validate_case(row) for row in rows]
        with self.lock:
            if len(self.cases) + len(validated) > 100:
                raise ValueError('Máximo 100 pruebas personales')
            self.cases.extend(validated)
            self.persist()
        return validated

    def persist(self):
        tmp = self.cases_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.cases, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.cases_file)

    def suite(self, request):
        from server import invoke
        variant = request.get('variant', self.server.default)
        with self.lock:
            cases = [r for r in self.seeds() + list(self.cases) if r['request']['variant'] == variant]
        chosen = request.get('ids')
        if chosen is not None:
            if not isinstance(chosen, list) or any(not isinstance(i, str) for i in chosen):
                raise ValueError('Selección de casos no válida')
            cases = [r for r in cases if r['id'] in chosen]
        reports = []
        for case in cases:
            try:
                req = self.prepare(case['request'])
                result = invoke(self.server.roots[variant], variant, req)
                actual = {'ok': result['ok'], **result['counters']}
                differences = [f'{k}: esperado {v}, obtenido {actual.get(k)}' for k, v in case['expected'].items()
                               if k != 'contains' and actual.get(k) != v]
                if 'contains' in case['expected'] and case['expected']['contains'] not in '\n'.join(result['outbox']):
                    differences.append('El texto esperado no aparece en las salidas')
                reports.append({'id': case['id'], 'name': case['name'], 'passed': not differences,
                                'actual': actual, 'differences': differences})
            except (ValueError, RuntimeError) as error:
                reports.append({'id': case['id'], 'name': case['name'], 'passed': False, 'differences': [str(error)]})
        return {'total': len(reports), 'passed': sum(r['passed'] for r in reports), 'reports': reports}

    def workflow(self, variant):
        if variant not in self.server.configs:
            raise ValueError('Variante no disponible')
        c = self.server.configs[variant]
        return {'name': f'Molly Security Lab — {variant}', 'active': False,
            'nodes': [
                {'parameters': {}, 'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1,
                 'position': [0, 0], 'id': 'molly-trigger', 'name': 'Ejecutar prueba'},
                {'parameters': {'method': 'POST',
                    'url': f'http://127.0.0.1:{self.server.server_port}/api/integration/run',
                    'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
                    'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': json.dumps({'variant': variant, 'mode': 'integration',
                                            'code': c['presets']['allowed']['code']}),
                    'options': {'timeout': 15000}},
                 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2,
                 'position': [280, 0], 'id': 'molly-run', 'name': 'Molly — ejecutar con políticas',
                 'notesInFlow': True,
                 'notes': 'Configura Header Auth: Authorization: Bearer <token local del laboratorio>. No devuelve datos privados.'}],
            'connections': {'Ejecutar prueba': {'main': [[{'node': 'Molly — ejecutar con políticas', 'type': 'main', 'index': 0}]]}},
            'settings': {'executionOrder': 'v1'}, 'pinData': {}}


class StudioHandler:
    """Mixin: the base handler has already checked local host/origin and JSON."""
    def studio_get(self, path):
        from urllib.parse import parse_qs, urlsplit
        studio = self.server.studio
        if path == '/api/cases':
            with studio.lock:
                return self.reply(200, {'cases': studio.seeds() + list(studio.cases)}) or True
        if path == '/api/connection':
            return self.reply(200, {'service': studio.orders.description(), 'modes': ['simulated', 'integration', 'operational'],
                'operational_scope': 'local synthetic delivery ledger', 'authenticated_gateway': '/api/integration/run'}) or True
        if path == '/api/n8n-workflow':
            query = parse_qs(urlsplit(self.path).query)
            variant = query.get('variant', [self.server.default])[0]
            return self.reply(200, studio.workflow(variant), download=f'molly-n8n-{variant}.json') or True
        if path == '/studio.js':
            return self.reply(200, (LAB / 'studio.js').read_bytes(), 'text/javascript; charset=utf-8') or True
        if path == '/studio.css':
            return self.reply(200, (LAB / 'studio.css').read_bytes(), 'text/css; charset=utf-8') or True
        return False

    def studio_post(self, path, data):
        from server import invoke, canonical
        studio = self.server.studio
        variant = data.get('variant', self.server.default)
        if not isinstance(variant, str) or variant not in self.server.roots:
            raise ValueError('Variante no disponible')
        root = self.server.roots[variant]
        if path == '/api/analyze':
            return self.reply(200, invoke(root, variant, {**data, 'action': 'analyze'})) or True
        if path == '/api/cases/save':
            return self.reply(200, {'saved': studio.save_cases([data])}) or True
        if path == '/api/cases/import':
            return self.reply(200, {'saved': studio.save_cases(data.get('cases'))}) or True
        if path == '/api/cases/remove':
            with studio.lock:
                studio.cases = [r for r in studio.cases if r['id'] != data.get('id')]
                studio.persist()
            return self.reply(200, {'removed': True}) or True
        if path == '/api/cases/run':
            with self.server.execution_lock:
                return self.reply(200, studio.suite(data)) or True
        if path == '/api/orders/update':
            c = self.server.configs[variant]
            studio.orders.update(c['tenant'], data.get('subject', 'ana'), data.get('text'))
            return self.reply(200, {'updated': True}) or True
        if path == '/api/integration/token':
            return self.reply(200, {'token': studio.token}) or True
        if path == '/api/integration/run':
            if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + studio.token):
                return self.reply(401, {'error': 'Credencial de integración no válida'}) or True
            c = self.server.configs[variant]
            # The authenticated host binds identity. Never trust tenant/subject from a plan or n8n input.
            req = {'variant': variant, 'code': data.get('code'), 'mode': data.get('mode', 'integration'),
                   'tenant': c['tenant'], 'subject': 'ana'}
            if req['mode'] not in ('integration', 'operational'):
                raise ValueError('Modo de integración no válido')
            key = data.get('request_id') or uuid.uuid4().hex
            if not isinstance(key, str) or not 1 <= len(key) <= 100:
                raise ValueError('request_id inválido')
            fingerprint = hashlib.sha256(canonical(req)).hexdigest()
            with studio.replay_lock:
                if key in studio.replays:
                    prior = studio.replays[key]
                    if prior['fingerprint'] != fingerprint:
                        return self.reply(409, {'error': 'request_id ya utilizado con otro programa'}) or True
                    return self.reply(200, {**prior['result'], 'replayed': True}) or True
                with self.server.execution_lock:
                    prepared = studio.prepare(req)
                    prepared['_connection']['run_id'] = 'gateway:' + key
                    result = invoke(root, variant, prepared)
                    receipt = self.server.record(result)
                phase = result.get('errors', [{}])[0].get('phase') if result.get('errors') else None
                # Return decisions only. Private outbox, trace, data and diagnostics stay inside Molly.
                safe = {'ok': result['ok'], 'status': 'allowed' if result['ok'] else 'blocked' if phase in ('Policy', 'Access', 'Política', 'Acceso') else 'rejected',
                        'counters': result['counters'], 'request_id': key, 'receipt_hash': receipt['hash']}
                studio.replays[key] = {'fingerprint': fingerprint, 'result': safe}
                if len(studio.replays) > 200:
                    del studio.replays[next(iter(studio.replays))]
                return self.reply(200, safe) or True
        if path == '/api/debug/start':
            if data.get('mode') == 'operational':
                raise ValueError('El depurador usa simulación o integración con envíos interceptados')
            with studio.lock:
                if studio.debug:
                    studio.debug.close()
                studio.debug = DebugSession(root, variant, studio.prepare(data))
                answer = studio.debug.advance()
                if answer['debug_event'] == 'finished':
                    answer['result']['receipt'] = self.server.record(answer['result'].copy())
            return self.reply(200, answer) or True
        if path in ('/api/debug/command', '/api/debug/stop'):
            with studio.lock:
                session = studio.debug
                if not session or data.get('session') != session.id:
                    raise ValueError('Sesión de depuración no encontrada')
                if path.endswith('/stop'):
                    session.close()
                    return self.reply(200, {'session': session.id, 'debug_event': 'cancelled'}) or True
                answer = session.advance(data.get('command'))
                if answer['debug_event'] == 'finished':
                    answer['result']['receipt'] = self.server.record(answer['result'].copy())
            return self.reply(200, answer) or True
        return False
