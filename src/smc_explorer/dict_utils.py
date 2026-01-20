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
from typing import Any
import fnmatch
import re

def cleanup_dict(
    data: dict[str, Any],
    keys_to_skip: set[str],
    keys_to_keep: set[str],
    remove_falsy: bool = False,
) -> dict[str, Any]:
    """
    Recursively skip specified keys from a dictionary structure.
    Handles nested dictionaries and lists containing dictionaries.

    Args:
        data: The data structure to process (dict, list, or any other type).
        keys_to_skip: Set of key names to skip/remove from dictionaries.

    Returns:
        New data structure with specified keys removed.

    Example:
        >>> data = {
             "name": "example",
             "password": "secret",
             "config": {
                 "timeout": 30,
                 "api_key": "hidden",
                 "settings": [
                     {"enabled": True, "token": "abc123"},
                     {"enabled": False, "token": "def456"}
                 ]
             },
             "items": [
                 {"id": 1, "secret": "data1"},
                 {"id": 2, "secret": "data2"}
             ]
         }
        >>> cleanup_dict(data, {"password", "api_key", "token", "secret"})
        {'name': 'example', 'config': {'timeout': 30, 'settings': [{'enabled': True}, {'enabled': False}]}, 'items': [{'id': 1}, {'id': 2}]}
    """
    return _skip_keys_recursive(data, keys_to_skip, keys_to_keep, remove_falsy)


def key_match(key: str, match_set: set[str]) -> bool:
    if not match_set:
        return True
    for pattern in match_set:
        regex = fnmatch.translate(pattern)
        if re.match(regex, key, re.IGNORECASE):
            return True
    return False

def _skip_keys_recursive(
    data: Any,
    keys_to_skip: set[str],
    keys_to_keep: set[str],
    remove_falsy: bool = False,
) -> Any:
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if keys_to_skip and key_match(key, keys_to_skip):
                continue

            if keys_to_keep and not key_match(key, keys_to_keep):
                continue

            if remove_falsy and (value is False or value == -1):
                continue
            # if remove_falsy and value != [] and value != {} and value != 0 and (not value or value == -1):
            #     continue

            result[key] = _skip_keys_recursive(value, keys_to_skip, keys_to_keep, remove_falsy)
        return result

    if isinstance(data, list):
        return [_skip_keys_recursive(item, keys_to_skip, keys_to_keep, remove_falsy) for item in data]

    return data
