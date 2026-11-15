"""Repository discovery and vocabulary metadata, never permission rules."""
import os
from pathlib import Path

LAB = Path(__file__).resolve().parent
PROFILES = {
    'english': {'name': 'Molly Lang · English', 'tenant': 'acme', 'source': 'current_order',
                'chat': 'customer_whatsapp', 'web': 'public_web', 'draft': 'draft',
                'external': 'external_model', 'public': 'public_catalog', 'other': 'other_order',
                'read_counter': 'reads',
                'cases': dict(allowed='allowed', web='web', model='model', other='other_customer',
                              branch='branch_leak', public='public', types='types', custom='allowed'),
                'default_order': 'Order DEMO-104 for Ana: silver ring, ships tomorrow.'},
    'vortex': {'name': 'Molly Vortex · Español', 'tenant': 'mitico', 'source': 'pedido_actual',
               'chat': 'whatsapp_actual', 'web': 'web_publica', 'draft': 'redactar',
               'external': 'modelo_externo', 'public': 'catalogo_publico', 'other': 'pedido_otro',
               'read_counter': 'lecturas',
               'cases': dict(allowed='permitido', web='web', model='modelo', other='otro_cliente',
                             branch='fuga_rama', public='publico', types='tipos', custom='permitido'),
               'default_order': 'Pedido DEMO-104 de Ana: anillo de plata, despacho mañana.'},
}


def identify(path):
    path = Path(path)
    if not (path / 'molly.py').is_file() or not (path / 'demo.py').is_file():
        return None
    text = (path / 'molly.py').read_text(encoding='utf-8')
    return 'vortex' if 'LIMITE_PROGRAMA' in text else 'english' if 'MAX_PROGRAM' in text else None


def discover(overrides=None):
    own = LAB.parent
    candidates = [own]
    for base in [own.parent, *list(own.parents)[:4]]:
        candidates += [base / 'molly-lang', base / 'molly-vortex',
                       base / 'Molly_Boceto_Funcional' / 'molly-boceto']
    found = {}
    for path in candidates:
        profile = identify(path)
        if profile and profile not in found:
            found[profile] = path.resolve()
    for key in PROFILES:
        explicit = (overrides or {}).get(key) or os.environ.get('MOLLY_' + key.upper() + '_ROOT')
        if explicit:
            path = Path(explicit).resolve()
            if identify(path) != key:
                raise ValueError(f'Carpeta inválida para {key}: {path}')
            found[key] = path
    if not found:
        raise ValueError('Coloca molly_lab junto a molly.py y demo.py, o configura las rutas.')
    return found, identify(own) or next(iter(found))
