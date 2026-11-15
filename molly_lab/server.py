"""Local multi-variant lab; child processes load the original interpreters."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit
from profiles import LAB, discover
from studio import Studio, StudioHandler

HOST, MAX_REQUEST, TIMEOUT, MAX_RESULT = '127.0.0.1', 60000, 6, 2 * 1024 * 1024


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def invoke(root, variant, request, timeout=TIMEOUT):
    try:
        proc = subprocess.run([sys.executable, '-I', str(LAB / 'worker.py'), str(root), variant],
                              input=json.dumps(request).encode('utf-8'), capture_output=True,
                              timeout=timeout, cwd=LAB,
                              creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    except subprocess.TimeoutExpired:
        raise RuntimeError('El laboratorio detuvo el proceso al superar el tiempo de ejecución') from None
    if proc.returncode or len(proc.stdout) > MAX_RESULT:
        raise RuntimeError('El proceso no terminó correctamente o excedió el límite de resultado')
    try:
        result = json.loads(proc.stdout.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise RuntimeError('El proceso no devolvió un resultado válido') from None
    if 'input_error' in result:
        raise ValueError(result['input_error'])
    if 'worker_error' in result:
        raise RuntimeError('Fallo del proceso de ejecución: ' + result['worker_error'])
    return result


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, roots, default, data_dir=None):
        super().__init__(address, Handler)
        self.roots, self.default = roots, default
        self.configs = {key: invoke(root, key, {'action': 'config'}) for key, root in roots.items()}
        self.execution_lock = threading.Lock()
        self.history_lock = threading.Lock()
        self.history = []
        self.studio = Studio(self, data_dir)

    def server_close(self):
        if hasattr(self, 'studio'):
            self.studio.close()
        super().server_close()

    def record(self, result):
        with self.history_lock:
            previous = self.history[-1]['hash'] if self.history else '0' * 64
            entry = {'at': datetime.now(timezone.utc).isoformat(), 'previous': previous, 'result': result}
            entry['hash'] = hashlib.sha256(canonical(entry)).hexdigest()
            self.history.append(entry)
            self.history = self.history[-20:]
            return {'hash': entry['hash'], 'previous': previous, 'at': entry['at']}


class Handler(StudioHandler, BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[Molly Lab]', fmt % args, flush=True)

    def local_request(self):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin')
        return self.headers.get('Host') in allowed and (origin is None or origin in {f'http://{h}' for h in allowed})

    def reply(self, status, data, mime='application/json; charset=utf-8', download=False):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8') if isinstance(data, (dict, list)) else data
        self.send_response(status)
        for key, value in [('Content-Type', mime), ('Content-Length', str(len(payload))),
                           ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                           ('X-Frame-Options', 'DENY')]:
            self.send_header(key, value)
        if download:
            filename = download if isinstance(download, str) else 'molly-lab-history.json'
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if not self.local_request():
            return self.reply(403, {'error': 'Solo acceso desde el laboratorio local'})
        path = urlsplit(self.path).path
        try:
            if self.studio_get(path):
                return
        except ValueError as error:
            return self.reply(400, {'error': str(error)})
        if path == '/api/health':
            return self.reply(200, {'connected': True, 'real_execution': True, 'adapters': 'synthetic',
                                    'variants': list(self.server.configs), 'default': self.server.default})
        if path == '/api/config':
            return self.reply(200, {'default': self.server.default, 'variants': self.server.configs})
        if path == '/api/history':
            with self.server.history_lock:
                entries = list(self.server.history)
            return self.reply(200, {'format': 'molly-lab-history-v1', 'signed': False,
                                    'anchor': entries[0]['previous'] if entries else '0' * 64,
                                    'entries': entries}, download=True)
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/index.html': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if path in files:
            name, mime = files[path]
            return self.reply(200, (LAB / name).read_bytes(), mime)
        return self.reply(404, {'error': 'Recurso no encontrado'})

    def do_POST(self):
        if not self.local_request():
            return self.reply(403, {'error': 'Origen no permitido'})
        if not self.path.startswith('/api/'):
            return self.reply(404, {'error': 'Recurso no encontrado'})
        try:
            if self.headers.get_content_type() != 'application/json':
                return self.reply(415, {'error': 'Usa application/json'})
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_REQUEST:
                return self.reply(413, {'error': 'Petición demasiado grande o vacía'})
            self.connection.settimeout(10)
            data = json.loads(self.rfile.read(size).decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError('Se esperaba un objeto JSON')
            if self.path != '/api/run':
                if self.studio_post(self.path, data):
                    return
                return self.reply(404, {'error': 'Recurso no encontrado'})
            variant = data.get('variant', self.server.default)
            if not isinstance(variant, str) or variant not in self.server.roots:
                raise ValueError('Variante no disponible')
            if not self.server.execution_lock.acquire(blocking=False):
                return self.reply(429, {'error': 'Hay otra ejecución en curso; vuelve a intentar'})
            try:
                data.pop('action', None)
                result = invoke(self.server.roots[variant], variant, self.server.studio.prepare(data))
                result['receipt'] = self.server.record(result.copy())
            finally:
                self.server.execution_lock.release()
            return self.reply(200, result)
        except (ValueError, UnicodeError) as error:
            return self.reply(400, {'error': str(error)})
        except RuntimeError as error:
            return self.reply(503, {'error': str(error)})
        except Exception:
            return self.reply(500, {'error': 'Error interno del laboratorio; no se fabricó un resultado del motor'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--english-root', type=Path)
    parser.add_argument('--vortex-root', type=Path)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    roots, default = discover({'english': args.english_root, 'vortex': args.vortex_root})
    server = LabServer((HOST, args.port), roots, default)
    print(f'Molly Security Lab: http://{HOST}:{server.server_port}', flush=True)
    for key, config in server.configs.items():
        print(f'  {config["name"]} v{config["version"]}: {roots[key]}', flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(f'http://{HOST}:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
