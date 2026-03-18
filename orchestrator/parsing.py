"""
Tool call parsing — extract TOOL: name(args) from LLM responses.
"""

import re

# Pattern: TOOL: function_name(...)
# Also catches Qwen markdown variants like **Tool Call:** func(), **TOOL:** func(), etc.
TOOL_START_PATTERN = re.compile(
    r"(?:\*{0,2}Tool(?:\s*Call)?:?\*{0,2}|TOOL:)\s*(\w+)\(", re.IGNORECASE
)


def parse_tool(text: str):
    """Extract TOOL: name(args) from LLM response. Returns (name, args, kwargs) or None."""
    match = TOOL_START_PATTERN.search(text)
    if not match:
        return None

    name = match.group(1)

    # Find the matching closing paren, respecting quotes and nested parens
    start = match.end()  # position right after the opening '('
    raw_args = _extract_balanced_args(text, start)
    if raw_args is None:
        raw_args = ""

    raw_args = raw_args.strip()

    if not raw_args:
        return name, [], {}

    args = []
    kwargs = {}
    for part in _split_args(raw_args):
        part = part.strip()
        if "=" in part and not part.startswith(("'", '"')):
            key, val = part.split("=", 1)
            kwargs[key.strip()] = _cast(val.strip())
        else:
            args.append(_cast(part))

    return name, args, kwargs


def _extract_balanced_args(text: str, start: int) -> str:
    """Extract content between balanced parentheses, respecting quoted strings.

    `start` should point to the first char after the opening '('.
    Returns the content between parens, or None if no balanced close found.
    """
    depth = 1
    in_quote = None
    i = start
    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == in_quote and (i == 0 or text[i-1] != "\\"):
                in_quote = None
        else:
            if ch in ("'", '"'):
                in_quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i]
        i += 1
    # No balanced close found — return everything we have
    return text[start:]


def _split_args(raw: str) -> list[str]:
    """Split comma-separated args, respecting quotes."""
    parts = []
    current = ""
    depth = 0
    in_quote = None
    for ch in raw:
        if ch in ("'", '"') and in_quote is None:
            in_quote = ch
        elif ch == in_quote:
            in_quote = None
        elif ch == "(" and in_quote is None:
            depth += 1
        elif ch == ")" and in_quote is None:
            depth -= 1
        elif ch == "," and depth == 0 and in_quote is None:
            parts.append(current)
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current)
    return parts


def _cast(val: str):
    """Try to cast a string argument to int, float, or stripped string."""
    val = val.strip().strip("'\"")
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val
