import json
import subprocess
import sys
import threading
import http.server
import socketserver
import contextlib
import os


def run_cli(args, cwd=None):
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'src'))
    cli_path = os.path.join(src_path, 'caiengine', 'cli.py')
    cmd = [sys.executable, cli_path] + args
    env = os.environ.copy()
    env['PYTHONPATH'] = src_path + os.pathsep + env.get('PYTHONPATH', '')
    env['CAIENGINE_LIGHT_IMPORT'] = '1'
    return subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, env=env)


@contextlib.contextmanager
def run_server(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

    with socketserver.TCPServer(('127.0.0.1', 0), Handler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            yield port
        finally:
            httpd.shutdown()
            thread.join()


def test_model_cli_local_workflow(tmp_path):
    src = tmp_path / 'model_src.json'
    with open(src, 'w', encoding='utf-8') as f:
        json.dump({'version': '1.0', 'data': []}, f)

    loaded = tmp_path / 'loaded.json'
    run_cli(['model', 'load', '--source', str(src), '--dest', str(loaded), '--version', '1.0'])
    assert loaded.exists()

    run_cli(['model', 'migrate', '--path', str(loaded), '--target-version', '2.0'])
    with open(loaded, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['version'] == '2.0'

    exported = tmp_path / 'exported.json'
    run_cli(['model', 'export', '--path', str(loaded), '--dest', str(exported)])
    with open(exported, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['version'] == '2.0'


def test_model_cli_remote_load(tmp_path):
    remote_model = tmp_path / 'remote.json'
    with open(remote_model, 'w', encoding='utf-8') as f:
        json.dump({'version': '1.0'}, f)

    with run_server(tmp_path) as port:
        dest = tmp_path / 'download.json'
        url = f'http://127.0.0.1:{port}/remote.json'
        run_cli(['model', 'load', '--source', url, '--dest', str(dest)])
        assert dest.exists()
        with open(dest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['version'] == '1.0'
