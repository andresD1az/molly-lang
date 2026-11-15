"""Integration tests for real engines, network adapters, editor and debugger."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from profiles import discover
from server import LabServer


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='molly-studio-')
        roots, default = discover()
        cls.server = LabServer(('127.0.0.1', 0), roots, default, Path(cls.temp.name))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.configs = cls.server.configs

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp.cleanup()

    def api(self, path, data=None, status=200, headers=None):
        req = Request(self.base + path, data=None if data is None else json.dumps(data).encode(),
                      headers={**({'Content-Type': 'application/json'} if data is not None else {}), **(headers or {})})
        try:
            response = urlopen(req, timeout=20)
        except HTTPError as error:
            response = error
        raw = response.read()
        self.assertEqual(response.status, status, raw)
        return json.loads(raw)

    def program(self, variant, case='allowed', **extra):
        return {'variant': variant, 'code': self.configs[variant]['presets'][case]['code'], **extra}

    def test_analysis_has_no_effects_and_preserves_diagnostics(self):
        for variant, c in self.configs.items():
            with self.subTest(variant=variant):
                r = self.api('/api/analyze', self.program(variant, 'web'))
                self.assertTrue(r['valid'])
                self.assertEqual(r['reads'], 0)
                self.assertTrue(any('flujo' in d['message'] for d in r['diagnostics']))
                self.assertTrue(r['variables'])
                r = self.api('/api/analyze', self.program(variant, 'syntax'))
                self.assertFalse(r['valid'])
                self.assertTrue(r['tokens'])
                self.assertTrue(all(d['severity'] == 'error' for d in r['diagnostics']))
                self.assertEqual(r['reads'], 0)
                r = self.api('/api/analyze', {'variant': variant, 'code': 'x' * 12001}, status=400)

    def test_sdk_typed_transform(self):
        for variant, c in self.configs.items():
            send = 'send' if variant == 'english' else 'transmitir'
            upper = 'uppercase' if variant == 'english' else 'mayusculas'
            code = f'{send} {c["chat"]}({upper}("hola"));'
            r = self.api('/api/run', {'variant': variant, 'code': code})
            self.assertTrue(r['ok'])
            self.assertEqual(r['outbox'], ['HOLA'])
            code = f'{send} {c["chat"]}({upper}(1));'
            r = self.api('/api/analyze', {'variant': variant, 'code': code})
            self.assertTrue(any('requiere str' in d['message'] for d in r['diagnostics']))
            r = self.api('/api/run', {'variant': variant, 'code': code})
            self.assertFalse(r['ok'])
            self.assertEqual(r['counters']['sends'], 0)
            code = f'{send} {c["web"]}({upper}({c["source"]}()));'
            r = self.api('/api/run', {'variant': variant, 'code': code})
            self.assertFalse(r['ok'])
            self.assertEqual(r['counters']['sends'], 0)

    def test_http_source_and_local_delivery(self):
        for variant, c in self.configs.items():
            with self.subTest(variant=variant):
                text = f'LIVE-ORDER-{variant}'
                self.api('/api/orders/update', {'variant': variant, 'text': text})
                r = self.api('/api/run', self.program(variant, mode='integration', order_text='IGNORE THIS'))
                self.assertTrue(r['ok'], r)
                self.assertIn(text, r['outbox'][0])
                self.assertEqual([e['operation'] for e in r['io_events']], ['GET'])
                r = self.api('/api/run', self.program(variant, mode='operational'))
                self.assertTrue(r['ok'])
                self.assertEqual([e['operation'] for e in r['io_events']], ['GET', 'POST'])
                with self.server.studio.orders.connect() as db:
                    self.assertGreater(db.execute('SELECT COUNT(*) FROM messages WHERE tenant=?', (c['tenant'],)).fetchone()[0], 0)
                r = self.api('/api/run', self.program(variant, 'web', mode='operational'))
                self.assertFalse(r['ok'])
                self.assertEqual(r['counters']['sends'], 0)
                self.assertFalse(any(e['operation'] == 'POST' for e in r['io_events']))

    def test_connection_faults_and_context_checks(self):
        for variant in self.configs:
            for fault in ('http500', 'timeout', 'invalid'):
                r = self.api('/api/run', self.program(variant, mode='integration', fault=fault))
                self.assertFalse(r['ok'])
                self.assertEqual(r['counters']['sends'], 0)
                if fault != 'invalid':
                    self.assertEqual(len(r['io_events']), 2)
            r = self.api('/api/run', self.program(variant, mode='integration', subject='bruno'))
            self.assertFalse(r['ok'])
            self.assertEqual(r['io_events'], [])
            self.assertEqual(r['counters']['reads'], 0)

    def test_saved_suites_are_persistent_and_import_validation_is_atomic(self):
        for variant in self.configs:
            row = {'name': f'Own case {variant}', 'request': self.program(variant), 'expected': {'ok': True, 'sends': 1}}
            saved = self.api('/api/cases/save', row)['saved'][0]
            disk = json.loads(self.server.studio.cases_file.read_text(encoding='utf-8'))
            self.assertTrue(any(c['id'] == saved['id'] for c in disk))
            suite = self.api('/api/cases/run', {'variant': variant})
            self.assertEqual(suite['total'], suite['passed'], suite)
            self.assertGreaterEqual(suite['total'], 9)
            before = len(disk)
            self.api('/api/cases/import', {'cases': [row, {'bad': 'case'}]}, status=400)
            self.assertEqual(len(self.server.studio.cases), before)
            self.api('/api/cases/save', {**row, 'request': self.program(variant, mode='operational')}, status=400)
            self.api('/api/cases/remove', {'id': saved['id']})

    def test_n8n_gateway_auth_identity_and_no_private_return(self):
        for variant, c in self.configs.items():
            workflow = self.api('/api/n8n-workflow?variant=' + variant)
            self.assertFalse(workflow['active'])
            node = next(n for n in workflow['nodes'] if n['type'] == 'n8n-nodes-base.httpRequest')
            request = json.loads(node['parameters']['jsonBody'])
            self.assertEqual(request['code'], c['presets']['allowed']['code'])
            self.api('/api/integration/run', request, status=401)
            token = self.api('/api/integration/token', {})['token']
            headers = {'Authorization': 'Bearer ' + token}
            request.update(subject='bruno', tenant='other', request_id='n8n-test-' + variant)
            r = self.api('/api/integration/run', request, headers=headers)
            self.assertTrue(r['ok'])  # identity comes from authenticated host, not the request
            self.assertEqual(set(r), {'ok', 'status', 'counters', 'request_id', 'receipt_hash'})
            repeated = self.api('/api/integration/run', request, headers=headers)
            self.assertTrue(repeated['replayed'])
            self.assertEqual(repeated['receipt_hash'], r['receipt_hash'])
            changed = {**request, 'code': c['presets']['web']['code']}
            self.api('/api/integration/run', changed, status=409, headers=headers)

    def test_operational_gateway_replay_does_not_duplicate_deliveries(self):
        variant = next(iter(self.configs))
        token = self.api('/api/integration/token', {})['token']
        request = self.program(variant, mode='operational', request_id='durable-test')
        headers = {'Authorization': 'Bearer ' + token}
        before = self.api('/api/integration/run', request, headers=headers)
        self.assertTrue(before['ok'])
        with self.server.studio.orders.connect() as db:
            count = db.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
        self.server.studio.replays.clear()  # exercise the SQLite delivery key too
        after = self.api('/api/integration/run', request, headers=headers)
        self.assertTrue(after['ok'])
        with self.server.studio.orders.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0], count)

    def test_debug_pauses_before_actual_effects_then_steps(self):
        for variant in self.configs:
            with self.subTest(variant=variant):
                snap = self.api('/api/debug/start', self.program(variant))
                session = snap['session']
                self.assertEqual(snap['debug_event'], 'paused')
                self.assertEqual(snap['line'], 1)
                self.assertEqual(snap['counters']['reads'], 0)
                self.assertEqual(snap['deliveries'], [])
                snap = self.api('/api/debug/command', {'session': session, 'command': 'step'})
                self.assertEqual(snap['line'], 2)
                self.assertEqual(snap['counters']['reads'], 1)
                self.assertEqual(snap['counters']['sends'], 0)
                var = 'order' if variant == 'english' else 'pedido'
                self.assertIn(var, snap['variables'])
                self.assertIsNotNone(snap['variables'][var]['audience'])
                snap = self.api('/api/debug/command', {'session': session, 'command': 'continue'})
                self.assertEqual(snap['debug_event'], 'finished')
                self.assertTrue(snap['result']['ok'])
                self.assertEqual(snap['result']['counters']['sends'], 1)
                snap = self.api('/api/debug/start', self.program(variant, breakpoints=[3]))
                snap = self.api('/api/debug/command', {'session': snap['session'], 'command': 'continue'})
                self.assertEqual(snap['line'], 3)
                self.assertEqual(snap['counters']['sends'], 0)
                self.api('/api/debug/stop', {'session': snap['session']})
                self.assertIsNotNone(self.server.studio.debug.proc.poll())


if __name__ == '__main__':
    unittest.main(verbosity=2)
