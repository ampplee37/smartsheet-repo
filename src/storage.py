"""
Azure Data Tables client for managing template mappings.
Provides functions to retrieve template folder IDs based on project categories.
"""

import logging
from typing import List, Optional, Dict, Any
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


class Template:
    """Template mapping data class."""
    
    def __init__(self, partition_key: str, row_key: str, template_folder_id: str, site_id: str = None, drive_id: str = None):
        """
        Initialize a Template instance.
        
        Args:
            partition_key: Project category (e.g., "Complex Design Build")
            row_key: Template name (e.g., "Standard Folder Structure")
            template_folder_id: SharePoint folder ItemId
            site_id: Site ID
            drive_id: Drive ID
        """
        self.partition_key = partition_key
        self.row_key = row_key
        self.template_folder_id = template_folder_id
        self.site_id = site_id
        self.drive_id = drive_id
    
    def __repr__(self):
        return f"Template({self.partition_key}, {self.row_key}, {self.template_folder_id}, {self.site_id}, {self.drive_id})"


class Project:
    """Project metadata data class for BVCSSProjects."""
    def __init__(self, partition_key: str, row_key: str, company_name: str, drive_id: str, job_folder_id: str, parent_folder_id: str, project_name: str, project_type: str, site_id: str):
        self.partition_key = partition_key
        self.row_key = row_key
        self.company_name = company_name
        self.drive_id = drive_id
        self.job_folder_id = job_folder_id
        self.parent_folder_id = parent_folder_id
        self.project_name = project_name
        self.project_type = project_type
        self.site_id = site_id
    def __repr__(self):
        return f"Project({self.partition_key}, {self.row_key}, {self.company_name}, {self.drive_id}, {self.job_folder_id}, {self.parent_folder_id}, {self.project_name}, {self.project_type}, {self.site_id})"


