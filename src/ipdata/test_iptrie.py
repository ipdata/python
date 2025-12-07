"""
Unit tests for the IPTrie module.

Run with: pytest test_iptrie.py -v
"""

import pytest

from .iptrie import IPTrie, InvalidIPError, KeyNotFoundError, _normalize_ip_key


class TestNormalizeIPKey:
    """Tests for the _normalize_ip_key helper function."""

    def test_valid_ipv4_address(self):
        key, is_ipv6 = _normalize_ip_key("192.168.1.1")
        assert key == "192.168.1.1"
        assert is_ipv6 is False

    def test_valid_ipv4_network(self):
        key, is_ipv6 = _normalize_ip_key("192.168.1.0/24")
        assert key == "192.168.1.0/24"
        assert is_ipv6 is False

    def test_ipv4_network_normalization(self):
        # Non-strict mode normalizes host bits
        key, is_ipv6 = _normalize_ip_key("192.168.1.100/24")
        assert key == "192.168.1.0/24"
        assert is_ipv6 is False

    def test_valid_ipv6_address(self):
        key, is_ipv6 = _normalize_ip_key("2001:db8::1")
        assert key == "2001:db8::1"
        assert is_ipv6 is True

    def test_valid_ipv6_network(self):
        key, is_ipv6 = _normalize_ip_key("2001:db8::/32")
        assert key == "2001:db8::/32"
        assert is_ipv6 is True

    def test_ipv6_normalization(self):
        key, is_ipv6 = _normalize_ip_key("2001:0db8:0000:0000:0000:0000:0000:0001")
        assert key == "2001:db8::1"
        assert is_ipv6 is True

    def test_whitespace_handling(self):
        key, is_ipv6 = _normalize_ip_key("  192.168.1.1  ")
        assert key == "192.168.1.1"

    def test_invalid_ip_raises_error(self):
        with pytest.raises(InvalidIPError, match="Invalid IP address"):
            _normalize_ip_key("not-an-ip")

    def test_empty_string_raises_error(self):
        with pytest.raises(InvalidIPError, match="cannot be empty"):
            _normalize_ip_key("")

    def test_non_string_raises_error(self):
        with pytest.raises(InvalidIPError, match="must be a string"):
            _normalize_ip_key(12345)  # type: ignore

    def test_none_raises_error(self):
        with pytest.raises(InvalidIPError, match="must be a string"):
            _normalize_ip_key(None)  # type: ignore


