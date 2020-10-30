import json
import os
import socket
from pathlib import Path
from sys import stderr, stdout

import click

if __name__ == '__main__':
    from ipdata import IPData
else:
    from .ipdata import IPData


class WrongAPIKey(Exception):
    pass


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


def get_and_check_api_key(api_key: str = None) -> str:
    if api_key is None:
        api_key = get_api_key()
    if api_key is None:
        print(f'Please specify IPData API Key', file=stderr)
        raise WrongAPIKey
    return api_key


@click.command()
@click.argument('api_key', type=str)
def init(api_key):
    key_path = get_api_key_path()

    ipdata = IPData(api_key)
    res = ipdata.lookup('8.8.8.8')
    if res['status'] == 200:
        existing_api_key = get_api_key()
        if existing_api_key:
            print(f'Warning: You already have an IPData API Key "{existing_api_key}" listed in {key_path}. '
                  f'It will be overwritten with {api_key}',
                  file=stderr)

        with open(key_path, 'w') as f:
            f.write(api_key)
        print(f'New API Key is saved to {key_path}')
    else:
        print(f'Failed to check the API Key (Error: {res["status"]}): {res["message"]}',
              file=stderr)


def json_filter(json, fields):
    res = dict()
    for name in fields:
        if name in json:
            res[name] = json[name]
        elif name.find('.') != -1:
            parts = name.split('.')
            part = parts[0] if len(parts) > 1 else None
            if part and part in json:
                sub_value = json_filter(json[part], ('.'.join(parts[1:]), ))
                if isinstance(sub_value, dict):
                    if part not in res:
                        res[part] = sub_value
                    else:
                        res[part] = {**res[part], **sub_value}
                else:
                    res[part] = sub_value
        else:
            pass
    return res


@click.command()
@click.option('--api_key', required=False, default=None, help='IPData API Key')
def me(api_key):
    try:
        ip_data = IPData(get_and_check_api_key(api_key))
        res = ip_data.lookup(ip_data.my_ip())
        json.dump(res, stdout)
    except ValueError as e:
        print(f'Error: IP address {e}', file=stderr)


def lookup_field(data, field):
    if field in data:
        return field, data[field]
    elif '.' in field:
        parent, children = field.split('.')
        parent_field, parent_data = lookup_field(data, parent)
        if parent_field:
            children_field, children_data = lookup_field(parent_data, children)
            return parent_field, {parent_field: children_data}
    return None, None


@click.command()
@click.argument('ip', type=str)
@click.argument('fields', type=str, nargs=-1)
@click.option('--api_key', required=False, default=None, help='IPData API Key')
def ip(ip, fields, api_key):
    try:
        res = IPData(get_and_check_api_key(api_key)).lookup(ip)
        if len(fields) > 0:
            json.dump(json_filter(res, fields), stdout)
        else:
            json.dump(res, stdout)
    except ValueError as e:
        print(f'Error: IP address {e}', file=stderr)


@click.command()
@click.option('--api-key', required=False, default=None, help='IPData API Key')
def info(api_key):
    res = IPData(get_and_check_api_key(api_key)).lookup('8.8.8.8')
    print(f'Number of requests made: {res["count"]}')


cli.add_command(init)
cli.add_command(me)
cli.add_command(ip)
cli.add_command(info)


if __name__ == '__main__':
    cli()