class StorageClient:
    """Azure Data Tables client for template management."""
    
    def __init__(self):
        """Initialize the storage client."""
        self.connection_string = config.STORAGE_CONNECTION_STRING
        self.table_name = config.TEMPLATE_MAPPING_TABLE
        self.table_service = None
        self.table_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the table service and client."""
        try:
            if not self.connection_string:
                logger.warning("No storage connection string provided, skipping table client initialization")
                self.table_service = None
                self.table_client = None
                return
                
            self.table_service = TableServiceClient.from_connection_string(
                self.connection_string
            )
            self.table_client = self.table_service.get_table_client(self.table_name)
            logger.info(f"Successfully initialized table client for '{self.table_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize table client: {e}")
            # Don't raise here, just log the error and continue
            self.table_service = None
            self.table_client = None
    
    def get_templates(self, category: str) -> List[Template]:
        """
        Get all templates for a specific project category.
        
        Args:
            category: Project category (e.g., "Complex Design Build")
            
        Returns:
            List[Template]: List of templates for the category
            
        Raises:
            Exception: If table operation fails
        """
        try:
            # Query templates by partition key (category)
            query_filter = f"PartitionKey eq '{category}'"
            entities = self.table_client.query_entities(query_filter)
            
            templates = []
            for entity in entities:
                template = Template(
                    partition_key=entity.get("PartitionKey"),
                    row_key=entity.get("RowKey"),
                    template_folder_id=entity.get("templateFolderId"),
                    site_id=entity.get("SiteID"),
                    drive_id=entity.get("DriveID")
                )
                templates.append(template)
            
            logger.info(f"Retrieved {len(templates)} templates for category '{category}'")
            return templates
            
        except ResourceNotFoundError:
            logger.warning(f"No templates found for category '{category}'")
            return []
        except AzureError as e:
            logger.error(f"Failed to query templates for category '{category}': {e}")
            raise Exception(f"Failed to query templates: {e}")
    
    def get_template_by_name(self, category: str, template_name: str) -> Optional[Template]:
        """
        Get a specific template by category and name.
        
        Args:
            category: Project category
            template_name: Template name
            
        Returns:
            Optional[Template]: Template if found, None otherwise
            
        Raises:
            Exception: If table operation fails
        """
        try:
            # Get specific entity by partition key and row key
            entity = self.table_client.get_entity(
                partition_key=category,
                row_key=template_name
            )
            
            template = Template(
                partition_key=entity.get("PartitionKey"),
                row_key=entity.get("RowKey"),
                template_folder_id=entity.get("templateFolderId"),
                site_id=entity.get("SiteID"),
                drive_id=entity.get("DriveID")
            )
            
            logger.info(f"Retrieved template '{template_name}' for category '{category}'")
            return template
            
        except ResourceNotFoundError:
            logger.warning(f"Template '{template_name}' not found for category '{category}'")
            return None
        except AzureError as e:
            logger.error(f"Failed to get template '{template_name}' for category '{category}': {e}")
            raise Exception(f"Failed to get template: {e}")
    
    def list_categories(self) -> List[str]:
        """
        Get all available project categories.
        
        Returns:
            List[str]: List of unique project categories
            
        Raises:
            Exception: If table operation fails
        """
        try:
            # Query all entities and extract unique partition keys
            entities = self.table_client.list_entities()
            categories = set()
            
            for entity in entities:
                partition_key = entity.get("PartitionKey")
                if partition_key:
                    categories.add(partition_key)
            
            category_list = list(categories)
            logger.info(f"Retrieved {len(category_list)} categories: {category_list}")
            return category_list
            
        except AzureError as e:
            logger.error(f"Failed to list categories: {e}")
            raise Exception(f"Failed to list categories: {e}")
    
    def add_template(self, category: str, template_name: str, template_folder_id: str, site_id: str = None, drive_id: str = None) -> bool:
        """
        Add a new template mapping.
        
        Args:
            category: Project category
            template_name: Template name
            template_folder_id: SharePoint folder ItemId
            site_id: Site ID
            drive_id: Drive ID
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: If table operation fails
        """
        try:
            entity = {
                "PartitionKey": category,
                "RowKey": template_name,
                "templateFolderId": template_folder_id
            }
            if site_id:
                entity["SiteID"] = site_id
            if drive_id:
                entity["DriveID"] = drive_id
            
            self.table_client.create_entity(entity)
            logger.info(f"Successfully added template '{template_name}' for category '{category}'")
            return True
            
        except AzureError as e:
            logger.error(f"Failed to add template '{template_name}' for category '{category}': {e}")
            raise Exception(f"Failed to add template: {e}")
    
    def update_template(self, category: str, template_name: str, template_folder_id: str, site_id: str = None, drive_id: str = None) -> bool:
        """
        Update an existing template mapping.
        
        Args:
            category: Project category
            template_name: Template name
            template_folder_id: SharePoint folder ItemId
            site_id: Site ID
            drive_id: Drive ID
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: If table operation fails
        """
        try:
            entity = {
                "PartitionKey": category,
                "RowKey": template_name,
                "templateFolderId": template_folder_id
            }
            if site_id:
                entity["SiteID"] = site_id
            if drive_id:
                entity["DriveID"] = drive_id
            try:
                self.table_client.update_entity(entity)
            except Exception as e:
                # If update fails (e.g., entity does not exist), try upsert
                logger.warning(f"Update failed, trying upsert: {e}")
                self.table_client.upsert_entity(entity)
            logger.info(f"Successfully updated or upserted template '{template_name}' for category '{category}'")
            return True
        except AzureError as e:
            logger.error(f"Failed to update template '{template_name}' for category '{category}': {e}")
            raise Exception(f"Failed to update template: {e}")
    
    def delete_template(self, category: str, template_name: str) -> bool:
        """
        Delete a template mapping.
        
        Args:
            category: Project category
            template_name: Template name
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: If table operation fails
        """
        try:
            self.table_client.delete_entity(
                partition_key=category,
                row_key=template_name
            )
            logger.info(f"Successfully deleted template '{template_name}' for category '{category}'")
            return True
            
        except AzureError as e:
            logger.error(f"Failed to delete template '{template_name}' for category '{category}': {e}")
            raise Exception(f"Failed to delete template: {e}")
    
    def create_table_if_not_exists(self) -> bool:
        """
        Create the template mapping table if it doesn't exist.
        
        Returns:
            bool: True if table exists or was created, False otherwise
        """
        try:
            self.table_service.create_table_if_not_exists(self.table_name)
            logger.info(f"Table '{self.table_name}' is ready")
            return True
        except AzureError as e:
            logger.error(f"Failed to create table '{self.table_name}': {e}")
            return False
    
    def seed_template_data(self, template_data: List[Dict[str, str]]) -> bool:
        """
        Seed the table with initial template data.
        
        Args:
            template_data: List of template dictionaries with keys:
                          'category', 'template_name', 'template_folder_id'
                          
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for template in template_data:
                self.add_template(
                    category=template['category'],
                    template_name=template['template_name'],
                    template_folder_id=template['template_folder_id'],
                    site_id=template.get('site_id'),
                    drive_id=template.get('drive_id')
                )
            
            logger.info(f"Successfully seeded {len(template_data)} template mappings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to seed template data: {e}")
            return False

    def get_project_by_type(self, project_type: str) -> Optional[Project]:
        """
        Get a project by ProjectType (RowKey) from BVCSSProjects table.
        Args:
            project_type: ProjectType (RowKey)
        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        try:
            if not self.table_service:
                logger.warning("Table service not initialized, cannot get project")
                return None
                
            table_client = self.table_service.get_table_client("BVCSSProjects")
            entity = table_client.get_entity(partition_key="project", row_key=project_type)
            project = Project(
                partition_key=entity.get("PartitionKey"),
                row_key=entity.get("RowKey"),
                company_name=entity.get("CompanyName"),
                drive_id=entity.get("DriveID"),
                job_folder_id=entity.get("JobFolderID"),
                parent_folder_id=entity.get("ParentFolderID"),
                project_name=entity.get("ProjectName"),
                project_type=entity.get("ProjectType"),
                site_id=entity.get("SiteID")
            )
            logger.info(f"Retrieved project for type '{project_type}': {project}")
            return project
        except ResourceNotFoundError:
            logger.warning(f"Project not found for type '{project_type}' in BVCSSProjects")
            return None
        except AzureError as e:
            logger.error(f"Failed to get project for type '{project_type}': {e}")
            raise Exception(f"Failed to get project: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting project for type '{project_type}': {e}")
            return None


# Global storage client instance
storage_client = StorageClient() 