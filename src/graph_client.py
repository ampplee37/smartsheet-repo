"""
Microsoft Graph API client with MSAL authentication.
Handles both app-only and delegated authentication for SharePoint and OneNote operations.
"""

import json
import time
import logging
import base64
from typing import Dict, Any, Optional, Tuple
import requests
import msal
import tenacity
try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


class GraphClient:
    """Microsoft Graph API client with MSAL authentication."""
    
    def __init__(self):
        """Initialize the Graph client with MSAL configuration."""
        self.authority = f"https://login.microsoftonline.com/{config.TENANT_ID}"
        self.scope = [config.get_graph_api_scope()]
        self.delegated_scope = [config.GRAPH_API_DELEGATED_SCOPE]
        # App-only (client credentials) flow
        self.app = msal.ConfidentialClientApplication(
            client_id=config.CLIENT_ID,
            client_credential=config.CLIENT_SECRET,
            authority=self.authority
        )
        # Delegated (user) flow: Public client, no secret
        self.public_app = msal.PublicClientApplication(
            client_id=config.BVC_ONENOTE_INGEST_BOT_ID,
            authority=self.authority
        )
        self._access_token = None
        self._token_expires_at = 0
        self._delegated_token = None
        self._delegated_token_expires_at = 0
    
    def is_token_valid(self, token: str) -> bool:
        """Check if the JWT access token is still valid (not expired)."""
        if not token:
            return False
        try:
            payload = token.split('.')[1]
            # Add padding if needed
            payload += '=' * (-len(payload) % 4)
            decoded = json.loads(
                base64.urlsafe_b64decode(payload.encode('utf-8')).decode('utf-8')
            )
            exp = decoded.get("exp")
            if not exp:
                return False
            # 2 min safety margin
            return int(exp) > int(time.time()) + 120
        except Exception as e:
            logger.warning(f"Could not decode token: {e}")
            return False
    
    def refresh_delegated_token(self) -> str:
        """Use the refresh token to get a new delegated access token (public client flow)."""
        logger.info("Refreshing delegated access token using refresh token (public client flow)...")
        bot_client_id = getattr(config, 'BVC_ONENOTE_INGEST_BOT_ID', None)
        refresh_token = getattr(config, 'BVC_BOT_REFRESH_TOKEN', None)
        if not all([bot_client_id, refresh_token]):
            raise Exception("Missing bot credentials for delegated authentication")
        # Use public client flow (no secret)
        result = self.public_app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=[
                "https://graph.microsoft.com/User.Read",
                "https://graph.microsoft.com/Notes.ReadWrite.All"
            ]
        )
        if "access_token" not in result:
            logger.error(f"Failed to refresh delegated token: {result}")
            raise Exception(f"Failed to refresh delegated token: {result}")
        access_token = result["access_token"]
        new_refresh_token = result.get("refresh_token")
        if access_token:
            self._delegated_token = access_token
            self._delegated_token_expires_at = time.time() + result.get("expires_in", 3600) - 300
            logger.info("Successfully refreshed delegated access token")
        if new_refresh_token:
            logger.info("New refresh token received (update your .env if you want to persist it)")
        return access_token
    
    def get_delegated_access_token(self) -> str:
        """
        Get a valid delegated access token, refreshing if necessary.
        
        Returns:
            str: Valid delegated access token
            
        Raises:
            Exception: If token acquisition fails
        """
        # Check if we have a valid delegated token
        if self._delegated_token and self.is_token_valid(self._delegated_token):
            return self._delegated_token
        
        # Try to get from config first
        config_token = getattr(config, 'BVC_BOT_ACCESS_TOKEN', None)
        if config_token and self.is_token_valid(config_token):
            self._delegated_token = config_token
            return config_token
        
        # Refresh the token
        return self.refresh_delegated_token()
    
    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            str: Valid access token
            
        Raises:
            Exception: If token acquisition fails
        """
        # Check if we have a valid token
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        # Acquire new token
        result = self.app.acquire_token_for_client(scopes=self.scope)
        
        if "access_token" not in result:
            error_msg = f"Failed to acquire token: {result.get('error_description', 'Unknown error')}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        self._access_token = result["access_token"]
        # Set expiration time with 5-minute buffer
        self._token_expires_at = time.time() + result.get("expires_in", 3600) - 300
        
        logger.info("Successfully acquired new access token")
        return self._access_token
    
    def graph_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Graph API endpoint (e.g., '/drives/{driveId}/items')
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            Exception: If request fails
        """
        url = f"https://graph.microsoft.com/v1.0{endpoint}"
        
        # Get access token
        access_token = self.get_access_token()
        
        # Prepare headers
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        # Make request
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=config.REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            # Handle empty or non-JSON responses
            if response.status_code in (202, 204) or not response.content:
                return {}
            
            try:
                return response.json()
            except Exception:
                logger.warning(f"Non-JSON response from Graph API for {url}: {response.text}")
                return {"raw_response": response.text}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise Exception(f"Graph API request failed: {e}")
    
    def graph_request_delegated(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        username: str = None,
        password: str = None
    ) -> Dict[str, Any]:
        """
        Make a delegated request to the Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Graph API endpoint (e.g., '/me/onenote/notebooks')
            data: Request body data
            params: Query parameters
            headers: Additional headers
            username: User email (optional)
            password: User password (optional)
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            Exception: If request fails
        """
        url = f"https://graph.microsoft.com/v1.0{endpoint}"
        
        # Get delegated access token
        access_token = self.get_delegated_access_token()
        
        # Prepare headers
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        # Make request
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=config.REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Delegated Graph API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise Exception(f"Delegated Graph API request failed: {e}")
    
    def copy_item(
        self, 
        drive_id: str, 
        item_id: str, 
        parent_reference: Dict[str, str], 
        name: str
    ) -> Dict[str, Any]:
        """
        Copy an item (folder/file) in SharePoint.
        
        Args:
            drive_id: SharePoint drive ID
            item_id: Item ID to copy
            parent_reference: Parent folder reference
            name: New name for the copied item
            
        Returns:
            Dict[str, Any]: Copy operation response
        """
        endpoint = f"/drives/{drive_id}/items/{item_id}/copy"
        data = {
            "parentReference": parent_reference,
            "name": name
        }
        
        logger.info(f"Copying item {item_id} to {name}")
        return self.graph_request("POST", endpoint, data=data)
    
    def get_copy_status(self, location_url: str) -> Dict[str, Any]:
        """
        Check the status of a copy operation.
        
        Args:
            location_url: Status URL from copy operation
            
        Returns:
            Dict[str, Any]: Status response
        """
        try:
            response = requests.get(
                location_url,
                timeout=config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 202:
                # Still in progress
                return {"status": "inProgress"}
            elif response.status_code == 200:
                # Completed
                return response.json()
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check copy status: {e}")
            raise Exception(f"Failed to check copy status: {e}")
    
    def wait_for_copy_completion(self, location_url: str, timeout: int = None) -> Dict[str, Any]:
        """
        Wait for a copy operation to complete.
        
        Args:
            location_url: Status URL from copy operation
            timeout: Maximum time to wait (seconds)
            
        Returns:
            Dict[str, Any]: Final status response
            
        Raises:
            Exception: If operation times out or fails
        """
        if timeout is None:
            timeout = config.COPY_OPERATION_TIMEOUT
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_copy_status(location_url)
            
            if status.get("status") != "inProgress":
                if "error" in status:
                    raise Exception(f"Copy operation failed: {status['error']}")
                return status
            
            # Wait before checking again
            time.sleep(5)
        
        raise Exception(f"Copy operation timed out after {timeout} seconds")
    
    def get_drive_items(self, drive_id: str, folder_id: str = None) -> Dict[str, Any]:
        """
        Get items in a SharePoint drive or folder.
        
        Args:
            drive_id: SharePoint drive ID
            folder_id: Optional folder ID to list items from
            
        Returns:
            Dict[str, Any]: Items response
        """
        if folder_id:
            endpoint = f"/drives/{drive_id}/items/{folder_id}/children"
        else:
            endpoint = f"/drives/{drive_id}/root/children"
        
        return self.graph_request("GET", endpoint)
    
    def get_site_notebooks(self, site_id: str, display_name: str = None) -> Dict[str, Any]:
        """
        Get OneNote notebooks for a SharePoint site using delegated authentication.
        
        Args:
            site_id: SharePoint site ID
            display_name: Optional filter by display name
            
        Returns:
            Dict[str, Any]: Notebooks response
        """
        endpoint = f"/sites/{site_id}/onenote/notebooks"
        params = {}
        
        if display_name:
            params["$filter"] = f"displayName eq '{display_name}'"
        
        return self.graph_request_delegated("GET", endpoint, params=params)
    
    def create_notebook(self, site_id: str, display_name: str) -> Dict[str, Any]:
        """
        Create a new OneNote notebook using delegated authentication.
        
        Args:
            site_id: SharePoint site ID
            display_name: Notebook display name
            
        Returns:
            Dict[str, Any]: Created notebook response
        """
        endpoint = f"/sites/{site_id}/onenote/notebooks"
        data = {
            "displayName": display_name
        }
        
        logger.info(f"Creating OneNote notebook with delegated auth: {display_name}")
        return self.graph_request_delegated("POST", endpoint, data=data)
    
    def create_notebook_section(
        self, 
        site_id: str, 
        notebook_id: str, 
        section_name: str
    ) -> Dict[str, Any]:
        """
        Create a new section in a OneNote notebook.
        
        Args:
            site_id: SharePoint site ID
            notebook_id: Notebook ID
            section_name: Section name
            
        Returns:
            Dict[str, Any]: Created section response
        """
        endpoint = f"/sites/{site_id}/onenote/notebooks/{notebook_id}/sections"
        data = {
            "displayName": section_name
        }
        
        logger.info(f"Creating OneNote section: {section_name}")
        return self.graph_request("POST", endpoint, data=data)
    
    def get_user_notebooks_delegated(self, display_name: str = None) -> Dict[str, Any]:
        """
        Get OneNote notebooks for the current user using delegated authentication.
        
        Args:
            display_name: Optional filter by display name
            
        Returns:
            Dict[str, Any]: Notebooks response
        """
        endpoint = "/me/onenote/notebooks"
        params = {}
        
        if display_name:
            params["$filter"] = f"displayName eq '{display_name}'"
        
        return self.graph_request_delegated("GET", endpoint, params=params)
    
    def create_notebook_delegated(self, display_name: str) -> Dict[str, Any]:
        """
        Create a new OneNote notebook using delegated authentication.
        
        Args:
            display_name: Notebook display name
            
        Returns:
            Dict[str, Any]: Created notebook response
        """
        endpoint = "/me/onenote/notebooks"
        data = {
            "displayName": display_name
        }
        
        logger.info(f"Creating OneNote notebook with delegated auth: {display_name}")
        return self.graph_request_delegated("POST", endpoint, data=data)
    
    def create_notebook_section_delegated(
        self, 
        notebook_id: str, 
        section_name: str
    ) -> Dict[str, Any]:
        """
        Create a new section in a OneNote notebook using delegated authentication.
        
        Args:
            notebook_id: Notebook ID
            section_name: Section name
            
        Returns:
            Dict[str, Any]: Created section response
        """
        endpoint = f"/me/onenote/notebooks/{notebook_id}/sections"
        data = {
            "displayName": section_name
        }
        
        logger.info(f"Creating OneNote section with delegated auth: {section_name}")
        return self.graph_request_delegated("POST", endpoint, data=data)
    
    def get_notebook_sections_delegated(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get sections in a OneNote notebook using delegated authentication.
        
        Args:
            notebook_id: Notebook ID
            
        Returns:
            Dict[str, Any]: Sections response
        """
        endpoint = f"/me/onenote/notebooks/{notebook_id}/sections"
        return self.graph_request_delegated("GET", endpoint)

    def get_site_notebook_sections(self, site_id: str, notebook_id: str) -> Dict[str, Any]:
        """
        Get sections in a OneNote notebook in a SharePoint site using delegated authentication.
        
        Args:
            site_id: SharePoint site ID
            notebook_id: Notebook ID
            
        Returns:
            Dict[str, Any]: Sections response
        """
        endpoint = f"/sites/{site_id}/onenote/notebooks/{notebook_id}/sections"
        return self.graph_request_delegated("GET", endpoint)

    @tenacity.retry(
        reraise=True,
        stop=tenacity.stop_after_attempt(config.MAX_RETRIES),
        wait=tenacity.wait_exponential(multiplier=config.RETRY_DELAY),
        retry=tenacity.retry_if_exception(lambda e: hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 403)
    )
    def create_site_notebook_section(
        self, 
        site_id: str, 
        notebook_id: str, 
        section_name: str
    ) -> Dict[str, Any]:
        """
        Create a new section in a OneNote notebook in a SharePoint site using delegated authentication.
        Retries on 403 errors with exponential backoff.
        """
        endpoint = f"/sites/{site_id}/onenote/notebooks/{notebook_id}/sections"
        data = {
            "displayName": section_name
        }
        logger.info(f"Creating OneNote section in site notebook with delegated auth: {section_name}")
        return self.graph_request_delegated("POST", endpoint, data=data)

    def get_notebook_by_name_and_parent(self, site_id: str, parent_folder_id: str, notebook_name: str):
        """
        Get a OneNote notebook by name in a specific parent folder (SharePoint site and folder).
        Args:
            site_id: SharePoint Site ID
            parent_folder_id: Parent folder ID
            notebook_name: Notebook display name
        Returns:
            Dict[str, Any] or None: Notebook metadata if found, else None
        """
        try:
            endpoint = f"/sites/{site_id}/onenote/notebooks"
            response = self.graph_request_delegated("GET", endpoint)
            notebooks = response.get('value', [])
            
            logger.info(f"Searching for notebook '{notebook_name}' in {len(notebooks)} notebooks")
            
            for nb in notebooks:
                nb_name = nb.get('displayName', '')
                nb_parent = nb.get('parentSectionGroupId', '')
                
                logger.debug(f"Checking notebook: '{nb_name}' with parent: '{nb_parent}'")
                
                if nb_name == notebook_name and nb_parent == parent_folder_id:
                    logger.info(f"Found matching notebook: '{notebook_name}' with ID: {nb.get('id')}")
                    return nb
            
            logger.info(f"No notebook found with name '{notebook_name}' in parent folder '{parent_folder_id}'")
            return None
        except Exception as e:
            logger.error(f"Failed to get notebook by name and parent: {e}")
            return None

    def create_notebook_in_folder(self, site_id: str, parent_folder_id: str, notebook_name: str):
        """
        Create a OneNote notebook in a specific parent folder (SharePoint site and folder).
        """
        try:
            endpoint = f"/sites/{site_id}/onenote/notebooks"
            data = {
                "displayName": notebook_name,
                "parentSectionGroupId": parent_folder_id
            }
            response = self.graph_request_delegated("POST", endpoint, data=data)
            return response
        except Exception as e:
            # If 409 conflict, fetch the existing notebook
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 409:
                logger.warning(f"Notebook already exists, fetching existing notebook: {notebook_name}")
                try:
                    notebooks = self.graph_request_delegated("GET", endpoint)
                    found = False
                    for nb in notebooks.get('value', []):
                        nb_name = nb.get('displayName', '')
                        nb_parent = nb.get('parentSectionGroupId', '')
                        logger.debug(f"Checking notebook: '{nb_name}' with parent: '{nb_parent}'")
                        if nb_name == notebook_name and nb_parent == parent_folder_id:
                            logger.info(f"Found existing notebook: {notebook_name} with ID: {nb.get('id')}")
                            found = True
                            return nb
                    if not found:
                        logger.error(f"Notebook exists but could not be found by name: {notebook_name} and parent: {parent_folder_id}")
                        # Fallback: return the first notebook with matching name
                        for nb in notebooks.get('value', []):
                            if nb.get('displayName', '') == notebook_name:
                                logger.info(f"Fallback: Found notebook by name only: {notebook_name} with ID: {nb.get('id')}")
                                return nb
                        raise Exception(f"Notebook exists but could not be found: {notebook_name}")
                except Exception as fetch_error:
                    logger.error(f"Failed to fetch existing notebook: {fetch_error}")
                    raise
            logger.error(f"Failed to create notebook in folder: {e}")
            raise

    def create_notebook_in_drive_folder(self, site_id: str, parent_folder_id: str, notebook_name: str):
        """
        Create a OneNote notebook in a specific document library folder using the drive/items endpoint.
        Args:
            site_id: SharePoint Site ID
            parent_folder_id: Folder ID in the document library
            notebook_name: Notebook display name
        Returns:
            Dict[str, Any]: Created notebook metadata
        """
        try:
            endpoint = f"/sites/{site_id}/drive/items/{parent_folder_id}/onenote/notebooks"
            data = {
                "displayName": notebook_name
            }
            response = self.graph_request_delegated("POST", endpoint, data=data)
            return response
        except Exception as e:
            # If 409 conflict, fetch the existing notebook in the folder
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 409:
                logger.warning(f"Notebook already exists in folder, fetching existing notebook: {notebook_name}")
                return self.find_notebook_in_drive_folder(site_id, parent_folder_id, notebook_name)
            logger.error(f"Failed to create notebook in drive folder: {e}")
            raise

    def find_notebook_in_drive_folder(self, site_id: str, parent_folder_id: str, notebook_name: str):
        """
        Find a OneNote notebook by name in a specific document library folder.
        Args:
            site_id: SharePoint Site ID
            parent_folder_id: Folder ID in the document library
            notebook_name: Notebook display name
        Returns:
            Dict[str, Any] or None: Notebook metadata if found, else None
        """
        try:
            endpoint = f"/sites/{site_id}/drive/items/{parent_folder_id}/children"
            response = self.graph_request_delegated("GET", endpoint)
            for item in response.get('value', []):
                if item.get('name', '').lower() == notebook_name.lower() and item.get('file', {}).get('mimeType', '').startswith('application/onenote'):
                    logger.info(f"Found notebook '{notebook_name}' in folder with ID: {item.get('id')}")
                    return item
            logger.info(f"No notebook named '{notebook_name}' found in folder {parent_folder_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to find notebook in drive folder: {e}")
            return None

    def create_page_in_section(self, site_id: str, section_id: str, html_content: str) -> dict:
        """
        Create a OneNote page in the specified section with the given HTML content.
        Args:
            site_id: SharePoint site ID
            section_id: OneNote section ID
            html_content: HTML content for the page
        Returns:
            dict: API response for the created page
        """
        import requests
        endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/onenote/sections/{section_id}/pages"
        headers = {
            "Authorization": f"Bearer {self.get_delegated_access_token()}"
            # Do NOT set Content-Type here; requests will set it for multipart
        }
        files = {
            'Presentation': ('page.html', html_content, 'text/html')
        }
        logger.info(f"Creating OneNote page in section {section_id} (site {site_id}) [multipart/form-data]")
        response = requests.post(endpoint, headers=headers, files=files)
        response.raise_for_status()
        return response.json()


# Global Graph client instance
graph_client = GraphClient() 