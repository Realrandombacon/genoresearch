"""
Tests for orchestrator/providers.py — OpenAI-compatible provider helpers.
"""

from unittest.mock import patch, MagicMock

import requests

from orchestrator.providers import (
    _build_recovery_prompt,
    _extract_thinking,
    _chat_openai_compatible,
    _recovery_openai_compatible,
)


class TestExtractThinking:

    def test_extract_thinking_basic(self):
        result = _extract_thinking("<think>reasoning</think>answer")
        assert "answer" in result
        assert "[Reasoning]" in result
        assert "reasoning" in result

    def test_extract_thinking_no_tags(self):
        result = _extract_thinking("just text")
        assert result == "just text"


class TestBuildRecoveryPrompt:

    def test_build_recovery_prompt(self):
        prompt = _build_recovery_prompt("Some analysis text here")
        assert "Some analysis text" in prompt
        assert "TOOL:" in prompt
        assert "NOW respond" in prompt

    def test_build_recovery_prompt_strips_reasoning(self):
        prompt = _build_recovery_prompt("[Reasoning] Deep thought about genes")
        # Should strip the [Reasoning] prefix
        assert "Deep thought" in prompt
        assert not prompt.startswith("[Reasoning]")


class TestChatOpenAICompatible:

    @patch("orchestrator.providers.requests.post")
    def test_chat_openai_compatible_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "TOOL: next_gene()"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _chat_openai_compatible(
            url="https://api.test.com/v1/chat/completions",
            api_key="test-key",
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            timeout=30,
        )
        assert "TOOL: next_gene()" in result

    @patch("orchestrator.providers.requests.post")
    def test_chat_openai_compatible_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        with pytest.raises(requests.exceptions.Timeout):
            _chat_openai_compatible(
                url="https://api.test.com/v1/chat/completions",
                api_key="test-key",
                model="test-model",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0.7,
                top_p=0.9,
                max_tokens=100,
                timeout=30,
            )

    @patch("orchestrator.providers.requests.post")
    def test_chat_openai_compatible_rate_limit(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Too Many Requests", response=mock_resp
        )
        mock_post.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            _chat_openai_compatible(
                url="https://api.test.com/v1/chat/completions",
                api_key="test-key",
                model="test-model",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0.7,
                top_p=0.9,
                max_tokens=100,
                timeout=30,
            )

    @patch("orchestrator.providers.requests.post")
    def test_chat_openai_compatible_empty(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _chat_openai_compatible(
            url="https://api.test.com/v1/chat/completions",
            api_key="test-key",
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            timeout=30,
        )
        assert result == ""


class TestRecoveryOpenAICompatible:

    @patch("orchestrator.providers.requests.post")
    def test_recovery_openai_compatible_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "TOOL: save_finding('title', 'desc', 'ev')"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _recovery_openai_compatible(
            url="https://api.test.com/v1/chat/completions",
            api_key="test-key",
            model="test-model",
            thought_text="I analyzed the gene and found a domain.",
            temperature=0.3,
            timeout=30,
        )
        assert "TOOL:" in result
        assert "save_finding" in result


import pytest
