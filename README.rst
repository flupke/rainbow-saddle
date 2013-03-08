Rainbow Saddle
==============

rainbow-saddle is a wrapper around `Gunicorn <http://gunicorn.org/>`_ to
simplify code reloading without dropping requests.

Installation
------------

Install from pypi::

    $ sudo pip install rainbow-saddle

Or from source::

    $ sudo ./setup.py install

Why?
----

Sometimes doing a ``kill -HUP <gunicorn PID>`` is not sufficient to reload your
code. For example it doesn't work well `if you host your code behind a symlink
<https://github.com/benoitc/gunicorn/issues/394>`_, or if a `.pth in your
installation is updated to point to a different directory
<https://github.com/benoitc/gunicorn/issues/402>`_.

The correct way to reload code in such situations is a bit complicated::

    # Reexec a new master with new workers
    /bin/kill -s USR2 `cat "$PID"`
    # Graceful stop old workers
    /bin/kill -s WINCH `cat "$PIDOLD"`
    # Graceful stop old master 
    /bin/kill -s QUIT `cat "$PIDOLD"`

It also has the downside of changing the "master" process PID, which confuses
tools such as supervisord.

rainbow-saddle handles all of this for you, and never changes its PID.
Reloading code becomes as simple as sending a ``SIGHUP`` again::

    rainbow-saddle gunicorn_paster development.ini --log-level debug --pid /tmp/mysite.pid
    kill -HUP `cat /tmp/mysite.pid`

All options are passed directly to the gunicorn executable, except for --pid
which writes rainbow-saddle's own PID (gunicorn's PID is written in a temporary
file).

