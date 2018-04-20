"""Command line tool for starting a Cheroot instance.

Basic usage::

    # Start a server on 127.0.0.1:8000 with the default settings
    # for the WSGI app myapp/wsgi.py:application()
    cheroot myapp.wsgi

    # Start a server on 0.0.0.0:9000 with 8 threads
    # for the WSGI app myapp/wsgi.py:main_app()
    cheroot myapp.wsgi:main_app --bind 0.0.0.0:9000 --threads 8
"""

import argparse
from importlib import import_module
import os
import re
import sys

from .wsgi import Server

RE_ADDRESS = r'^(\S+)(?::)([0-9]+)$'


def wsgi_app_path(string):
    """Convert WSGI app string to a tuple."""
    if ':' in string:
        mod_path, app_path = string.split(':', 1)
    else:
        mod_path, app_path = string, 'application'

    return mod_path, app_path


def wsgi_bind_addr(string):
    """Convert bind address string to a format accepted by Server()."""
    # try and match for an IP/hostname and port
    match = re.match(RE_ADDRESS, string)
    if match:
        addr, port = match.groups()
        port = int(port)
        return addr, port

    # else, assume a UNIX socket path
    return string


def main(args=None):
    """Run cheroot from the CLI."""
    # read arguments
    parser = argparse.ArgumentParser(
        description='Start an instance of the Cheroot WSGI server.')
    parser.add_argument(
        '_wsgi_app', metavar='APP_MODULE',
        type=wsgi_app_path,
        help='WSGI application callable to use')
    parser.add_argument(
        '--bind', metavar='ADDRESS',
        dest='bind_addr', type=wsgi_bind_addr,
        default='127.0.0.1:8000',
        help='Network interface to listen on (default: 127.0.0.1:8000)')
    parser.add_argument(
        '--chdir', metavar='PATH',
        dest='_chdir', default='.',
        help='Set the working directory')
    parser.add_argument(
        '--server-name',
        dest='server_name', type=str,
        help='Web server name to be advertised via Server HTTP header')
    parser.add_argument(
        '--threads', metavar='INT',
        dest='numthreads', type=int,
        help='Number of threads for WSGI thread pool')
    parser.add_argument(
        '--max-threads', metavar='INT',
        dest='max', type=int,
        help='Maximum number of worker threads')
    parser.add_argument(
        '--timeout', metavar='INT',
        dest='timeout', type=int,
        help='Timeout in seconds for accepted connections')
    parser.add_argument(
        '--shutdown-timeout', metavar='INT',
        dest='shutdown_timeout', type=int,
        help='Time in seconds to wait for worker threads to cleanly exit')
    parser.add_argument(
        '--request-queue-size', metavar='INT',
        dest='request_queue_size', type=int,
        help='Maximum number of queued connections')
    parser.add_argument(
        '--accepted-queue-size', metavar='INT',
        dest='accepted_queue_size', type=int,
        help='Maximum number of active requests in queue')
    parser.add_argument(
        '--accepted-queue-timeout', metavar='INT',
        dest='accepted_queue_timeout', type=int,
        help='Timeout in seconds for putting requests into queue')
    raw_args = parser.parse_args(args)

    # change directory if required
    chdir = os.path.abspath(raw_args._chdir)
    os.chdir(chdir)

    # add working directory to the path so module importing will resolve
    if chdir not in sys.path:
        sys.path.insert(0, chdir)

    # import the module and grab the application object
    mod_path, app_path = raw_args._wsgi_app
    module = import_module(mod_path)
    app = eval(app_path, vars(module))

    if app is None:
        raise NameError(
            'Failed to find application object: {}'.format(app_path))
    elif not callable(app):
        raise TypeError('Application must be a callable object')

    # create a Server object based on the arguments provided
    server_args = {
        k: v for k, v in vars(raw_args).items()
        if (not k.startswith('_')) and v is not None
    }
    server_args['wsgi_app'] = app
    server = Server(**server_args)

    try:
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


if __name__ == '__main__':
    main()
