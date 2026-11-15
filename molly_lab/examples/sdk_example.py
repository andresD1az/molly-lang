"""Run from a repository root: python molly_lab/examples/sdk_example.py.

All adapters below are local; no messages or network requests are made.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import molly
from molly_lab.sdk import Toolkit, Tool, Parameter

vortex = hasattr(molly, 'LIMITE_PROGRAMA')
context = molly.Context('demo', 'ana')
outbox = []
tools = Toolkit()
tools.add(Tool('my_order', 'source', lambda ctx: 'Pedido de prueba',
               'Pedido del usuario autenticado', output='str',
               authorize=lambda ctx: ctx == context,
               audience=lambda ctx: frozenset({'customer:' + ctx.subject})))
tools.add(Tool('upper', 'transform', lambda ctx, text: text.upper(),
               'Texto en mayúsculas', output='str', parameters=(Parameter('text', 'str'),)))
tools.add(Tool('reply', 'sink', lambda ctx, text: outbox.append(text),
               'Caja de salida local', identity=lambda ctx: 'customer:' + ctx.subject))
engine = tools.install(molly, molly.Engine({}, {}, {}))
send = 'transmitir' if vortex else 'send'
engine.run(f'{send} reply(upper(my_order()));', context)
assert outbox == ['PEDIDO DE PRUEBA']
print('SDK OK:', outbox)
