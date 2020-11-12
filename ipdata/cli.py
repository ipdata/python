import csv
import json
import multiprocessing
import os
import sys
from ipaddress import ip_address
from pathlib import Path
from sys import stderr, stdout

import click
from setuptools._vendor.ordered_set import OrderedSet
from tqdm import tqdm

if __name__ == '__main__' or __name__ == '__mp_main__':
    from ipdata import IPData
else:
    from .ipdata import IPData


class WrongAPIKey(Exception):
    pass


class IPAddressType(click.ParamType):
    name = 'IP_Address'

    def convert(self, value, param, ctx):
        try:
            return ip_address(value)
        except:
            self.fail(f'{value} is not valid IPv4 or IPv6 address')

    def __str__(self) -> str:
        return 'IP Address'


@click.group(help='CLI for ipdata API', invoke_without_command=True)
@click.option('--api-key', required=False, default=None, help='ipdata API Key')
@click.pass_context
def cli(ctx, api_key):
    ctx.ensure_object(dict)
    key = ctx.obj['api-key'] = get_and_check_api_key(api_key)
    if not ctx.invoked_subcommand == "init":
        if key is None:
            print(f'Please initialize the cli by running "ipdata init <api key>" then try again', file=stderr)
            sys.exit(1)
    if ctx.invoked_subcommand is None:
        print_ip_info(api_key)
    else:
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


def get_and_check_api_key(api_key: str = None) -> str:
    if api_key is None:
        api_key = get_api_key()
    return api_key


@cli.command()
@click.argument('api-key', required=True, type=str)
def init(api_key):
    key_path = get_api_key_path()

    ipdata = IPData(api_key)
    res = ipdata.lookup('8.8.8.8')
    if res['status'] == 200:
        with open(key_path, 'w') as f:
            f.write(api_key)
        print(f'Successfully initialized.')
    else:
        print(f'Setup failed. (Error: {res["status"]}): {res["message"]}',
              file=stderr)


def get_json_value(json, name):
    if name in json:
        return json[name]
    elif name.find('.') != -1:
        parts = name.split('.')
        part = parts[0] if len(parts) > 1 else None
        if part and part in json:
            return get_json_value(json[part], '.'.join(parts[1:]))
    else:
        return None


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


@cli.command()
@click.option('--fields', required=False, type=str, default=None, help='Comma separated list of fields to extract')
@click.pass_context
def me(ctx, fields):
    print_ip_info(ctx.obj['api-key'], ip=None, fields=fields)


def do_lookup(ip_chunk, fields, api_key):
    ip_data = IPData(get_and_check_api_key(api_key))

    @filter_json_response(batch=True)
    def get_bulk_result(ip_chunk, fields):
        return ip_data.bulk_lookup(ip_chunk, fields=fields)

    return get_bulk_result(ip_chunk, fields=fields)


@cli.command()
@click.argument('ip-list', required=True, type=click.File(mode='r', encoding='utf-8'))
@click.option('--output', required=False, default=stdout, type=click.File(mode='w', encoding='utf-8'),
              help='Output to file or stdout')
@click.option('--output-format', required=False, type=click.Choice(('JSON', 'CSV'), case_sensitive=False),
              default='JSON', help='Format of output')
@click.option('--fields', required=False, type=str, default=None, help='Comma separated list of fields to extract')
@click.option('--workers', '-w', 'workers', required=False, type=int, default=multiprocessing.cpu_count(),
              help='Number of workers')
@click.pass_context
def batch(ctx, ip_list, output, output_format, fields, workers):
    print(f'Batch lookup IP addresses from {ip_list.name}')

    extract_fields = fields.split(',') if fields else None
    output_format = output_format.upper()

    if output_format == 'CSV' and extract_fields is None:
        print(f'You need to specify a "--fields" argument with a list of fields to extract to get results in CSV. To get entire responses use JSON.', file=stderr)
        return

    def filter_ip(value):
        value = value.strip()
        try:
            ip_address(value)
            return True
        except:
            return False

    with tqdm(total=0) as t, \
            multiprocessing.Pool(workers) as pool:
        ips = list(
            filter(filter_ip, [ip.strip() for ip in ip_list])
        )

        result_context = {}
        if output_format == 'CSV':
            print(f'# {fields}', file=output)  # print comment with columns
            result_context['writer'] = csv.writer(output)

            def print_result(res):
                for result in res['responses']:
                    t.update()
                    result_context['writer'].writerow(
                        [get_json_value(result, k) for k in extract_fields]
                    )

            def finish():
                pass

        elif output_format == 'JSON':
            result_context['results'] = []

            def print_result(res):
                t.update(len(res['responses']))
                result_context['results'].append(res['responses'])

            def finish():
                json.dump(result_context, fp=output)

        else:
            print(f'Unsupported format: {output_format}', file=stderr)
            return

        def handle_error(e):
            print(e)

        for i in range(0, len(ips), 100):
            chunk = ips[i:i + 100]
            t.total += len(chunk)

            pool.apply_async(do_lookup,
                             args=[chunk],
                             kwds=dict(fields=fields, api_key=ctx.obj['api-key']),
                             callback=print_result,
                             error_callback=handle_error)
        pool.close()
        pool.join()
        t.close()

        finish()


@click.command()
@click.argument('ip', required=True, type=IPAddressType())
@click.option('--fields', required=False, type=str, default=None, help='Comma separated list of fields to extract')
@click.option('--api-key', required=False, default=None, help='ipdata API Key')
def ip(ip, fields, api_key):
    print_ip_info(get_and_check_api_key(api_key), ip=ip, fields=fields)


def print_ip_info(api_key, ip=None, fields=None):
    try:
        json.dump(get_ip_info(api_key, ip, fields=fields), stdout)
    except ValueError as e:
        print(f'Error: {e}', file=stderr)


def filter_json_response(batch=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'fields' in kwargs and kwargs['fields']:
                fields = kwargs['fields']
                prepared_fields = OrderedSet(filter(
                    lambda x: len(x.strip()) > 0,
                    fields.split(',') if fields else None
                ))
                plain_fields = list(OrderedSet(map(lambda f: f.split('.')[0], prepared_fields)))

                del kwargs['fields']
                kwargs['fields'] = plain_fields

                if batch:
                    responses = func(*args, **kwargs)
                    filtered_responses = []
                    for r in responses['responses']:
                        filtered_responses.append(json_filter(r, prepared_fields))
                    responses['responses'] = filtered_responses
                    return responses
                else:
                    return json_filter(func(*args, **kwargs), prepared_fields)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


@filter_json_response()
def get_ip_info(api_key, ip=None, fields=None):
    api_key = get_and_check_api_key(api_key)
    if api_key is None:
        print(f'Please initialize the cli by running "ipdata init <api key>" then try again or pass an API key with the --api-key option', file=stderr)
        sys.exit(1)
    ip_data = IPData(api_key)
    return ip_data.lookup(ip, fields=fields)


@cli.command()
@click.pass_context
def info(ctx):
    res = IPData(get_and_check_api_key(ctx.obj['api-key'])).lookup('8.8.8.8')
    print(f'Number of requests made: {res["count"]}')


def is_ip_address(value):
    try:
        ip_address(value)
        return True
    except ValueError:
        return False


def todo():
    if len(sys.argv) >= 2 and is_ip_address(sys.argv[1]):
        ip()
    else:
        cli(obj={})


if __name__ == '__main__':
    todo()
