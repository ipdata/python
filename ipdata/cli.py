import os
from pathlib import Path
from sys import stderr

import click

from ipdata import IPData


@click.group(help='CLI for IPData API')
def cli():
    pass


def get_api_key_path():
    home = str(Path.home())
    return os.path.join(home, '.ipdata')


@click.command()
@click.argument('api_key', type=str)
def init(api_key):
    key_path = get_api_key_path()
    override = False
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            for line in f:
                if line:
                    override = True
                break

    ipdata = IPData(api_key)
    res = ipdata.lookup('8.8.8.8')
    if res['status'] == 200:
        with open(key_path, 'w') as f:
            f.write(api_key)
        if override:
            print(f'Warning: You already have an IPData API Key "{line}" listed in {key_path}. '
                  f'It will be overwritten with {api_key}',
                  file=stderr)
        print(f'New API Key is saved to {key_path}')
    else:
        print(f'Failed to check the API Key (Error: {res["status"]}): {res["message"]}',
              file=stderr)


@click.command(name='ipdata')
def main():
    pass


cli.add_command(init)
# cli.add_command(main)


if __name__ == '__main__':
    cli()
