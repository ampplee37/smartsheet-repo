"""
Smartsheet updater module for updating rows with OneNote URLs.
"""

import os
import logging
import smartsheet
import requests
from typing import Dict, Any, Optional
from src.config import config

logger = logging.getLogger(__name__)

class SmartsheetUpdater:
    """
    Handles Smartsheet API operations for updating rows with OneNote URLs.
    """
    
    def __init__(self):
        """Initialize the Smartsheet client."""
        self.token = config.SMTSHEET_TOKEN
        if not self.token:
            raise ValueError("SMTSHEET_TOKEN is required")
        
        self.client = smartsheet.Smartsheet(self.token)
        self.client.errors_as_exceptions(True)
        
        # Column ID for "Public Notebook" column
        self.public_notebook_column_id = 3086497829048196
        
    def update_row_with_onenote_url(
        self, 
        sheet_id: int, 
        row_id: int, 
        notebook_name: str, 
        notebook_url: str,
        section_url: Optional[str] = None
    ) -> bool:
        """
        Update a Smartsheet row with a hyperlink to the OneNote notebook/section.
        
        Args:
            sheet_id: Smartsheet sheet ID
            row_id: Row ID to update
            notebook_name: Display name for the hyperlink
            notebook_url: URL to the OneNote notebook
            section_url: URL to the OneNote section (preferred over notebook_url)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prefer section URL if available, otherwise use notebook URL
            target_url = section_url or notebook_url
            
            if not target_url:
                logger.error("No URL provided for OneNote link")
                return False
                
            logger.info(f"Updating Smartsheet row {row_id} with OneNote URL: {target_url}")
            
            # Use raw API format (like the working example provided)
            payload = {
                "id": row_id,
                "cells": [
                    {
                        "columnId": self.public_notebook_column_id,
                        "value": notebook_name,
                        "hyperlink": {
                            "url": target_url
                        }
                    }
                ]
            }
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://api.smartsheet.com/2.0/sheets/{sheet_id}/rows"
            response = requests.put(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Successfully updated Smartsheet row {row_id} with OneNote URL")
                return True
            else:
                logger.error(f"Failed to update Smartsheet row {row_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Smartsheet row {row_id} with OneNote URL: {e}")
            return False
    
    def get_sheet_info(self, sheet_id: int) -> Optional[Dict[str, Any]]:
        """
        Get basic information about a Smartsheet.
        
        Args:
            sheet_id: Smartsheet sheet ID
            
        Returns:
            Dict[str, Any]: Sheet information or None if failed
        """
        try:
            sheet = self.client.Sheets.get_sheet(sheet_id)
            return {
                'id': sheet.id,
                'name': sheet.name,
                'access_level': sheet.access_level
            }
        except Exception as e:
            logger.error(f"Error getting sheet info for {sheet_id}: {e}")
            return None

# Global instance
smartsheet_updater = SmartsheetUpdater() 