"""Validate workflow policies against installed Codex, without starting a turn.

Run on the Ubuntu worker; yaml and jsonschema are provided by cloud-init.
An optional first argument selects a workflow file for before/after checks.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

import jsonschema
import yaml

workflow = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / 'WORKFLOW.md'
config = yaml.safe_load(workflow.read_text().split('---', 2)[1])['codex']
with tempfile.TemporaryDirectory(prefix='relicrat-protocol-') as directory:
    root = Path(directory)
    schemas = root / 'schemas'
    subprocess.run(['codex', 'app-server', 'generate-json-schema', '--out', str(schemas)],
                   check=True, timeout=30)
    start = {'cwd': directory, 'approvalPolicy': config['approval_policy'],
             'sandbox': config['thread_sandbox'], 'ephemeral': True}
    turn = {'threadId': 'schema-check-only',
            'input': [{'type': 'text', 'text': 'Schema validation only; never submitted'}],
            'cwd': directory, 'title': 'Protocol preflight',
            'approvalPolicy': config['approval_policy'],
            'sandboxPolicy': config['turn_sandbox_policy']}
    for name, params in (('ThreadStartParams.json', start), ('TurnStartParams.json', turn)):
        schema = json.loads(next(schemas.rglob(name)).read_text())
        jsonschema.validate(params, schema)

    # An ephemeral thread exercises the real startup protocol; no turn is sent.
    with (root / 'server.stderr').open('w') as errors:
        process = subprocess.Popen(['codex', 'app-server'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=errors, text=True)
        timer = threading.Timer(30, process.kill)
        timer.start()
        try:
            def request(identifier, method, params):
                process.stdin.write(json.dumps({'id': identifier, 'method': method, 'params': params}) + '\n')
                process.stdin.flush()
                for line in process.stdout:
                    reply = json.loads(line)
                    if reply.get('id') == identifier:
                        if 'error' in reply:
                            raise RuntimeError(reply['error'].get('message', 'Protocol error'))
                        return reply['result']
                raise RuntimeError('Codex app-server closed before responding')

            request(1, 'initialize', {'clientInfo': {'name': 'relicrat-preflight', 'version': '1'},
                                      'capabilities': {'experimentalApi': True}})
            process.stdin.write(json.dumps({'method': 'initialized', 'params': {}}) + '\n')
            process.stdin.flush()
            result = request(2, 'thread/start', start)
            assert result['approvalPolicy'] == config['approval_policy']
            print('Protocol preflight passed: policy schemas valid, ephemeral thread accepted; no turn started')
        finally:
            timer.cancel()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
