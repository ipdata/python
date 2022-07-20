"""This is the official IPData Command Line Interface.

Use it to do one-off lookups or high throughput bulk lookups. With a ton of convenience features eg.
copying a result to the clipboard with '-c', pretty printing results in easy to parse panels with '-p' and more!

    $ ipdata --help
    Usage: ipdata [OPTIONS] COMMAND [ARGS]...

      Welcome to the ipdata CLI

    Options:
      --api-key TEXT  Your ipdata API Key. Get one for free from
                      https://ipdata.co/sign-up.html
      --help          Show this message and exit.

    Commands:
      lookup*
      batch
      init
      usage
      validate   

    $ ipdata
    Your IP

    $ ipdata 1.1.1.1 -f ip -f asn
    {
      "ip": "1.1.1.1",
      "asn": {
        "asn": "AS13335",
        "name": "Cloudflare, Inc.",
        "domain": "cloudflare.com",
        "route": "1.1.1.0/24",
        "type": "business"
      },
      "status": 200
    }

    $ ipdata 1.1.1.1 -f ip -f asn -c 
    📋️ Copied result to clipboard!  

    $ ipdata 8.8.8.8 -f ip -p
    ╭───────────────╮
    │ country_name  │
    │ United States │
    ╰───────────────╯ 
"""
import csv
import io
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from sys import stderr

import click
import pyperclip
from click_default_group import DefaultGroup
from rich import print, print_json
from rich.columns import Columns
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress
from rich.tree import Tree

from .lolcat import LolCat
from .geofeeds import Geofeed, GeofeedValidationError
from .ipdata import DotDict, IPData

console = Console()

