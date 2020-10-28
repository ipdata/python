import os
import socket
from pathlib import Path
from sys import stderr

import click

if __name__ == '__main__':
    from ipdata import IPData
else:
    from .ipdata import IPData


@click.group(help='CLI for IPData API')
def cli():
    pass


def get_api_key_path():
    home = str(Path.home())
    return os.path.join(home, '.ipdata')


def get_api_key():
    key_path = get_api_key_path()
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            for line in f:
                if line:
                    return line
    else:
        return None


def get_my_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


@click.command()
@click.argument('api_key', type=str)
def init(api_key):
    key_path = get_api_key_path()

    override = False
    existing_api_key = get_api_key()
    if existing_api_key:
        override = True

    ipdata = IPData(api_key)
    res = ipdata.lookup('8.8.8.8')
    if res['status'] == 200:
        with open(key_path, 'w') as f:
            f.write(api_key)
        if override:
            print(f'Warning: You already have an IPData API Key "{existing_api_key}" listed in {key_path}. '
                  f'It will be overwritten with {api_key}',
                  file=stderr)
        print(f'New API Key is saved to {key_path}')
    else:
        print(f'Failed to check the API Key (Error: {res["status"]}): {res["message"]}',
              file=stderr)


@click.command()
@click.option('--api_key', required=False, default=None, help='IPData API Key')
def myip(api_key):
    if api_key is None:
        api_key = get_api_key()
    if api_key is None:
        print(f'Please specify IPData API Key', file=stderr)
        return

    ipdata = IPData(api_key)
    ip = get_my_ip()
    try:
        res = ipdata.lookup(ip)
        print(res)
    except ValueError as e:
        print(f'Error: Your IP address {e}', file=stderr)


@click.command()
@click.argument('ip', type=str)
@click.option('--api_key', required=False, default=None, help='IPData API Key')
def ip(ip, api_key):
    if api_key is None:
        api_key = get_api_key()
    if api_key is None:
        print(f'Please specify IPData API Key', file=stderr)
        return

    ipdata = IPData(api_key)
    try:
        res = ipdata.lookup(ip)
        print(res)
    except ValueError as e:
        print(f'Error: IP address {e}', file=stderr)


cli.add_command(init)
cli.add_command(myip)
cli.add_command(ip)


if __name__ == '__main__':
    cli()
