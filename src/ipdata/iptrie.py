"""
IP Trie module for efficient IP address and CIDR prefix lookups.

This module provides a dictionary-like data structure that supports both IPv4 and IPv6
addresses with longest-prefix matching using Patricia tries.

Example:
    >>> ip_trie = IPTrie()
    >>> ip_trie["192.168.0.0/16"] = "private-network"
    >>> ip_trie["192.168.1.100"]
    'private-network'
    >>> ip_trie.parent("192.168.1.100")
    '192.168.0.0/16'
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterator
from typing import TypeVar, Generic

from pytricia import PyTricia

T = TypeVar("T")


class IPTrieError(Exception):
    """Base exception for IPTrie errors."""

    pass


class InvalidIPError(IPTrieError):
    """Raised when an invalid IP address or network is provided."""

    pass


class KeyNotFoundError(IPTrieError, KeyError):
    """Raised when a key is not found in the trie."""

    pass


def _normalize_ip_key(key: str) -> tuple[str, bool]:
    """
    Validate and normalize an IP address or network string.

    Args:
        key: An IP address or CIDR notation string.

    Returns:
        A tuple of (normalized_key, is_ipv6).

    Raises:
        InvalidIPError: If the key is not a valid IP address or network.
    """
    if not isinstance(key, str):
        raise InvalidIPError(f"Key must be a string, got {type(key).__name__}")

    key = key.strip()
    if not key:
        raise InvalidIPError("Key cannot be empty")

    try:
        if "/" in key:
            network = ipaddress.ip_network(key, strict=False)
            return str(network), isinstance(network, ipaddress.IPv6Network)
        else:
            address = ipaddress.ip_address(key)
            return str(address), isinstance(address, ipaddress.IPv6Address)
    except ValueError as e:
        raise InvalidIPError(f"Invalid IP address or network: {key!r}") from e


class IPTrie(Generic[T]):
    """
    A trie-based container for IP addresses and CIDR prefixes.

    Supports both IPv4 and IPv6 addresses with longest-prefix matching.
    Keys can be individual IP addresses or CIDR notation networks.

    This class uses Patricia tries internally for efficient lookups,
    providing O(k) lookup time where k is the prefix length.

    Attributes:
        IPV4_BITS: Number of bits in IPv4 addresses (32).
        IPV6_BITS: Number of bits in IPv6 addresses (128).

    Example:
        >>> ip_trie = IPTrie[str]()
        >>> ip_trie["10.0.0.0/8"] = "class-a-private"
        >>> ip_trie["10.1.0.0/16"] = "datacenter"
        >>> ip_trie["10.1.2.3"]
        'datacenter'
        >>> ip_trie.parent("10.1.2.3")
        '10.1.0.0/16'
    """

    IPV4_BITS: int = 32
    IPV6_BITS: int = 128

    def __init__(self) -> None:
        """Initialize an empty IPTrie."""
        self._ipv4: PyTricia = PyTricia(self.IPV4_BITS)
        self._ipv6: PyTricia = PyTricia(self.IPV6_BITS)

    def _get_trie(self, is_ipv6: bool) -> PyTricia:
        """Return the appropriate trie based on IP version."""
        return self._ipv6 if is_ipv6 else self._ipv4

    def __setitem__(self, key: str, value: T) -> None:
        """
        Set a value for an IP address or network prefix.

        Args:
            key: An IP address or CIDR notation network string.
            value: The value to associate with the key.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.

        Example:
            >>> ip_trie["192.168.1.0/24"] = "local-network"
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        self._get_trie(is_ipv6)[normalized_key] = value

    def __getitem__(self, key: str) -> T:
        """
        Get the value for an IP address using longest-prefix matching.

        Args:
            key: An IP address or CIDR notation network string.

        Returns:
            The value associated with the longest matching prefix.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.
            KeyNotFoundError: If no matching prefix is found.

        Example:
            >>> ip_trie["192.168.1.100"]
            'local-network'
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        trie = self._get_trie(is_ipv6)

        if normalized_key not in trie:
            raise KeyNotFoundError(key)

        return trie[normalized_key]

    def get(self, key: str, default: T | None = None) -> T | None:
        """
        Get the value for an IP address, returning default if not found.

        Args:
            key: An IP address or CIDR notation network string.
            default: Value to return if key is not found.

        Returns:
            The value associated with the longest matching prefix,
            or the default value if not found.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.

        Example:
            >>> ip_trie.get("8.8.8.8", "unknown")
            'unknown'
        """
        try:
            return self[key]
        except KeyNotFoundError:
            return default

    def __delitem__(self, key: str) -> None:
        """
        Delete an exact prefix from the trie.

        Args:
            key: An IP address or CIDR notation network string.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.
            KeyNotFoundError: If the exact prefix is not found.

        Example:
            >>> del ip_trie["192.168.1.0/24"]
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        trie = self._get_trie(is_ipv6)

        if not trie.has_key(normalized_key):
            raise KeyNotFoundError(key)

        del trie[normalized_key]

    def __contains__(self, key: object) -> bool:
        """
        Check if an IP address matches any prefix in the trie.

        Args:
            key: An IP address or CIDR notation network string.

        Returns:
            True if a matching prefix exists, False otherwise.

        Example:
            >>> "192.168.1.100" in ip_trie
            True
        """
        if not isinstance(key, str):
            return False

        try:
            normalized_key, is_ipv6 = _normalize_ip_key(key)
            return normalized_key in self._get_trie(is_ipv6)
        except InvalidIPError:
            return False

    def has_key(self, key: str) -> bool:
        """
        Check if an exact prefix exists in the trie.

        Unlike __contains__, this checks for an exact match rather than
        longest-prefix matching.

        Args:
            key: An IP address or CIDR notation network string.

        Returns:
            True if the exact prefix exists, False otherwise.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.

        Example:
            >>> ip_trie.has_key("192.168.1.0/24")
            True
            >>> ip_trie.has_key("192.168.1.0/25")
            False
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        return self._get_trie(is_ipv6).has_key(normalized_key)

    def parent(self, key: str) -> str | None:
        """
        Get the longest matching prefix for an IP address.

        Args:
            key: An IP address or CIDR notation network string.

        Returns:
            The longest matching prefix as a string, or None if not found.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.

        Example:
            >>> ip_trie.parent("192.168.1.100")
            '192.168.1.0/24'
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        trie = self._get_trie(is_ipv6)

        if normalized_key not in trie:
            return None

        return trie.get_key(normalized_key)

    def children(self, key: str) -> list[str]:
        """
        Get all prefixes that are more specific than the given prefix.

        Args:
            key: A CIDR notation network string.

        Returns:
            A list of all more specific prefixes.

        Raises:
            InvalidIPError: If the key is not a valid IP address or network.

        Example:
            >>> ip_trie.children("192.168.0.0/16")
            ['192.168.1.0/24', '192.168.2.0/24']
        """
        normalized_key, is_ipv6 = _normalize_ip_key(key)
        trie = self._get_trie(is_ipv6)

        try:
            return list(trie.children(normalized_key))
        except KeyError:
            return []

    def __len__(self) -> int:
        """
        Return the total number of prefixes stored.

        Returns:
            The combined count of IPv4 and IPv6 prefixes.

        Example:
            >>> len(ip_trie)
            3
        """
        return len(self._ipv4) + len(self._ipv6)

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over all prefixes in the trie.

        Yields:
            All stored prefixes (IPv4 first, then IPv6).

        Example:
            >>> list(ip_trie)
            ['192.168.1.0/24', '10.0.0.0/8', '2001:db8::/32']
        """
        yield from self._ipv4
        yield from self._ipv6

    def keys(self) -> Iterator[str]:
        """
        Return an iterator over all prefixes.

        Yields:
            All stored prefixes.
        """
        return iter(self)

    def values(self) -> Iterator[T]:
        """
        Return an iterator over all values.

        Yields:
            All stored values.
        """
        for key in self:
            try:
                if ":" in key:
                    yield self._ipv6[key]
                else:
                    yield self._ipv4[key]
            except KeyError:
                continue

    def items(self) -> Iterator[tuple[str, T]]:
        """
        Return an iterator over all (prefix, value) pairs.

        Yields:
            Tuples of (prefix, value).
        """
        for key in self:
            try:
                if ":" in key:
                    yield key, self._ipv6[key]
                else:
                    yield key, self._ipv4[key]
            except KeyError:
                continue

    def clear(self) -> None:
        """Remove all entries from the trie."""
        self._ipv4 = PyTricia(self.IPV4_BITS)
        self._ipv6 = PyTricia(self.IPV6_BITS)

    def __repr__(self) -> str:
        """Return a string representation of the IPTrie."""
        ipv4_count = len(self._ipv4)
        ipv6_count = len(self._ipv6)
        return f"IPTrie(ipv4_prefixes={ipv4_count}, ipv6_prefixes={ipv6_count})"

    def __bool__(self) -> bool:
        """Return True if the trie contains any entries."""
        return len(self) > 0