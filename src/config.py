"""
Configuration management for BVC Smartsheet-SharePoint Automation.
Loads environment variables and provides centralized configuration.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration class."""
    
    # Azure AD Configuration
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    
    # Smartsheet Configuration
    SMTSHEET_TOKEN: str = os.getenv("SMTSHEET_TOKEN", "")
    SMTSHEET_ID: str = os.getenv("SMTSHEET_ID", "")
    
    # Azure Storage Configuration
    STORAGE_CONNECTION_STRING: str = os.getenv("STORAGE_CONNECTION_STRING", "")
    
    # SharePoint Configuration
    SHAREPOINT_SITE_ID: str = os.getenv("SHAREPOINT_SITE_ID", "")
    SHAREPOINT_USERNAME: str = os.getenv("SHAREPOINT_USERNAME", "")
    SHAREPOINT_PASSWORD: str = os.getenv("SHAREPOINT_PASSWORD", "")
    
    # Bot Authentication for OneNote (Delegated Auth)
    BVC_ONENOTE_INGEST_BOT_ID: str = os.getenv("BVC_ONENOTE_INGEST_BOT_ID", "")
    BVC_ONENOTE_INGEST_BOT_KEY: str = os.getenv("BVC_ONENOTE_INGEST_BOT_KEY", "")
    BVC_BOT_REFRESH_TOKEN: str = os.getenv("BVC_BOT_REFRESH_TOKEN", "")
    BVC_BOT_CLIENT_SECRET: str = os.getenv("BVC_BOT_CLIENT_SECRET", "")
    
    # Azure Function Configuration
    FUNCTION_KEY: Optional[str] = os.getenv("FUNCTION_KEY")
    
    # Graph API Configuration
    GRAPH_API_SCOPE: str = "https://graph.microsoft.com/.default"
    GRAPH_API_DELEGATED_SCOPE: str = "https://graph.microsoft.com/Notes.ReadWrite.All"
    
    # Smartsheet API Configuration
    SMARTSHEET_API_BASE: str = "https://api.smartsheet.com/2.0"
    
    # Table Configuration
    TEMPLATE_MAPPING_TABLE: str = "TemplateMapping"
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds
    
    # Timeout Configuration
    REQUEST_TIMEOUT: int = 30  # seconds
    COPY_OPERATION_TIMEOUT: int = 300  # seconds
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            bool: True if all required config is present, False otherwise
        """
        required_fields = [
            "BVC_ONENOTE_INGEST_BOT_ID",
            "BVC_ONENOTE_INGEST_BOT_KEY",
            "BVC_BOT_REFRESH_TOKEN",
            "BVC_BOT_CLIENT_SECRET",
            "SMTSHEET_TOKEN"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"Missing required configuration: {', '.join(missing_fields)}")
            return False
        
        return True
    
    @classmethod
    def get_graph_api_scope(cls) -> str:
        """Get the Graph API scope for authentication."""
        return cls.GRAPH_API_SCOPE
    
    @classmethod
    def get_smartsheet_api_base(cls) -> str:
        """Get the Smartsheet API base URL."""
        return cls.SMARTSHEET_API_BASE


# Global config instance
config = Config() 