"""
Tests for orchestrator/parsing.py — tool call parsing from LLM responses.
"""

from orchestrator.parsing import parse_tool, _split_args, _cast


class TestParseTool:

    def test_parse_basic_tool_call(self):
        result = parse_tool("TOOL: ncbi_search('query')")
        assert result is not None
        name, args, kwargs = result
        assert name == "ncbi_search"
        assert args == ["query"]
        assert kwargs == {}

    def test_parse_kwargs(self):
        result = parse_tool("TOOL: ncbi_search('query', db='gene')")
        assert result is not None
        name, args, kwargs = result
        assert name == "ncbi_search"
        assert args == ["query"]
        assert kwargs == {"db": "gene"}

    def test_parse_no_tool(self):
        result = parse_tool("Just thinking here")
        assert result is None

    def test_parse_qwen_variant(self):
        result = parse_tool("**Tool Call:** func()")
        assert result is not None
        name, args, kwargs = result
        assert name == "func"
        assert args == []
        assert kwargs == {}

    def test_parse_nested_parens(self):
        # Should not crash; exact result depends on implementation
        result = parse_tool("TOOL: func(other('inner'))")
        assert result is not None
        name, _, _ = result
        assert name == "func"

    def test_parse_quoted_string_with_comma(self):
        result = parse_tool("TOOL: func('hello, world')")
        assert result is not None
        name, args, kwargs = result
        assert name == "func"
        assert args == ["hello, world"]
        assert kwargs == {}


class TestSplitArgs:

    def test_split_args_basic(self):
        parts = _split_args("'a', 'b', 'c'")
        assert len(parts) == 3
        assert parts[0].strip() == "'a'"
        assert parts[1].strip() == "'b'"
        assert parts[2].strip() == "'c'"


class TestCast:

    def test_cast_types(self):
        assert _cast("42") == 42
        assert _cast("3.14") == 3.14
        assert _cast("'hello'") == "hello"
        assert _cast('"world"') == "world"
        assert _cast("plain") == "plain"
