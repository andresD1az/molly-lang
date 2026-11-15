"""Actual local HTTP + SQLite pilot, using only synthetic orders and messages."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlsplit


class OrdersAPI(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, data_dir):
        self.db = Path(data_dir) / 'orders.sqlite'
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS orders (tenant TEXT, subject TEXT, text TEXT, PRIMARY KEY(tenant,subject))')
            db.execute('CREATE TABLE IF NOT EXISTS messages (request_id TEXT PRIMARY KEY, tenant TEXT, subject TEXT, channel TEXT, text TEXT)')
            for tenant in ('acme', 'mitico'):
                for subject in ('ana', 'bruno'):
                    db.execute('INSERT OR IGNORE INTO orders VALUES (?,?,?)',
                               (tenant, subject, f'Pedido DEMO-104 de {subject}: anillo de plata, despacho mañana.'))
        super().__init__(('127.0.0.1', 0), OrdersHandler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=3)
        try:
            with db:
                yield db
        finally:
            db.close()

    def update(self, tenant, subject, text):
        if tenant not in ('acme', 'mitico') or subject not in ('ana', 'bruno') or not isinstance(text, str) or len(text) > 3000:
            raise ValueError('Pedido de prueba inválido')
        with self.connect() as db:
            db.execute('UPDATE orders SET text=? WHERE tenant=? AND subject=?', (text, tenant, subject))

    def description(self):
        return {'kind': 'local-http-sqlite', 'url': f'http://127.0.0.1:{self.server_port}',
                'synthetic': True, 'durable': True}


class OrdersHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def authorized(self):
        return secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.server.token)

    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'error': 'unauthorized'})
        parsed = urlsplit(self.path)
        if parsed.path != '/orders/current':
            return self.reply(404, {'error': 'not-found'})
        query = parse_qs(parsed.query)
        tenant, subject = query.get('tenant', [''])[0], query.get('subject', [''])[0]
        fault = query.get('fault', ['none'])[0]
        if fault == 'timeout':
            time.sleep(1.5)
        if fault == 'http500':
            return self.reply(500, {'error': 'synthetic-service-failure'})
        if fault == 'invalid':
            return self.reply(200, {'unexpected': True})
        with self.server.connect() as db:
            row = db.execute('SELECT text FROM orders WHERE tenant=? AND subject=?', (tenant, subject)).fetchone()
        return self.reply(200 if row else 404, {'text': row[0]} if row else {'error': 'not-found'})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'unauthorized'})
        if self.path != '/deliveries':
            return self.reply(404, {'error': 'not-found'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 20000:
                raise ValueError()
            value = json.loads(self.rfile.read(size))
            key = self.headers.get('Idempotency-Key', '')
            if not key or value.get('channel') not in ('chat', 'web') or not isinstance(value.get('text'), str):
                raise ValueError()
            with self.server.connect() as db:
                existing = db.execute('SELECT tenant,subject,channel,text FROM messages WHERE request_id=?', (key,)).fetchone()
                body = (value['tenant'], value['subject'], value['channel'], value['text'])
                if existing and existing != body:
                    return self.reply(409, {'error': 'idempotency-conflict'})
                db.execute('INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?)', (key, *body))
            return self.reply(200, {'accepted': True, 'duplicate': existing is not None})
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {'error': 'invalid-input'})
