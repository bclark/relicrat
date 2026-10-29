"""SSH policy/quoting and binary relay lifecycle checks; no credentials needed."""
import importlib.util
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('worker_ssh', Path(__file__).with_name('worker-ssh.py'))
worker_ssh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_ssh)


class WorkerSSHTests(unittest.TestCase):
    def test_command_and_interactive_modes_preserve_identity_and_quoting(self):
        for arguments, tty in [([], '-tt'), (["printf '%s' 'a; b'"], '-T')]:
            with self.subTest(arguments=arguments), patch.object(sys, 'argv', ['worker-ssh.py', *arguments]), patch.object(worker_ssh.os, 'execvp') as execute:
                worker_ssh.main()
                executable, outer = execute.call_args.args
                self.assertEqual(executable, 'ssh')
                self.assertEqual(outer[1], tty)
                self.assertIn('StrictHostKeyChecking=yes', outer)
                self.assertIn('ForwardAgent=no', outer)
                self.assertEqual(outer[-2], 'technodrome')
                inner = shlex.split(outer[-1])
                self.assertEqual(inner[1], tty)
                self.assertIn('IdentitiesOnly=yes', inner)
                self.assertIn('ForwardAgent=no', inner)
                self.assertIn('HostKeyAlias=relicrat-worker', inner)
                self.assertIn('UserKnownHostsFile=/home/bclark/relicrat-worker/known_hosts', inner)
                self.assertEqual(inner[inner.index('-i')+1], '/home/bclark/relicrat-worker/operator_ed25519')
                self.assertEqual(inner[inner.index('-p')+1], '22222')
                proxy = shlex.split(next(x.removeprefix('ProxyCommand=') for x in inner if x.startswith('ProxyCommand=')))
                self.assertEqual(proxy[:6], ['docker', 'exec', '-i', 'relicrat-worker-vm-1', 'python3', '-c'])
                self.assertEqual(proxy[6:], [worker_ssh.RELAY, '2222'])
                self.assertEqual(inner[-len(arguments):] if arguments else [], arguments)

    def test_binary_relay_delivers_response_after_stdin_eof(self):
        payload = bytes(range(256)) * 1024
        received = bytearray()
        errors = []
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen(); server.settimeout(10)
            def respond():
                try:
                    with server.accept()[0] as connection:
                        connection.settimeout(10)
                        connection.sendall(b'banner\x00\xff')
                        while data := connection.recv(65536):
                            received.extend(data)
                        connection.sendall(bytes(received)[::-1])
                except Exception as error:
                    errors.append(error)
            thread = threading.Thread(target=respond, daemon=True); thread.start()
            result = subprocess.run([sys.executable, '-c', worker_ssh.RELAY, str(server.getsockname()[1])], input=payload, capture_output=True, timeout=15)
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(received, payload)
        self.assertEqual(result.stdout, b'banner\x00\xff' + payload[::-1])

    def test_remote_eof_exits_without_waiting_for_stdin(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen(); server.settimeout(10)
            with subprocess.Popen([sys.executable, '-c', worker_ssh.RELAY, str(server.getsockname()[1])], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                with server.accept()[0] as connection:
                    connection.sendall(b'last bytes')
                self.assertEqual(process.wait(timeout=10), 0)
                self.assertEqual(process.stdout.read(), b'last bytes')


if __name__ == '__main__':
    unittest.main()
