import os
import os.path as op
import shutil
import subprocess
import tempfile
import random
import time
import signal

import requests


THIS_DIR = op.dirname(__file__)


def test_reload_copy():
    # Create first wsgi file
    pid_fp = tempfile.NamedTemporaryFile(delete=False)
    pid_file = pid_fp.name
    wsgi_file_1 = op.join(THIS_DIR, 'wsgi_1.py')
    wsgi_file_2 = op.join(THIS_DIR, 'wsgi_2.py')
    target_wsgi_file = op.join(THIS_DIR, 'wsgi.py')
    shutil.copy(wsgi_file_1, target_wsgi_file)

    # Start rainbow-saddle
    port = random.randint(32000, 64000)
    bind_address = '127.0.0.1:%s' % port
    url = 'http://%s' % bind_address
    rs_proc = subprocess.Popen([
        'rainbow-saddle',
        '--pid=%s' % pid_file,
        'gunicorn',
        'tests.wsgi:simple_app',
        '--bind=%s' % bind_address,
    ])

    # Wait until app responds
    assert_responds(url, 200, 'one')

    # Create second wsgi file, also remove .pyc files
    shutil.copy(wsgi_file_2, target_wsgi_file)
    try:
        os.unlink(target_wsgi_file + 'c')
    except OSError:
        pass
    shutil.rmtree(op.join(THIS_DIR, '__pycache__'), ignore_errors=True)

    # Send HUP to rainbow-saddle, and wait until response changes
    rs_proc.send_signal(signal.SIGHUP)
    assert_responds(url, 200, 'two')

    # Terminate rainbow-saddle
    rs_proc.send_signal(signal.SIGQUIT)
    rs_proc.wait()


def assert_responds(url, status_code=None, text=None, method='GET',
        timeout=5, reqs_timeout=0.1):
    '''
    Assert *url* responds under *timeout*.

    *status_code* and *text* can be used to add additional assertions on the
    response.
    '''
    start_time = time.time()
    resp = None
    while time.time() - start_time < timeout:
        try:
            resp = requests.request(method, url, timeout=reqs_timeout)
        except requests.RequestException as exc:
            pass
        else:
            if status_code is None and text is None:
                break
            elif status_code is not None and text is not None:
                if resp.status_code == status_code and resp.text == text:
                    break
            elif status_code is not None:
                if resp.status_code == status_code:
                    break
            elif text is not None:
                if resp.text == text:
                    break
    if resp is None:
        raise AssertionError('got no response from %s after %s seconds, last '
                'exception was:\n%s' % (url, timeout, exc))
    if status_code is not None:
        assert resp.status_code == status_code
    if text is not None:
        assert resp.text == text
