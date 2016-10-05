from __future__ import print_function

import os
import os.path as op
import sys
import atexit
import subprocess
import signal
import time
import argparse
import tempfile
import functools
import traceback

import psutil

try:
    import Queue as queue
except ImportError:
    import queue


def signal_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            print('Uncaught exception in signal handler %s' % func,
                    file=sys.stderr)
            traceback.print_exc()
    return wrapper


class RainbowSaddle(object):

    def __init__(self, options):
        self._arbiter_pid = None
        self.hup_queue = queue.Queue()
        self.stopped = False
        # Create a temporary file for the gunicorn pid file
        if options.gunicorn_pidfile:
            self.pidfile = options.gunicorn_pidfile
        else:
            fp = tempfile.NamedTemporaryFile(prefix='rainbow-saddle-gunicorn-',
                suffix='.pid', delete=False)
            fp.close()
            self.pidfile = fp.name
        # Start gunicorn process
        args = options.gunicorn_args + ['--pid', self.pidfile]
        process = subprocess.Popen(args)
        self.arbiter_pid = process.pid
        # Install signal handlers
        signal.signal(signal.SIGHUP, self.handle_hup)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, self.stop)

    @property
    def arbiter_pid(self):
        return self._arbiter_pid

    @arbiter_pid.setter
    def arbiter_pid(self, pid):
        self._arbiter_pid = pid
        self.arbiter_process = psutil.Process(self.arbiter_pid)

    def run_forever(self):
        while self.is_running():
            if not self.hup_queue.empty():
                with self.hup_queue.mutex:
                    self.hup_queue.queue.clear()
                self.restart_arbiter()
            time.sleep(1)

    def is_running(self):
        if self.stopped:
            return False
        try:
            pstatus = self.arbiter_process.status()
        except psutil.NoSuchProcess:
            return False
        else:
            if pstatus == psutil.STATUS_ZOMBIE:
                self.log('Gunicorn master is %s (PID: %s), shutting down '
                    'rainbow-saddle' % (pstatus, self.arbiter_pid))
                return False
        return True

    @signal_handler
    def handle_hup(self, signum, frame):
        self.hup_queue.put((signum, frame))

    def restart_arbiter(self):
        # Fork a new arbiter
        self.log('Starting new arbiter')
        os.kill(self.arbiter_pid, signal.SIGUSR2)

        # Wait until the new master is up
        new_pidfile = self.pidfile + '.2'
        while True:
            if op.exists(new_pidfile):
                self.log('New pidfile found: {}'.format(new_pidfile))
                break
            time.sleep(0.3)

        # Read new arbiter PID, being super paranoid about it (we read the PID
        # file until we get the same value twice)
        _verification_pid = None
        while True:
            with open(new_pidfile) as fp:
                try:
                    new_pid = int(fp.read())
                except ValueError:
                    pass
                else:
                    if _verification_pid == new_pid:
                        break
                    _verification_pid = new_pid
            time.sleep(0.3)

        # Gracefully kill old workers
        self.log('Stopping old arbiter with PID %s' % self.arbiter_pid)
        os.kill(self.arbiter_pid, signal.SIGTERM)
        self.wait_pid(self.arbiter_pid)

        self.arbiter_pid = new_pid
        self.log('New arbiter PID is %s' % self.arbiter_pid)

    def stop(self, signum, frame):
        os.kill(self.arbiter_pid, signal.SIGTERM)
        self.wait_pid(self.arbiter_pid)
        self.stopped = True

    def log(self, msg):
        print('-' * 78, file=sys.stderr)
        print(msg, file=sys.stderr)
        print('-' * 78, file=sys.stderr)

    def wait_pid(self, pid):
        """
        Wait until process *pid* exits.
        """
        try:
            os.waitpid(pid, 0)
        except OSError as err:
            if err.errno == 10:
                while True:
                    try:
                        process = psutil.Process(pid)
                        if process.status() == psutil.STATUS_ZOMBIE:
                            break
                    except psutil.NoSuchProcess:
                        break
                    time.sleep(0.1)


def main():
    # Parse command line
    parser = argparse.ArgumentParser(description='Wrap gunicorn to handle '
            'graceful restarts correctly')
    parser.add_argument('--pid', help='a filename to store the '
            'rainbow-saddle PID')
    parser.add_argument('--gunicorn-pidfile', help='a filename to store the '
            'gunicorn PID')
    parser.add_argument('gunicorn_args', nargs=argparse.REMAINDER,
            help='gunicorn command line')
    options = parser.parse_args()

    # Write pid file
    if options.pid is not None:
        with open(options.pid, 'w') as fp:
            fp.write('%s\n' % os.getpid())
        atexit.register(os.unlink, options.pid)

    # Run script
    saddle = RainbowSaddle(options)
    saddle.run_forever()