class TestIPTrieBasicOperations:
    """Tests for basic trie operations."""

    def test_setitem_and_getitem_ipv4(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.1.0/24"] = "local-network"
        assert ip_trie["192.168.1.100"] == "local-network"

    def test_setitem_and_getitem_ipv6(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["2001:db8::/32"] = "documentation"
        assert ip_trie["2001:db8::1"] == "documentation"

    def test_getitem_not_found_raises_error(self):
        ip_trie: IPTrie[str] = IPTrie()
        with pytest.raises(KeyNotFoundError):
            _ = ip_trie["192.168.1.1"]

    def test_get_with_default(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert ip_trie.get("192.168.1.1") is None
        assert ip_trie.get("192.168.1.1", "default") == "default"

    def test_get_existing_key(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "class-a"
        assert ip_trie.get("10.1.2.3") == "class-a"

    def test_contains_ipv4(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.0.0/16"] = "private"
        assert "192.168.1.1" in ip_trie
        assert "10.0.0.1" not in ip_trie

    def test_contains_ipv6(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["2001:db8::/32"] = "docs"
        assert "2001:db8::1" in ip_trie
        assert "2001:db9::1" not in ip_trie

    def test_contains_invalid_key_returns_false(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert "not-an-ip" not in ip_trie
        assert 12345 not in ip_trie  # type: ignore

    def test_delitem(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.1.0/24"] = "test"
        assert "192.168.1.1" in ip_trie
        del ip_trie["192.168.1.0/24"]
        assert "192.168.1.1" not in ip_trie

    def test_delitem_not_found_raises_error(self):
        ip_trie: IPTrie[str] = IPTrie()
        with pytest.raises(KeyNotFoundError):
            del ip_trie["192.168.1.0/24"]

    def test_len(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert len(ip_trie) == 0
        ip_trie["10.0.0.0/8"] = "a"
        assert len(ip_trie) == 1
        ip_trie["192.168.0.0/16"] = "b"
        assert len(ip_trie) == 2
        ip_trie["2001:db8::/32"] = "c"
        assert len(ip_trie) == 3

    def test_bool_empty(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert not ip_trie

    def test_bool_non_empty(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "test"
        assert ip_trie


class TestIPTrieLongestPrefixMatching:
    """Tests for longest-prefix matching behavior."""

    def test_longest_prefix_match_ipv4(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "broad"
        ip_trie["10.1.0.0/16"] = "narrower"
        ip_trie["10.1.1.0/24"] = "specific"

        assert ip_trie["10.1.1.100"] == "specific"
        assert ip_trie["10.1.2.100"] == "narrower"
        assert ip_trie["10.2.0.1"] == "broad"

    def test_longest_prefix_match_ipv6(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["2001:db8::/32"] = "broad"
        ip_trie["2001:db8:1::/48"] = "specific"

        assert ip_trie["2001:db8:1::1"] == "specific"
        assert ip_trie["2001:db8:2::1"] == "broad"

    def test_parent_returns_matching_prefix(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.0.0/16"] = "network"
        ip_trie["192.168.1.0/24"] = "subnet"

        assert ip_trie.parent("192.168.1.100") == "192.168.1.0/24"
        assert ip_trie.parent("192.168.2.100") == "192.168.0.0/16"

    def test_parent_not_found(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert ip_trie.parent("192.168.1.1") is None


class TestIPTrieHasKey:
    """Tests for exact prefix matching."""

    def test_has_key_exact_match(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.1.0/24"] = "test"

        assert ip_trie.has_key("192.168.1.0/24") is True
        assert ip_trie.has_key("192.168.1.0/25") is False
        assert ip_trie.has_key("192.168.1.100") is False


class TestIPTrieIteration:
    """Tests for iteration methods."""

    def test_iter(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "a"
        ip_trie["192.168.0.0/16"] = "b"
        ip_trie["2001:db8::/32"] = "c"

        keys = list(ip_trie)
        assert len(keys) == 3
        assert "10.0.0.0/8" in keys
        assert "192.168.0.0/16" in keys
        assert "2001:db8::/32" in keys

    def test_keys(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "a"
        keys = list(ip_trie.keys())
        assert keys == ["10.0.0.0/8"]

    def test_values(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "value-a"
        ip_trie["192.168.0.0/16"] = "value-b"
        values = list(ip_trie.values())
        assert set(values) == {"value-a", "value-b"}

    def test_items(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "value-a"
        items = list(ip_trie.items())
        assert ("10.0.0.0/8", "value-a") in items


class TestIPTrieChildren:
    """Tests for the children method."""

    def test_children_returns_more_specific_prefixes(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "parent"
        ip_trie["10.1.0.0/16"] = "child1"
        ip_trie["10.2.0.0/16"] = "child2"
        ip_trie["192.168.0.0/16"] = "other"

        children = ip_trie.children("10.0.0.0/8")
        assert len(children) == 2
        assert "10.1.0.0/16" in children
        assert "10.2.0.0/16" in children

    def test_children_no_children(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "test"
        children = ip_trie.children("10.1.0.0/16")
        assert children == []


class TestIPTrieClear:
    """Tests for the clear method."""

    def test_clear_removes_all_entries(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "a"
        ip_trie["2001:db8::/32"] = "b"
        assert len(ip_trie) == 2

        ip_trie.clear()
        assert len(ip_trie) == 0
        assert "10.0.0.1" not in ip_trie


class TestIPTrieRepr:
    """Tests for string representation."""

    def test_repr_empty(self):
        ip_trie: IPTrie[str] = IPTrie()
        assert repr(ip_trie) == "IPTrie(ipv4_prefixes=0, ipv6_prefixes=0)"

    def test_repr_with_entries(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "a"
        ip_trie["192.168.0.0/16"] = "b"
        ip_trie["2001:db8::/32"] = "c"
        assert repr(ip_trie) == "IPTrie(ipv4_prefixes=2, ipv6_prefixes=1)"


class TestIPTrieValueTypes:
    """Tests for different value types."""

    def test_dict_values(self):
        ip_trie: IPTrie[dict] = IPTrie()
        ip_trie["10.0.0.0/8"] = {"name": "class-a", "owner": "acme"}
        result = ip_trie["10.1.2.3"]
        assert result == {"name": "class-a", "owner": "acme"}

    def test_list_values(self):
        ip_trie: IPTrie[list[str]] = IPTrie()
        ip_trie["10.0.0.0/8"] = ["tag1", "tag2"]
        result = ip_trie["10.1.2.3"]
        assert result == ["tag1", "tag2"]

    def test_none_value(self):
        ip_trie: IPTrie[None] = IPTrie()
        ip_trie["10.0.0.0/8"] = None
        assert ip_trie["10.1.2.3"] is None


class TestIPTrieEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_host_address_as_key(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["192.168.1.1"] = "single-host"
        assert ip_trie["192.168.1.1"] == "single-host"
        assert "192.168.1.2" not in ip_trie

    def test_default_routes(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["0.0.0.0/0"] = "default-v4"
        ip_trie["::/0"] = "default-v6"

        assert ip_trie["8.8.8.8"] == "default-v4"
        assert ip_trie["2001:4860:4860::8888"] == "default-v6"

    def test_overwrite_value(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["10.0.0.0/8"] = "original"
        ip_trie["10.0.0.0/8"] = "updated"
        assert ip_trie["10.1.2.3"] == "updated"

    def test_ipv4_mapped_ipv6(self):
        ip_trie: IPTrie[str] = IPTrie()
        ip_trie["::ffff:192.168.1.0/120"] = "mapped"
        assert ip_trie["::ffff:192.168.1.1"] == "mapped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])