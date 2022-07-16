"""
    Convenience methods for using the library.

    Example:
        >>> import ipdata
        >>> ipdata.api_key = <YOUR API KEY>
        >>> ipdata.lookup() # or ipdata.lookup("8.8.8.8") 
"""
from .ipdata import IPData

# Configuration
api_key = None
endpoint = "https://api.ipdata.co/"
default_client = None


def lookup(resource="", fields=[]):
    return _proxy("lookup", resource=resource, fields=fields)


def bulk(resources, fields=[]):
    return _proxy("bulk", resources, fields=fields)


def _proxy(method, *args, **kwargs):
    """Create an IPData client if one doesn't exist."""
    global default_client
    if not default_client:
        default_client = IPData(
            api_key,
            endpoint
        )

    fn = getattr(default_client, method)
    return fn(*args, **kwargs)
