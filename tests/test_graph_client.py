"""
Tests for Microsoft Graph API client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.graph_client import GraphClient, graph_client


class TestGraphClient:
    """Test cases for GraphClient class."""
    
    def test_graph_client_initialization(self):
        """Test that GraphClient is properly initialized."""
        with patch('src.config.config') as mock_config:
            mock_config.CLIENT_ID = 'test_client_id'
            mock_config.CLIENT_SECRET = 'test_client_secret'
            mock_config.TENANT_ID = 'test_tenant_id'
            mock_config.get_graph_api_scope.return_value = 'test_scope'
            
            client = GraphClient()
            assert client.authority == f"https://login.microsoftonline.com/{mock_config.TENANT_ID}"
            assert client.scope == [mock_config.get_graph_api_scope()]
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    def test_get_access_token_success(self, mock_msal_app, mock_config):
        """Test successful access token retrieval."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        
        client = GraphClient()
        token = client.get_access_token()
        
        assert token == 'test_token'
        mock_app_instance.acquire_token_for_client.assert_called_once_with(scopes=['test_scope'])
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    def test_get_access_token_failure(self, mock_msal_app, mock_config):
        """Test access token retrieval failure."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'error': 'invalid_client',
            'error_description': 'Client authentication failed'
        }
        
        client = GraphClient()
        
        with pytest.raises(Exception, match="Failed to acquire token"):
            client.get_access_token()
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    @patch('requests.request')
    def test_graph_request_success(self, mock_request, mock_msal_app, mock_config):
        """Test successful Graph API request."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        mock_config.REQUEST_TIMEOUT = 30
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'test_id', 'name': 'test_name'}
        mock_request.return_value = mock_response
        
        client = GraphClient()
        result = client.graph_request('GET', '/test/endpoint')
        
        assert result == {'id': 'test_id', 'name': 'test_name'}
        mock_request.assert_called_once()
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    @patch('requests.request')
    def test_graph_request_failure(self, mock_request, mock_msal_app, mock_config):
        """Test Graph API request failure."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        mock_config.REQUEST_TIMEOUT = 30
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        
        mock_request.side_effect = Exception("Network error")
        
        client = GraphClient()
        
        with pytest.raises(Exception, match="Graph API request failed"):
            client.graph_request('GET', '/test/endpoint')
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    def test_copy_item(self, mock_msal_app, mock_config):
        """Test copy item operation."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        
        client = GraphClient()
        
        with patch.object(client, 'graph_request') as mock_graph_request:
            mock_graph_request.return_value = {'id': 'copied_item_id'}
            
            result = client.copy_item(
                drive_id='test_drive_id',
                item_id='test_item_id',
                parent_reference={'driveId': 'test_drive_id', 'id': 'test_parent_id'},
                name='test_name'
            )
            
            assert result == {'id': 'copied_item_id'}
            mock_graph_request.assert_called_once_with(
                'POST',
                '/drives/test_drive_id/items/test_item_id/copy',
                data={
                    'parentReference': {'driveId': 'test_drive_id', 'id': 'test_parent_id'},
                    'name': 'test_name'
                }
            )
    
    @patch('requests.get')
    def test_get_copy_status_in_progress(self, mock_get):
        """Test copy status check when operation is in progress."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_get.return_value = mock_response
        
        client = GraphClient()
        result = client.get_copy_status('http://test-location-url')
        
        assert result == {'status': 'inProgress'}
    
    @patch('requests.get')
    def test_get_copy_status_completed(self, mock_get):
        """Test copy status check when operation is completed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'completed_item_id'}
        mock_get.return_value = mock_response
        
        client = GraphClient()
        result = client.get_copy_status('http://test-location-url')
        
        assert result == {'id': 'completed_item_id'}
    
    @patch('src.config.config')
    @patch('msal.ConfidentialClientApplication')
    def test_get_drive_items(self, mock_msal_app, mock_config):
        """Test get drive items operation."""
        # Setup mocks
        mock_config.CLIENT_ID = 'test_client_id'
        mock_config.CLIENT_SECRET = 'test_client_secret'
        mock_config.TENANT_ID = 'test_tenant_id'
        mock_config.get_graph_api_scope.return_value = 'test_scope'
        
        mock_app_instance = Mock()
        mock_msal_app.return_value = mock_app_instance
        
        mock_app_instance.acquire_token_for_client.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        
        client = GraphClient()
        
        with patch.object(client, 'graph_request') as mock_graph_request:
            mock_graph_request.return_value = {'value': [{'id': 'item1'}, {'id': 'item2'}]}
            
            # Test with folder_id
            result = client.get_drive_items('test_drive_id', 'test_folder_id')
            assert result == {'value': [{'id': 'item1'}, {'id': 'item2'}]}
            mock_graph_request.assert_called_with('GET', '/drives/test_drive_id/items/test_folder_id/children')
            
            # Test without folder_id
            result = client.get_drive_items('test_drive_id')
            assert result == {'value': [{'id': 'item1'}, {'id': 'item2'}]}
            mock_graph_request.assert_called_with('GET', '/drives/test_drive_id/root/children')


class TestGraphClientIntegration:
    """Integration test cases for GraphClient."""
    
    @patch('src.config.config')
    def test_graph_client_singleton(self, mock_config):
        """Test that graph_client is a singleton instance."""
        assert isinstance(graph_client, GraphClient)
        assert graph_client is GraphClient()
    
    def test_graph_client_methods_exist(self):
        """Test that all required methods exist on graph_client."""
        required_methods = [
            'get_access_token',
            'graph_request',
            'copy_item',
            'get_copy_status',
            'wait_for_copy_completion',
            'get_drive_items',
            'get_site_notebooks',
            'create_notebook',
            'create_notebook_section'
        ]
        
        for method_name in required_methods:
            assert hasattr(graph_client, method_name)
            assert callable(getattr(graph_client, method_name)) 