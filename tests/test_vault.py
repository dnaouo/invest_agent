"""Tests for the vault credential proxy layer."""

from unittest.mock import patch

import pytest

from vault.proxy import get_credential


class TestGetCredential:
    @patch("vault.secrets.config", return_value="sk-test-moonshot-key")
    def test_get_credential_moonshot(self, _mock_config):
        assert get_credential("moonshot") == "sk-test-moonshot-key"

    @patch("vault.secrets.config", return_value="ts-test-tushare-token")
    def test_get_credential_tushare(self, _mock_config):
        assert get_credential("tushare") == "ts-test-tushare-token"

    def test_get_credential_unknown_service(self):
        with pytest.raises(ValueError, match="Unknown service"):
            get_credential("nonexistent")

    @patch("vault.secrets.config", return_value="")
    def test_get_credential_empty_value(self, _mock_config):
        with pytest.raises(RuntimeError, match="not set or empty"):
            get_credential("moonshot")
