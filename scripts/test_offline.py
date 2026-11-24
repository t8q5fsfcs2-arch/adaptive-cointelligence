"""Run the complete Python test suite with outbound networking disabled.

Loopback is allowed for native HTTP integration tests. This never loads real model
credentials; tests use synthetic fixtures and mocked providers.
"""
import ipaddress
import os
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'src'))
sys.dont_write_bytecode = True
for key in ('OPENAI_API_KEY', 'COACH_LLM_API_KEY', 'COACH_CONFIG_FILE', 'ANTHROPIC_API_KEY'):
    os.environ.pop(key, None)


def loopback(host):
    if host in ('localhost', b'localhost'):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex
original_getaddrinfo = socket.getaddrinfo


def connect(sock, address):
    if sock.family != socket.AF_UNIX and not loopback(address[0]):
        raise AssertionError('Offline tests forbid outbound network connections')
    return original_connect(sock, address)


def connect_ex(sock, address):
    if sock.family != socket.AF_UNIX and not loopback(address[0]):
        raise AssertionError('Offline tests forbid outbound network connections')
    return original_connect_ex(sock, address)


def getaddrinfo(host, *args, **kwargs):
    if host is not None and not loopback(host):
        raise AssertionError('Offline tests forbid external name resolution')
    return original_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = getaddrinfo
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
