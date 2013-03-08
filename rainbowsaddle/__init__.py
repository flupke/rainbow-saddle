import os
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
            print 'Uncaught exception in signal handler %s' % func
            traceback.print_exc()
    return wrapper


class RainbowSaddle(object):

    def __init__(self, options):
        self.stopped = False
        self.pid = os.getpid()
        # Create a temporary file for the gunicorn pid file
        fp = tempfile.NamedTemporaryFile(prefix='rainbow-saddle-gunicorn-',
                suffix='.pid', delete=False)
        fp.close()
        self.pidfile = fp.name
        # Start gunicorn process
        args = [options.command, '--pid', self.pidfile] + options.args
        process = subprocess.Popen(args)
        self.arbiter_pid = process.pid
        # Install signal handlers
        signal.signal(signal.SIGHUP, self.restart_arbiter)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, self.stop)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def handle_sigchld(self, signum, frame):
        pass

    def run_forever(self):
        while not self.stopped:
            time.sleep(1)

    @signal_handler
    def restart_arbiter(self, signum, frame):
        # Fork a new arbiter
        self.log('Starting new arbiter and gracefully stopping old workers')
        os.kill(self.arbiter_pid, signal.SIGUSR2)
        # Gracefully kill workers and wait until they are all closed
        os.kill(self.arbiter_pid, signal.SIGWINCH)
        process = psutil.Process(self.arbiter_pid)
        while len(process.get_children()) != 1:
            time.sleep(0.1)
        # Stop previous arbiter
        self.log('Stoping old arbiter with PID %s' % self.arbiter_pid)
        os.kill(self.arbiter_pid, signal.SIGQUIT)
        self.wait_pid(self.arbiter_pid)
        # Read new arbiter PID
        with open(self.pidfile) as fp:
            self.arbiter_pid = int(fp.read())
        self.log('New arbiter PID is %s' % self.arbiter_pid)

    def stop(self, signum, frame):
        os.kill(self.arbiter_pid, signal.SIGTERM)
        self.wait_pid(self.arbiter_pid)
        self.stopped = True

    def log(self, msg):
        print '-' * 78
        print msg
        print '-' * 78

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
    parser = argparse.ArgumentParser(description='Wrap gunicorn to handle '
            'graceful restarts correctly')
    parser.add_argument('command', help='the gunicorn exe to run (e.g. '
            'gunicorn, gunicorn_paster, etc...)')
    parser.add_argument('--pid', '-p', help='a filename to use for the PID '
            'file')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='additional '
            'arguments to pass to gunicorn')
    options = parser.parse_args()

    # Write pid file
    if options.pid is not None:
        with open(options.pid, 'w') as fp:
            fp.write(os.getpid())
        atexit.register(os.unlink, options.pid)
    saddle = RainbowSaddle(options)
    saddle.run_forever()
