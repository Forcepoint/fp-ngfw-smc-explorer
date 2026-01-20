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

from .str_utils import to_snake


def dict_to_hcl(data: dict[str, Any], indent: int = 0, use_blocks: bool = True) -> str:
    """
    Convert a Python dictionary to HCL (HashiCorp Configuration Language) format.
    Can use either block syntax (terraform-style) or attribute syntax.

    Args:
        data: Dictionary to convert to HCL.
        indent: Current indentation level (used for recursion).
        use_blocks: Whether to use terraform block syntax for dictionaries and lists of dictionaries.

    Returns:
        String representation in HCL format.

    Example:
        >>> dict_to_hcl({
        ...     "resource": {
        ...         "aws_instance": {
        ...             "web": {"ami": "ami-123", "instance_type": "t2.micro"}
        ...         }
        ...     }
        ... }, use_blocks=True)
    """
    lines = []
    indent_str = "  " * indent

    for key, value in data.items():
        key_tf = to_snake(key).lower()

        if use_blocks and isinstance(value, dict) and value:
            # Use block format for dictionaries
            block = _dict_to_block(value, key_tf, indent)
            lines.append(block)
        elif (
            use_blocks
            and isinstance(value, list)
            and value
            and all(isinstance(item, dict) for item in value)
        ):
            # Use block format for lists of dictionaries
            for item in value:
                if item:  # Skip empty dicts
                    block = _dict_to_block(item, key_tf, indent)
                    lines.append(block)
        elif use_blocks and isinstance(value, list) and not value:
            # Skip empty lists in block mode
            continue
        else:
            # Use attribute assignment
            hcl_value = _value_to_hcl(
                value, indent + 1, as_block=use_blocks, block_name=key_tf
            )
            lines.append(f"{indent_str}{key_tf} = {hcl_value}")

    return "\n".join(lines)


def _value_to_hcl(
    value: Any, indent: int = 0, as_block: bool = False, block_name: str = ""
) -> str:
    """
    Convert a Python value to its HCL representation.

    Args:
        value: Value to convert.
        indent: Current indentation level.
        as_block: Whether to format dictionaries as blocks instead of attributes.
        block_name: Name for the block when as_block is True.

    Returns:
        String representation of the value in HCL format.
    """
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return _string_to_hcl(value)
    elif isinstance(value, list):
        return _list_to_hcl(value, indent, as_block, block_name)
    elif isinstance(value, dict):
        return _dict_to_hcl_value(value, indent, as_block, block_name)
    else:
        return f'"{str(value)}"'


def _string_to_hcl(value: str) -> str:
    """Convert a string value to HCL format with proper escaping."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _list_to_hcl(value: list, indent: int, as_block: bool, block_name: str) -> str:
    """Convert a list to HCL format."""
    if not value:
        return "[]"

    # Check if this is a list of dictionaries - format as multiple blocks
    if _is_dict_list(value) and as_block:
        return _dict_list_to_blocks(value, block_name, indent)
    else:
        # Regular list - format as array
        elements = [_value_to_hcl(item, indent) for item in value]
        return f"[{', '.join(elements)}]"


def _dict_to_hcl_value(
    value: dict, indent: int, as_block: bool, block_name: str
) -> str:
    """Convert a dictionary to HCL format."""
    if not value:
        return "{}"

    if as_block:
        return _dict_to_block(value, block_name, indent)
    else:
        return _dict_to_attributes(value, indent)


def _is_dict_list(value: list) -> bool:
    """Check if all items in list are dictionaries."""
    return all(isinstance(item, dict) for item in value)


def _dict_list_to_blocks(value: list, block_name: str, indent: int) -> str:
    """Convert list of dictionaries to multiple blocks."""
    lines = []
    for item in value:
        if item:  # Skip empty dicts
            lines.append(_dict_to_block(item, block_name, indent))
    return "\n".join(lines)


def _dict_to_attributes(value: dict, indent: int) -> str:
    """Convert dictionary to attribute assignment format."""
    indent_str = "  " * indent
    prev_indent_str = "  " * (indent - 1)
    lines = []
    for k, v in value.items():
        hcl_key = to_snake(k).lower()
        hcl_value = _value_to_hcl(v, indent + 1)
        lines.append(f"{indent_str}{hcl_key} = {hcl_value}")
    return "{\n" + "\n".join(lines) + f"\n{prev_indent_str}" + "}"


def _dict_to_block(data: dict[str, Any], block_type: str, indent: int = 0) -> str:
    """
    Convert a dictionary to a terraform block format.

    Args:
        data: Dictionary to convert.
        block_type: The block type name.
        indent: Current indentation level.

    Returns:
        String representation as a terraform block.
    """
    indent_str = "  " * indent
    block_indent_str = "  " * (indent + 1)

    lines = [f"{indent_str}{block_type} {{"]

    for key, value in data.items():
        hcl_key = to_snake(key).lower()

        if isinstance(value, dict) and value:
            # Nested dictionary becomes a nested block
            nested_block = _dict_to_block(value, hcl_key, indent + 1)
            lines.append(nested_block)
        elif isinstance(value, list):
            if value:
                if _is_dict_list(value):
                    # List of dictionaries becomes multiple blocks of the same type
                    for item in value:
                        if item:  # Skip empty dicts
                            nested_block = _dict_to_block(item, hcl_key, indent + 1)
                            lines.append(nested_block)
                else:
                    # Regular list becomes an attribute
                    hcl_value = _value_to_hcl(value, indent + 1)
                    lines.append(f"{block_indent_str}{hcl_key} = {hcl_value}")
            else:
                continue  # Skip empty lists

        else:
            # Regular attribute assignment
            hcl_value = _value_to_hcl(value, indent + 1)
            lines.append(f"{block_indent_str}{hcl_key} = {hcl_value}")

    lines.append(f"{indent_str}}}")
    return "\n".join(lines)
