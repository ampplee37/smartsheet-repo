"""
Tests for configuration management module.
"""

import os
import pytest
from unittest.mock import patch
from src.config import Config, config


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_initialization(self):
        """Test that config is properly initialized."""
        assert isinstance(config, Config)
        assert hasattr(config, 'CLIENT_ID')
        assert hasattr(config, 'CLIENT_SECRET')
        assert hasattr(config, 'TENANT_ID')
        assert hasattr(config, 'SMTSHEET_TOKEN')
        assert hasattr(config, 'STORAGE_CONNECTION_STRING')
        assert hasattr(config, 'SHAREPOINT_SITE_ID')
    
    @patch.dict(os.environ, {
        'CLIENT_ID': 'test_client_id',
        'CLIENT_SECRET': 'test_client_secret',
        'TENANT_ID': 'test_tenant_id',
        'SMTSHEET_TOKEN': 'test_token',
        'STORAGE_CONNECTION_STRING': 'test_connection_string',
        'SHAREPOINT_SITE_ID': 'test_site_id'
    })
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        test_config = Config()
        assert test_config.validate() is True
    
    @patch.dict(os.environ, {
        'CLIENT_ID': '',
        'CLIENT_SECRET': 'test_client_secret',
        'TENANT_ID': 'test_tenant_id',
        'SMTSHEET_TOKEN': 'test_token',
        'STORAGE_CONNECTION_STRING': 'test_connection_string',
        'SHAREPOINT_SITE_ID': 'test_site_id'
    })
    def test_config_validation_failure(self):
        """Test configuration validation failure."""
        test_config = Config()
        assert test_config.validate() is False
    
    def test_get_graph_api_scope(self):
        """Test Graph API scope retrieval."""
        expected_scope = "https://graph.microsoft.com/.default"
        assert config.get_graph_api_scope() == expected_scope
    
    def test_get_smartsheet_api_base(self):
        """Test Smartsheet API base URL retrieval."""
        expected_base = "https://api.smartsheet.com/2.0"
        assert config.get_smartsheet_api_base() == expected_base
    
    def test_config_constants(self):
        """Test that configuration constants are properly set."""
        assert config.GRAPH_API_SCOPE == "https://graph.microsoft.com/.default"
        assert config.SMARTSHEET_API_BASE == "https://api.smartsheet.com/2.0"
        assert config.TEMPLATE_MAPPING_TABLE == "TemplateMapping"
        assert config.MAX_RETRIES == 3
        assert config.RETRY_DELAY == 5
        assert config.REQUEST_TIMEOUT == 30
        assert config.COPY_OPERATION_TIMEOUT == 300


class TestConfigEnvironmentVariables:
    """Test cases for environment variable handling."""
    
    @patch.dict(os.environ, {
        'CLIENT_ID': 'env_client_id',
        'CLIENT_SECRET': 'env_client_secret',
        'TENANT_ID': 'env_tenant_id',
        'SMTSHEET_TOKEN': 'env_token',
        'STORAGE_CONNECTION_STRING': 'env_connection_string',
        'SHAREPOINT_SITE_ID': 'env_site_id'
    })
    def test_environment_variable_loading(self):
        """Test that environment variables are properly loaded."""
        test_config = Config()
        assert test_config.CLIENT_ID == 'env_client_id'
        assert test_config.CLIENT_SECRET == 'env_client_secret'
        assert test_config.TENANT_ID == 'env_tenant_id'
        assert test_config.SMTSHEET_TOKEN == 'env_token'
        assert test_config.STORAGE_CONNECTION_STRING == 'env_connection_string'
        assert test_config.SHAREPOINT_SITE_ID == 'env_site_id'
    
    def test_missing_environment_variables(self):
        """Test handling of missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            test_config = Config()
            assert test_config.CLIENT_ID == ''
            assert test_config.CLIENT_SECRET == ''
            assert test_config.TENANT_ID == ''
            assert test_config.SMTSHEET_TOKEN == ''
            assert test_config.STORAGE_CONNECTION_STRING == ''
            assert test_config.SHAREPOINT_SITE_ID == ''
    
    def test_optional_environment_variables(self):
        """Test optional environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            test_config = Config()
            assert test_config.FUNCTION_KEY is None 