"""
SharePoint folder management operations.
Handles parsing folder links and copying template folders.
"""

import re
import logging
import time
from typing import Tuple, Dict, Any, List
from urllib.parse import urlparse, parse_qs, unquote
from .graph_client import graph_client
from .storage import storage_client, Template

logger = logging.getLogger(__name__)


class FolderManager:
    """Manages SharePoint folder operations."""
    
    def __init__(self):
        """Initialize the folder manager."""
        pass
    
    def parse_folder_link(self, url: str) -> Tuple[str, str]:
        """
        Parse a SharePoint folder link to extract driveId and folderId.
        
        Args:
            url: SharePoint folder URL
            
        Returns:
            Tuple[str, str]: (driveId, folderId)
            
        Raises:
            ValueError: If URL cannot be parsed
        """
        try:
            # Handle different SharePoint URL formats
            if "sharepoint.com" in url:
                return self._parse_sharepoint_url(url)
            elif "graph.microsoft.com" in url:
                return self._parse_graph_url(url)
            else:
                raise ValueError(f"Unsupported URL format: {url}")
                
        except Exception as e:
            logger.error(f"Failed to parse folder link '{url}': {e}")
            raise ValueError(f"Failed to parse folder link: {e}")
    
    def _parse_sharepoint_url(self, url: str) -> Tuple[str, str]:
        """
        Parse a SharePoint URL to extract drive and folder IDs using robust Graph API lookups.
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            hostname = parsed.hostname  # e.g., 'bvcollective.sharepoint.com'
            # Find the site name
            site_index = -1
            for i, part in enumerate(path_parts):
                if part == 'sites':
                    site_index = i
                    break
            if site_index == -1:
                raise ValueError("Could not find 'sites' in SharePoint URL")
            site_name = path_parts[site_index + 1]
            logger.info(f"Extracted site_name: {site_name}")
            logger.info(f"Extracted hostname: {hostname}")
            # Get site ID from Graph API
            site_identifier = f"{hostname}:/sites/{site_name}"
            logger.info(f"Looking up site ID with identifier: {site_identifier}")
            site_response = graph_client.graph_request("GET", f"/sites/{site_identifier}")
            site_id = site_response.get('id')
            if not site_id:
                raise ValueError(f"Could not get site ID for {site_identifier}")
            logger.info(f"Resolved site_id: {site_id}")
            # Get default drive for the site
            drive_response = graph_client.graph_request("GET", f"/sites/{site_id}/drive")
            drive_id = drive_response.get('id')
            if not drive_id:
                raise ValueError(f"Could not get default drive for site {site_id}")
            logger.info(f"Resolved drive_id: {drive_id}")
            # Extract the server-relative folder path from the URL
            query_params = parse_qs(parsed.query)
            folder_path = query_params.get('id', [None])[0]
            if not folder_path:
                # If no ?id= param, extract the path after /sites/{siteName}/
                # e.g., /sites/Opportunities/Shared Documents/General/LED Studio/Convention Center - Tree
                after_site = parsed.path.split(f"/sites/{site_name}/", 1)
                if len(after_site) == 2:
                    folder_path = after_site[1]
                else:
                    raise ValueError("Could not extract folder path from URL")
                # Decode percent-encoded characters
                folder_path = unquote(folder_path)
            logger.info(f"Initial extracted folder_path: {folder_path}")
            folder_path = folder_path.lstrip('/')
            logger.info(f"Relative folder_path for drive: {folder_path}")
            # Use Graph API to get the folder item by path
            api_url = f"/sites/{site_id}/drive/root:/{folder_path}"
            logger.info(f"Graph API folder lookup URL: {api_url}")
            folder_response = graph_client.graph_request("GET", api_url)
            folder_id = folder_response.get('id')
            if not folder_id:
                raise ValueError(f"Could not find folder: {folder_path}")
            logger.info(f"Successfully resolved SharePoint folder - Drive: {drive_id}, Folder: {folder_id}")
            return (drive_id, folder_id)
        except Exception as e:
            logger.error(f"Failed to robustly parse SharePoint URL: {e}")
            raise ValueError(f"Failed to parse SharePoint URL: {e}")
    
    def _parse_graph_url(self, url: str) -> Tuple[str, str]:
        """
        Parse a Graph API URL to extract drive and folder IDs.
        
        Args:
            url: Graph API URL
            
        Returns:
            Tuple[str, str]: (driveId, folderId)
        """
        # Example Graph URL:
        # https://graph.microsoft.com/v1.0/drives/{driveId}/items/{itemId}
        
        pattern = r'/drives/([^/]+)/items/([^/?]+)'
        match = re.search(pattern, url)
        
        if not match:
            raise ValueError("Could not extract drive and item IDs from Graph URL")
        
        drive_id = match.group(1)
        folder_id = match.group(2)
        
        logger.info(f"Parsed Graph URL - Drive: {drive_id}, Folder: {folder_id}")
        return (drive_id, folder_id)
    
    def copy_template(
        self, 
        drive_id: str,  # source drive
        template_id: str, 
        parent_id: str,  # destination folder
        name: str,
        dest_drive_id: str  # destination drive
    ) -> Dict[str, Any]:
        """
        Copy the children of a template folder to a new location (destination folder).
        Args:
            drive_id: Source SharePoint drive ID
            template_id: Template folder ID
            parent_id: Destination parent folder ID
            name: New folder name (not used for children)
            dest_drive_id: Destination SharePoint drive ID
        Returns:
            Dict[str, Any]: Copy operation result
        """
        try:
            # List children of the template folder
            children = graph_client.get_drive_items(drive_id, template_id).get('value', [])
            if not children:
                logger.warning(f"No children found in template folder {template_id}")
                return {'success': False, 'error': 'No children in template folder'}
            results = []
            for child in children:
                child_id = child['id']
                child_name = child['name']
                parent_reference = {
                    "driveId": dest_drive_id,
                    "id": parent_id
                }
                logger.info(f"Copying child item {child_id} ({child_name}) to destination folder {parent_id}")
                try:
                    copy_response = graph_client.copy_item(
                        drive_id=drive_id,  # source drive
                        item_id=child_id,
                        parent_reference=parent_reference,
                        name=child_name
                    )
                    # Wait for completion if needed
                    if 'Location' in copy_response:
                        location_url = copy_response['Location']
                        logger.info(f"Copy operation for {child_name} initiated, monitoring at: {location_url}")
                        result = graph_client.wait_for_copy_completion(location_url)
                        logger.info(f"Copy operation for {child_name} completed: {result}")
                        results.append({'child': child_name, 'result': result, 'success': True})
                    else:
                        logger.info(f"Copy operation for {child_name} completed immediately: {copy_response}")
                        results.append({'child': child_name, 'result': copy_response, 'success': True})
                except Exception as e:
                    logger.error(f"Failed to copy child {child_name}: {e}")
                    results.append({'child': child_name, 'error': str(e), 'success': False})
            # Summarize
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            return {
                'total_children': len(children),
                'successful_copies': len(successful),
                'failed_copies': len(failed),
                'details': results
            }
        except Exception as e:
            logger.error(f"Failed to copy children from template {template_id}: {e}")
            raise
    
    def copy_templates_for_category(
        self, 
        parent_drive_id: str, 
        parent_folder_id: str, 
        project_category: str, 
        project_name: str
    ) -> List[Dict[str, Any]]:
        """
        Copy all templates for a project category, supporting cross-site/drive copying.
        Args:
            parent_drive_id: Destination SharePoint drive ID (project)
            parent_folder_id: Destination parent folder ID (project)
            project_category: Project category
            project_name: Project name
        Returns:
            List[Dict[str, Any]]: List of copy operation results
        """
        try:
            # Get templates for the category
            templates = storage_client.get_templates(project_category)
            if not templates:
                logger.warning(f"No templates found for category '{project_category}'")
                return []
            results = []
            for template in templates:
                try:
                    # Each template has its own drive_id (source) from the TemplateMapping table
                    source_drive_id = template.drive_id or parent_drive_id
                    template_id = template.template_folder_id
                    folder_name = f"{template.row_key} - {project_name}"
                    logger.info(f"Copying template '{template.row_key}' from drive {source_drive_id} to drive {parent_drive_id}")
                    # Copy the template from source_drive_id/template_id to parent_drive_id/parent_folder_id
                    result = self.copy_template(
                        drive_id=source_drive_id,  # source
                        template_id=template_id,
                        parent_id=parent_folder_id,  # destination folder
                        name=folder_name,
                        dest_drive_id=parent_drive_id  # destination drive
                    )
                    results.append({
                        'template': template,
                        'folder_name': folder_name,
                        'result': result,
                        'success': True
                    })
                    logger.info(f"Successfully copied template '{template.row_key}' to '{folder_name}'")
                except Exception as e:
                    logger.error(f"Failed to copy template '{template.row_key}': {e}")
                    results.append({
                        'template': template,
                        'folder_name': folder_name,
                        'error': str(e),
                        'success': False
                    })
            return results
        except Exception as e:
            logger.error(f"Failed to copy templates for category '{project_category}': {e}")
            raise
    
    def get_folder_info(self, drive_id: str, folder_id: str) -> Dict[str, Any]:
        """
        Get information about a SharePoint folder.
        
        Args:
            drive_id: SharePoint drive ID
            folder_id: Folder ID
            
        Returns:
            Dict[str, Any]: Folder information
        """
        try:
            endpoint = f"/drives/{drive_id}/items/{folder_id}"
            return graph_client.graph_request("GET", endpoint)
        except Exception as e:
            logger.error(f"Failed to get folder info for {folder_id}: {e}")
            raise
    
    def list_folder_contents(self, drive_id: str, folder_id: str) -> Dict[str, Any]:
        """
        List contents of a SharePoint folder.
        
        Args:
            drive_id: SharePoint drive ID
            folder_id: Folder ID
            
        Returns:
            Dict[str, Any]: Folder contents
        """
        try:
            return graph_client.get_drive_items(drive_id, folder_id)
        except Exception as e:
            logger.error(f"Failed to list folder contents for {folder_id}: {e}")
            raise
    
    def create_folder(self, drive_id: str, parent_id: str, folder_name: str) -> Dict[str, Any]:
        """
        Create a new folder in SharePoint.
        
        Args:
            drive_id: SharePoint drive ID
            parent_id: Parent folder ID
            folder_name: New folder name
            
        Returns:
            Dict[str, Any]: Created folder information
        """
        try:
            endpoint = f"/drives/{drive_id}/items/{parent_id}/children"
            data = {
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename"
            }
            
            logger.info(f"Creating folder '{folder_name}' in parent {parent_id}")
            return graph_client.graph_request("POST", endpoint, data=data)
            
        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise


# Global folder manager instance
folder_manager = FolderManager() 