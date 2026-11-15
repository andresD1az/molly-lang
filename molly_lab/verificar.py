"""End-to-end HTTP checks and offline verification of exported hash chains."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from profiles import discover
from server import LabServer, canonical, invoke


def verify_history(data):
    if data.get('format') != 'molly-lab-history-v1' or data.get('signed') is not False:
        raise ValueError('Formato de historial no admitido')
    previous = data['anchor']
    for i, entry in enumerate(data['entries']):
        raw = {key: value for key, value in entry.items() if key != 'hash'}
        if entry['previous'] != previous or hashlib.sha256(canonical(raw)).hexdigest() != entry['hash']:
            raise ValueError(f'Cadena alterada en la entrada {i + 1}')
        previous = entry['hash']
    return len(data['entries'])


def check():
    roots, default = discover()
    server = LabServer(('127.0.0.1', 0), roots, default)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    total = 0

    def request(path, data=None, expected=200, headers=None):
        nonlocal total
        req = Request(base + path, data=None if data is None else json.dumps(data).encode('utf-8'),
                      headers=headers or ({'Content-Type': 'application/json'} if data is not None else {}))
        try:
            response = urlopen(req, timeout=12)
        except HTTPError as error:
            response = error
        assert response.code == expected, (path, response.code, response.read())
        payload = response.read()
        total += 1
        return json.loads(payload) if path.startswith('/api/') else payload

    try:
        config = request('/api/config')
        assert request('/api/health')['real_execution']
        assert b'id="variant"' in request('/')
        assert b'changeVariant' in request('/app.js')
        for variant, c in config['variants'].items():
            for case, ok, sends, reads in [('allowed', True, 1, 1), ('web', False, 0, 1),
                                           ('model', False, 0, 1), ('other', False, 0, 0),
                                           ('branch', False, 0, 1), ('public', True, 1, 1),
                                           ('syntax', False, 0, 0), ('types', True, 1, 1)]:
                code = c['presets'][case]['code']
                r = request('/api/run', {'variant': variant, 'code': code})
                assert r['ok'] is ok, (variant, case, r)
                assert r['counters'] == {'reads': reads, 'external_model': 0, 'sends': sends}, (variant, case, r)
                assert len(r['deliveries']) == sends
                assert r['variant'] == variant
                assert r['engine_sha256'] == hashlib.sha256((roots[variant] / 'molly.py').read_bytes()).hexdigest()
                assert r['tokens'], (variant, case)
                if case == 'syntax':
                    assert r['ast'] is None
                else:
                    assert r['ast']
                if variant == 'vortex':
                    assert r['trace'][0]['operation'] in ('ANÁLISIS', 'RECHAZO')
                print(f'OK {variant:7} {case:8} sends={sends} reads={reads}')

            custom = '<script>alert("synthetic")</script> pedido cambiado'
            r = request('/api/run', {'variant': variant, 'code': c['presets']['allowed']['code'], 'order_text': custom})
            assert custom in r['outbox'][0]
            r = request('/api/run', {'variant': variant, 'code': c['presets']['allowed']['code'], 'subject': 'bruno'})
            assert not r['ok'] and r['counters']['reads'] == 0
            request('/api/run', {'variant': variant, 'code': c['presets']['allowed']['code'], 'tenant': 'invalid'}, 400)
            send = 'send' if variant == 'english' else 'transmitir'
            declared = 'int' if variant == 'english' else 'instante'
            mixed = f'{send} {c["chat"]}("chat"); {send} {c["web"]}("web"); {declared} bad = "x";'
            r = request('/api/run', {'variant': variant, 'code': mixed})
            assert not r['ok'] and r['counters']['sends'] == 2
            assert [d['sink'] for d in r['deliveries']] == [c['chat'], c['web']]
            request('/api/run', {'variant': variant, 'code': 'x' * 12001}, 400)
        request('/api/run', {'variant': 'unknown', 'code': ''}, 400)
        request('/api/run', [], 400)
        request('/api/run', {'code': ''}, 403, {'Origin': 'https://example.invalid', 'Content-Type': 'application/json'})
        history = request('/api/history')
        assert verify_history(history) == min(20, 11 * len(config['variants']))
        tampered = copy.deepcopy(history)
        tampered['entries'][0]['result']['ok'] = 'tampered'
        try:
            verify_history(tampered)
        except ValueError:
            pass
        else:
            raise AssertionError('Alteración no detectada')
        # Verify a small timeout kills the worker and a fresh execution still succeeds.
        key = next(iter(roots))
        try:
            invoke(roots[key], key, {'action': 'config'}, timeout=0.001)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Timeout no aplicado')
        assert invoke(roots[key], key, {'action': 'config'})['id'] == key
        print(f'OK: {total} comprobaciones HTTP, cadena/tampering y timeout; motores: {list(roots)}')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', type=Path, help='Comprobar el JSON descargado, sin iniciar servidor')
    args = parser.parse_args()
    if args.history:
        print(f'Cadena consistente: {verify_history(json.loads(args.history.read_text(encoding="utf-8")))} entradas. Sin firma.')
    else:
        check()
