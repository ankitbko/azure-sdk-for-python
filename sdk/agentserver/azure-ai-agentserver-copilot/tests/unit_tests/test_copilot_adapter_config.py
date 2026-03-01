# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
"""Unit tests for the BYOK / Managed Identity config builder."""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBuildSessionConfig:
    """Tests for _build_session_config()."""

    def test_default_github_copilot_model(self):
        """Without AZURE_AI_FOUNDRY_RESOURCE_URL, uses default GitHub Copilot model."""
        env = {"COPILOT_MODEL": ""}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("AZURE_AI_FOUNDRY_RESOURCE_URL", None)
            os.environ.pop("COPILOT_MODEL", None)

            from azure.ai.agentserver.copilot.copilot_adapter import _build_session_config

            config = _build_session_config()
            assert config["model"] == "gpt-5"
            assert "provider" not in config

    def test_custom_github_model(self):
        """COPILOT_MODEL overrides default when not in BYOK mode."""
        with patch.dict(os.environ, {"COPILOT_MODEL": "gpt-4.1"}, clear=False):
            os.environ.pop("AZURE_AI_FOUNDRY_RESOURCE_URL", None)

            from azure.ai.agentserver.copilot.copilot_adapter import _build_session_config

            config = _build_session_config()
            assert config["model"] == "gpt-4.1"

    def test_byok_foundry_mode(self):
        """With AZURE_AI_FOUNDRY_RESOURCE_URL, builds BYOK ProviderConfig with placeholder token."""
        env = {
            "AZURE_AI_FOUNDRY_RESOURCE_URL": "https://myresource.openai.azure.com",
            "COPILOT_MODEL": "gpt-4.1",
        }
        with patch.dict(os.environ, env, clear=False):
            from azure.ai.agentserver.copilot.copilot_adapter import _build_session_config

            config = _build_session_config()

        assert config["model"] == "gpt-4.1"
        assert config["provider"]["type"] == "openai"
        assert config["provider"]["base_url"] == "https://myresource.openai.azure.com/openai/v1/"
        assert config["provider"]["bearer_token"] == "placeholder"
        assert config["provider"]["wire_api"] == "responses"

    @patch("azure.identity.DefaultAzureCredential")
    def test_byok_trailing_slash_stripped(self, mock_cred_cls):
        """Trailing slash on resource URL is handled correctly."""
        mock_cred = MagicMock()
        mock_cred.get_token.return_value = MagicMock(token="t")
        mock_cred_cls.return_value = mock_cred

        env = {
            "AZURE_AI_FOUNDRY_RESOURCE_URL": "https://myresource.openai.azure.com/",
        }
        with patch.dict(os.environ, env, clear=False):
            from azure.ai.agentserver.copilot.copilot_adapter import _build_session_config

            config = _build_session_config()

        assert config["provider"]["base_url"] == "https://myresource.openai.azure.com/openai/v1/"

    @patch("azure.identity.DefaultAzureCredential")
    def test_byok_default_model(self, mock_cred_cls):
        """BYOK mode defaults to gpt-4.1 when COPILOT_MODEL is not set."""
        mock_cred = MagicMock()
        mock_cred.get_token.return_value = MagicMock(token="t")
        mock_cred_cls.return_value = mock_cred

        env = {
            "AZURE_AI_FOUNDRY_RESOURCE_URL": "https://myresource.openai.azure.com",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("COPILOT_MODEL", None)

            from azure.ai.agentserver.copilot.copilot_adapter import _build_session_config

            config = _build_session_config()

        assert config["model"] == "gpt-4.1"


@pytest.mark.unit
class TestTokenRefresh:
    """Tests for _refresh_token_if_needed()."""

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_refresh_updates_bearer_token(self, mock_build):
        """Token refresh replaces the bearer_token in the provider config."""
        mock_build.return_value = {
            "model": "gpt-4.1",
            "provider": {
                "type": "openai",
                "base_url": "https://x.openai.azure.com/openai/v1/",
                "bearer_token": "old-token",
                "wire_api": "responses",
            },
        }

        with patch.dict(os.environ, {"AZURE_AI_FOUNDRY_RESOURCE_URL": "https://x.openai.azure.com"}, clear=False):
            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter.__new__(CopilotAdapter)
            adapter._session_config = mock_build.return_value

            mock_cred = MagicMock()
            mock_cred.get_token.return_value = MagicMock(token="new-token-456")
            adapter._credential = mock_cred

            config = adapter._refresh_token_if_needed()

        assert config["provider"]["bearer_token"] == "new-token-456"

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_no_refresh_without_credential(self, mock_build):
        """Without a credential (non-BYOK mode), config is returned as-is."""
        mock_build.return_value = {"model": "gpt-5"}

        from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

        adapter = CopilotAdapter.__new__(CopilotAdapter)
        adapter._session_config = mock_build.return_value
        adapter._credential = None

        config = adapter._refresh_token_if_needed()
        assert config == {"model": "gpt-5"}


@pytest.mark.unit
class TestSystemMessage:
    """Tests for system message resolution in CopilotAdapter."""

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_string_system_message(self, mock_build):
        """A plain string is treated as append mode."""
        mock_build.return_value = {"model": "gpt-5"}

        from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

        adapter = CopilotAdapter(system_message="You are a helpful coding assistant.")

        sm = adapter._session_config.get("system_message")
        assert sm is not None
        assert sm["mode"] == "append"
        assert sm["content"] == "You are a helpful coding assistant."

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_dict_system_message_replace(self, mock_build):
        """A SystemMessageConfig dict with replace mode is used as-is."""
        mock_build.return_value = {"model": "gpt-5"}

        from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

        sm_config = {"mode": "replace", "content": "Custom system prompt."}
        adapter = CopilotAdapter(system_message=sm_config)

        sm = adapter._session_config.get("system_message")
        assert sm is not None
        assert sm["mode"] == "replace"
        assert sm["content"] == "Custom system prompt."

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_env_var_system_message(self, mock_build):
        """COPILOT_SYSTEM_MESSAGE env var is used when no explicit param is given."""
        mock_build.return_value = {"model": "gpt-5"}

        with patch.dict(os.environ, {"COPILOT_SYSTEM_MESSAGE": "Env system prompt."}, clear=False):
            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter()

        sm = adapter._session_config.get("system_message")
        assert sm is not None
        assert sm["mode"] == "append"
        assert sm["content"] == "Env system prompt."

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_explicit_param_overrides_env_var(self, mock_build):
        """Explicit system_message parameter takes priority over env var."""
        mock_build.return_value = {"model": "gpt-5"}

        with patch.dict(os.environ, {"COPILOT_SYSTEM_MESSAGE": "From env."}, clear=False):
            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter(system_message="From param.")

        sm = adapter._session_config.get("system_message")
        assert sm["content"] == "From param."

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_no_system_message(self, mock_build):
        """Without any system message, the config has no system_message key."""
        mock_build.return_value = {"model": "gpt-5"}

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COPILOT_SYSTEM_MESSAGE", None)

            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter()

        assert "system_message" not in adapter._session_config

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_session_config_system_message_preserved(self, mock_build):
        """system_message inside session_config is preserved when no explicit param."""
        mock_build.return_value = {"model": "gpt-5"}
        sc = {"system_message": {"mode": "replace", "content": "From session config."}}

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COPILOT_SYSTEM_MESSAGE", None)

            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter(session_config=sc)

        sm = adapter._session_config.get("system_message")
        assert sm is not None
        assert sm["mode"] == "replace"
        assert sm["content"] == "From session config."

    @patch("azure.ai.agentserver.copilot.copilot_adapter._build_session_config")
    def test_explicit_param_overrides_session_config(self, mock_build):
        """Explicit system_message parameter takes priority over session_config."""
        mock_build.return_value = {"model": "gpt-5"}
        sc = {"system_message": {"mode": "replace", "content": "From session config."}}

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COPILOT_SYSTEM_MESSAGE", None)

            from azure.ai.agentserver.copilot.copilot_adapter import CopilotAdapter

            adapter = CopilotAdapter(session_config=sc, system_message="Override.")

        sm = adapter._session_config.get("system_message")
        assert sm["mode"] == "append"
        assert sm["content"] == "Override."
