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
        self.stopped = False
        # Create a temporary file for the gunicorn pid file
        fp = tempfile.NamedTemporaryFile(prefix='rainbow-saddle-gunicorn-',
                suffix='.pid', delete=False)
        fp.close()
        self.pidfile = fp.name
        # Start gunicorn process
        args = options.gunicorn_args + ['--pid', self.pidfile]
        process = subprocess.Popen(args)
        self.arbiter_pid = process.pid
        # Install signal handlers
        signal.signal(signal.SIGHUP, self.restart_arbiter)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, self.stop)

    def run_forever(self):
        while not self.stopped:
            time.sleep(1)

    @signal_handler
    def restart_arbiter(self, signum, frame):
        # Fork a new arbiter
        self.log('Starting new arbiter')
        os.kill(self.arbiter_pid, signal.SIGUSR2)

        # Wait until pidfile has been renamed
        old_pidfile = self.pidfile + '.oldbin'
        while True:
            if op.exists(old_pidfile):
                break
            time.sleep(0.3)

        # Gracefully kill old workers
        self.log('Stoping old arbiter with PID %s' % self.arbiter_pid)
        os.kill(self.arbiter_pid, signal.SIGTERM)
        self.wait_pid(self.arbiter_pid)

        # Read new arbiter PID, being super paranoid about it (we read the PID
        # file until we get the same value twice)
        prev_pid = None
        while True:
            if op.exists(self.pidfile):
                with open(self.pidfile) as fp:
                    try:
                        pid = int(fp.read())
                    except ValueError:
                        pass
                    else:
                        if prev_pid == pid:
                            break
                        prev_pid = pid
            else:
                print('pidfile not found: ' + self.pidfile)
            time.sleep(0.3)
        self.arbiter_pid = pid
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
        except OSError, err:
            if err.errno == 10:
                while True:
                    try:
                        process = psutil.Process(pid)
                        if process.status == 'zombie':
                            break
                    except psutil.NoSuchProcess:
                        break
                    time.sleep(0.1)


def main():
    # Parse command line
    parser = argparse.ArgumentParser(description='Wrap gunicorn to handle '
            'graceful restarts correctly')
    parser.add_argument('--pid',  help='a filename to store the '
            'rainbow-saddle PID')
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