FORMAT = "%(message)s"
logging.basicConfig(
    level="ERROR", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("rich")

API_KEY_FILE = f"{Path.home()}/.ipdata"


def _lookup(ipdata, *args, **kwargs):
    """
    Wrapper for looking up individual resources with error handling. Takes the same arguments and returns the same response as ipdata.lookup.
    """
    try:
        response = ipdata.lookup(*args, **kwargs)
    except Exception as e:
        log.error(e)
    else:
        return response


def print_ascii_logo():
    """
    Print cool ascii logo with lolcat.
    """
    options = DotDict({"animate": False, "os": 6, "spread": 3.0, "freq": 0.1})
    logo = """
 _           _       _        
(_)_ __   __| | __ _| |_ __ _ 
| | '_ \ / _` |/ _` | __/ _` |
| | |_) | (_| | (_| | || (_| |
|_| .__/ \__,_|\__,_|\__\__,_|
  |_|
    """
    lol = LolCat()
    lol.cat(io.StringIO(logo), options)


def pretty_print_data(data):
    """
    Users rich to generate panels for individual API response fields for better readability!

    :param data: the response from ipdata.lookup
    """
    # we print single value panels first then multiple value panels for better organization
    single_value_panels = []
    multiple_value_panels = []

    # if data is empty do nothing
    if not data:
        return

    # push the blocklists field up a level, it's usually nested under the threat data
    if data.get("threat", {}).get("blocklists"):
        data["blocklists"] = data.get("threat", {}).pop("blocklists")

    # generate panels!
    for key, value in data.items():
        # simple case
        if type(value) in [str, bool]:
            single_value_panels.append(
                Panel(f"[b]{key}[/b]\n[yellow]{value}", expand=True)
            )

        # if the value is a dictionary we generate a tree inside a panel
        if type(value) is dict:
            tree = Tree(key)
            for k, v in value.items():
                if key == "threat":
                    if v:
                        sub_tree = tree.add(f"[b]{k}[/b]\n[bright_red]{v}")
                    else:
                        sub_tree = tree.add(f"[b]{k}[/b]\n[green]{v}")
                else:
                    sub_tree = tree.add(f"[b]{k}[/b]\n[yellow]{v}")
            multiple_value_panels.append(Panel(tree, expand=False))

        # if value if a list we generate nested trees
        if type(value) is list:
            tree = Tree(key)
            for item in value:
                branch = tree.add("")
                for k, v in item.items():
                    _ = branch.add(f"[b]{k}[/b]\n[yellow]{v}")
            multiple_value_panels.append(Panel(tree, expand=False))

    # print the single value panels to the console
    console.print(Columns(single_value_panels), overflow="ignore", crop=False)

    # print the multiple value panels to the console
    console.print(Columns(multiple_value_panels), overflow="ignore", crop=False)


@click.group(
    help="Welcome to the ipdata CLI",
    cls=DefaultGroup,
    default_if_no_args=True,
    default="lookup",
)
@click.option(
    "--api-key",
    required=False,
    default=None,
    help="Your ipdata API Key. Get one for free from https://ipdata.co/sign-up.html",
)
@click.pass_context
def cli(ctx, api_key):
    """
    This is the main entry point for the CLI. We first check for the presence of an API key at ~/.ipdata and make it accessible to all other commands in our group.
    Note that the 'init' and 'validate' commands are the only ones that can run without an API key present.

    :param api_key: A valid IPData API key
    """
    ctx.ensure_object(dict)
    key = ctx.obj["api-key"] = (
        Path(API_KEY_FILE).read_text() if Path(API_KEY_FILE).exists() else None
    )

    # Allow init and validate to run without an API key
    if not ctx.invoked_subcommand in ["init", "validate"] and key is None:
        print(
            f'Please initialize the cli by running "ipdata init <api key>" then try again',
            file=stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument(
    "api-key",
    required=True,
    type=str,
)
def init(api_key):
    """
    Initialize the CLI by setting an API key.

    :param api_key: A valid IPData API key
    """
    ipdata = IPData(api_key)

    # We verify that the API key can successfully make requests by making one
    with console.status("Verifying key ...", spinner="dots12"):
        response = _lookup(ipdata, "8.8.8.8")

    # Handle success
    if response.status == 200:
        with open(API_KEY_FILE, "w") as f:
            f.write(api_key)
        print_ascii_logo()
        print(f"✨ Successfully initialized.")
    else:
        # Handle failure
        print(
            f"Initialization failed. Error: {response.status}): {response.message}",
            file=stderr,
        )


@cli.command()
@click.option("--api-key", "-k", required=False, default=None, help="ipdata API Key")
@click.pass_context
def usage(ctx, api_key):
    """
    Get today's usage. Quota resets every day at 00:00 UTC.
    """
    api_key = ctx.obj["api-key"]
    ipdata = IPData(api_key)
    with console.status("Getting usage ...", spinner="dots12"):
        response = _lookup(ipdata)
    print(f"{int(response.count):,}")


@cli.command(default=True)
@click.argument("resource", required=False, type=str, default="")
@click.option(
    "--fields",
    "-f",
    required=False,
    multiple=True,
    default=[],
)
@click.option(
    "--exclude",
    "-e",
    required=False,
    multiple=True,
    default=[],
)
@click.option("--api-key", "-k", required=False, default=None, help="ipdata API Key")
@click.option(
    "--pretty-print",
    "-p",
    is_flag=True,
    required=False,
    default=False,
    help="Pretty prints results as panels",
)
@click.option(
    "--raw",
    "-r",
    is_flag=True,
    required=False,
    default=False,
    help="Disable pretty printing",
)
@click.option(
    "--copy",
    "-c",
    is_flag=True,
    required=False,
    default=False,
    help="Copy the result to the clipboard",
)
@click.pass_context
def lookup(ctx, resource, fields, api_key, pretty_print, raw, copy, exclude):
    """
    Lookup resources by using the IPData class methods.

    :param resource: The resource to lookup
    :param fields: A list of supported fields passed as multiple parameters eg. "... -f ip -f country_name"
    :param api_key: A valid API key
    :param pretty_print: Whether to pretty print the response with panels
    :param raw: Whether to print raw unformatted but syntax-highlighted JSON
    :param copy: Copy the response to the clipboard
    """
    api_key = api_key if api_key else ctx.obj["api-key"]
    ipdata = IPData(api_key)

    # enforce mutual exclusivity of fields and exclude
    if exclude and fields:
        raise click.ClickException(
            "'--fields / -f' and '--exclude / -e' are mutually exclusive."
        )

    # if the user wants to exclude some fields, get all the fields in fields that are not in exclude
    if exclude:
        fields = set(ipdata.valid_fields).difference(set(exclude))

    with console.status(
        f"""Looking up {resource if resource else "this device's IP address"}""",
        spinner="dots12",
    ):
        data = _lookup(ipdata, resource, fields=fields)

    if copy:
        pyperclip.copy(json.dumps(data))
        print(f"📋️ Copied result to clipboard!")
    elif raw:
        print(data)
    elif pretty_print:
        pretty_print_data(data)
    else:
        print_json(data=data)


def chunks(lst, n=100):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def process(resources, processor, fields):
    """Farm out work to worker threads."""
    n_workers = os.cpu_count()
    with ThreadPoolExecutor(n_workers) as executor:
        futures = [
            executor.submit(processor, chunk, fields) for chunk in chunks(resources)
        ]
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                log.error(e)
            else:
                yield result


@cli.command()
@click.argument("input", required=True, type=click.File(mode="r", encoding="utf-8"))
@click.option("--fields", "-f", required=False, multiple=True)
@click.option(
    "--exclude",
    "-e",
    required=False,
    multiple=True,
    default=[],
)
@click.option(
    "--output", "-o", required=True, type=click.File(mode="w", encoding="utf-8")
)
@click.option(
    "--format",
    required=False,
    type=click.Choice(("JSON", "CSV"), case_sensitive=False),
    default="JSON",
    help="Output file format",
)
@click.pass_context
def batch(ctx, input, fields, output, format, exclude):
    """
    Batch command for doing fast bulk processing.

    :param input: A list of resources to lookup either IP addresses or ASNs. You could mix them however this could break output processing when writing to CSV
    :param fields: A list of valid fields to extract from the individual responses
    :param output: The path to write the results to
    :param format: The format to write the results to. When using the CSV format it is required to provide fields.
    """

    if format == "CSV" and not fields:
        print(
            f'You need to specify a "--fields" argument with a list of fields to extract to get results in CSV. To get entire responses use JSON.',
            file=stderr,
        )
        return

    # enforce mutual exclusivity of fields and exclude
    if exclude and fields:
        raise click.ClickException(
            "'--fields / -f' and '--exclude / -e' are mutually exclusive."
        )

    # if the user wants to exclude some fields, get all the fields in fields that are not in exclude
    if exclude:
        fields = set(ipdata.valid_fields).difference(set(exclude))

    # Prepare requests
    ipdata = IPData(ctx.obj["api-key"])
    resources = [resource.strip() for resource in input.readlines()]
    bulk_results = process(resources, ipdata.bulk, fields)

    # Prepare CSV writing by expanding fieldnames eg. asn to asn, name, domain etc
    csv_writer = None
    fieldnames = []
    for field in fields:
        if field == "asn":
            fieldnames += [
                f"asn_{sub_field}"
                for sub_field in ["asn", "name", "domain", "route", "type"]
            ]
            continue
        if field == "company":
            fieldnames += [
                f"company_{sub_field}"
                for sub_field in ["asn", "name", "domain", "network", "type"]
            ]
            continue
        if field == "threat":
            fieldnames += [
                f"asn_{sub_field}"
                for sub_field in [
                    "is_tor",
                    "is_icloud_relay",
                    "is_proxy",
                    "is_datacenter",
                    "is_anonymous",
                    "is_known_attacker",
                    "is_known_abuser",
                    "is_threat",
                    "is_bogon",
                    "blocklists",
                ]
            ]
            continue
        if field in ipdata.valid_fields:
            fieldnames += [field]

    # Do lookups concurrenctly using threads in batches of 100 each
    with Progress() as progress:
        # update progress bar
        task = progress.add_task("[green]Processing...", total=len(resources))

        # write individual results to file
        for bulk_result in bulk_results:
            for result in bulk_result.get("responses", {}):
                progress.update(task, advance=1)
                if format == "JSON":
                    output.write(f"{json.dumps(result)}\n")
                if format == "CSV":
                    if not csv_writer:
                        # create writer if none exists
                        csv_writer = csv.DictWriter(output, fieldnames=fieldnames)
                        csv_writer.writeheader()

                    # prepare row
                    row = {}
                    for field, value in result.items():
                        if type(value) is dict:
                            for k, v in result[field].items():
                                row[f"{field}_{k}"] = v
                        else:
                            row[field] = value

                    # ensure no unexpected fields
                    try:
                        # handle when dict fields are none eg. when asn, company or carrier are empty
                        row_copy = row.copy()
                        for key in row_copy:
                            if key not in fieldnames:
                                row.pop(key)

                        # write results
                        csv_writer.writerow(row)
                    except ValueError as e:
                        log.error(f"Error writing row: {row}. Error: {e}")


@cli.command()
@click.argument("feed", required=True, type=str)
def validate(feed):
    """
    Validates a geofeed file.

    :param feed: Either a valid URL (with the https:// path) or a file path
    """
    geofeed = Geofeed(feed)
    valid = True
    for entry in geofeed:
        if type(entry) is GeofeedValidationError:
            log.error(entry)
            valid = False
        else:
            try:
                entry.validate()

                # keep count of valid entries
                geofeed.valid_count += 1
            except GeofeedValidationError as e:
                valid = False
                log.error(e)

    if geofeed.total_count == 0:
        log.error(f"The provided geofeed is empty")

    valid_percentage = geofeed.valid_count / geofeed.total_count * 100
    print(
        f"{geofeed.source} has {geofeed.valid_count:,} ({valid_percentage:.2f}%) valid entries."
    )

    if not valid:
        sys.exit(1)

    print(
        "✨ Success! Your geofeed is valid and ready for publishing! Send an email to corrections@ipdata.co with the URL of this feed."
    )


if __name__ == "__main__":
    cli()
