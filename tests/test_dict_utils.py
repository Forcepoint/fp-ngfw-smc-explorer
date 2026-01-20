#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
import pytest
from smc_explorer.dict_utils import cleanup_dict


def test_cleanup_dict_skip_simple_keys():
    """Test skipping simple keys from a flat dictionary."""
    data = {
        "name": "example",
        "password": "secret",
        "email": "user@example.com",
    }
    result = cleanup_dict(data, {"password"}, set(), False)
    assert result == {"name": "example", "email": "user@example.com"}


def test_cleanup_dict_skip_multiple_keys():
    """Test skipping multiple keys."""
    data = {
        "name": "example",
        "password": "secret",
        "api_key": "hidden",
        "timeout": 30,
    }
    result = cleanup_dict(data, {"password", "api_key"}, set(), False)
    assert result == {"name": "example", "timeout": 30}


def test_cleanup_dict_nested_dictionaries():
    """Test skipping keys in nested dictionaries."""
    data = {
        "name": "example",
        "password": "secret",
        "config": {
            "timeout": 30,
            "api_key": "hidden",
            "host": "localhost",
        },
    }
    result = cleanup_dict(data, {"password", "api_key"}, set(), False)
    assert result == {
        "name": "example",
        "config": {"timeout": 30, "host": "localhost"},
    }


def test_cleanup_dict_with_lists():
    """Test skipping keys in lists containing dictionaries."""
    data = {
        "items": [
            {"id": 1, "secret": "data1"},
            {"id": 2, "secret": "data2"},
        ]
    }
    result = cleanup_dict(data, {"secret"}, set(), False)
    assert result == {"items": [{"id": 1}, {"id": 2}]}


def test_cleanup_dict_complex_nested_structure():
    """Test the example from the docstring."""
    data = {
        "name": "example",
        "password": "secret",
        "config": {
            "timeout": 30,
            "api_key": "hidden",
            "settings": [
                {"enabled": True, "token": "abc123"},
                {"enabled": False, "token": "def456"},
            ],
        },
        "items": [
            {"id": 1, "secret": "data1"},
            {"id": 2, "secret": "data2"},
        ],
    }
    result = cleanup_dict(data, {"password", "api_key", "token", "secret"}, set(), False)
    expected = {
        "name": "example",
        "config": {
            "timeout": 30,
            "settings": [{"enabled": True}, {"enabled": False}],
        },
        "items": [{"id": 1}, {"id": 2}],
    }
    assert result == expected


def test_cleanup_dict_empty_dict():
    """Test with an empty dictionary."""
    result = cleanup_dict({}, {"password"}, set(), False)
    assert result == {}


def test_cleanup_dict_no_keys_to_skip():
    """Test when no keys should be skipped."""
    data = {"name": "example", "email": "user@example.com"}
    result = cleanup_dict(data, set(), set(), False)
    assert result == data


def test_cleanup_dict_all_keys_skipped():
    """Test when all keys are skipped."""
    data = {"password": "secret", "api_key": "hidden"}
    result = cleanup_dict(data, {"password", "api_key"}, set(), False)
    assert result == {}


def test_cleanup_dict_keys_to_keep():
    """Test keeping only specific keys."""
    data = {
        "name": "example",
        "password": "secret",
        "email": "user@example.com",
        "timeout": 30,
    }
    result = cleanup_dict(data, set(), {"name", "email"}, False)
    assert result == {"name": "example", "email": "user@example.com"}


def test_cleanup_dict_keys_to_keep_and_skip():
    """Test combining keys_to_keep and keys_to_skip."""
    data = {
        "name": "example",
        "password": "secret",
        "email": "user@example.com",
        "timeout": 30,
    }
    # Keep name and email, but skip password
    result = cleanup_dict(data, {"password"}, {"name", "email"}, False)
    assert result == {"name": "example", "email": "user@example.com"}


def test_cleanup_dict_remove_falsy_false():
    """Test removing False values when remove_falsy is True."""
    data = {
        "enabled": False,
        "active": True,
        "count": 0,
        "value": -1,
        "name": "test",
    }
    result = cleanup_dict(data, set(), set(), remove_falsy=True)
    assert result == {"active": True, "count": 0, "name": "test"}


def test_cleanup_dict_remove_falsy_nested():
    """Test removing False values in nested structures."""
    data = {
        "config": {
            "enabled": False,
            "active": True,
            "items": [
                {"valid": True, "disabled": False},
                {"valid": False, "code": -1},
            ],
        }
    }
    result = cleanup_dict(data, set(), set(), remove_falsy=True)
    expected = {
        "config": {
            "active": True,
            "items": [{"valid": True}, {}],
        }
    }
    assert result == expected


def test_cleanup_dict_wildcard_pattern():
    """Test pattern matching with wildcards."""
    data = {
        "user_password": "secret1",
        "admin_password": "secret2",
        "username": "john",
        "email": "user@example.com",
    }
    result = cleanup_dict(data, {"*password"}, set(), False)
    assert result == {"username": "john", "email": "user@example.com"}


def test_cleanup_dict_wildcard_pattern_complex():
    """Test pattern matching with multiple wildcards."""
    data = {
        "api_key": "key1",
        "api_secret": "secret1",
        "api_token": "token1",
        "username": "john",
    }
    result = cleanup_dict(data, {"api_*"}, set(), False)
    assert result == {"username": "john"}


def test_cleanup_dict_case_insensitive_pattern():
    """Test that pattern matching is case insensitive."""
    data = {
        "Password": "secret",
        "PASSWORD": "secret2",
        "username": "john",
    }
    result = cleanup_dict(data, {"password"}, set(), False)
    assert result == {"username": "john"}


def test_cleanup_dict_preserves_non_dict_values():
    """Test that non-dict values are preserved unchanged."""
    data = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "none": None,
        "list": [1, 2, 3],
    }
    result = cleanup_dict(data, set(), set(), False)
    assert result == data


def test_cleanup_dict_empty_list():
    """Test with empty lists."""
    data = {"items": [], "name": "test"}
    result = cleanup_dict(data, set(), set(), False)
    assert result == data


def test_cleanup_dict_deeply_nested():
    """Test with deeply nested structures."""
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "password": "secret",
                    "data": "value",
                }
            }
        }
    }
    result = cleanup_dict(data, {"password"}, set(), False)
    expected = {"level1": {"level2": {"level3": {"data": "value"}}}}
    assert result == expected


def test_cleanup_dict_mixed_list_content():
    """Test lists with mixed content types."""
    data = {
        "items": [
            {"id": 1, "password": "secret"},
            "plain_string",
            42,
            {"id": 2, "name": "test"},
        ]
    }
    result = cleanup_dict(data, {"password"}, set(), False)
    expected = {"items": [{"id": 1}, "plain_string", 42, {"id": 2, "name": "test"}]}
    assert result == expected


def test_cleanup_dict_empty_keys_to_keep():
    """Test that empty keys_to_keep keeps all keys (except skipped ones)."""
    data = {"name": "example", "email": "user@example.com", "password": "secret"}
    result = cleanup_dict(data, {"password"}, set(), False)
    assert result == {"name": "example", "email": "user@example.com"}
