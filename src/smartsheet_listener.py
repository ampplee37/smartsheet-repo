"""
Smartsheet webhook listener and data processing.
Handles webhook validation and extracts relevant data from row updates.
"""

import json
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional, List
import smartsheet
import traceback
try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


class SmartsheetListener:
    """Handles Smartsheet webhook events and data processing."""
    
    def __init__(self):
        """Initialize the Smartsheet listener."""
        if not config.SMTSHEET_TOKEN:
            logger.warning("No Smartsheet token provided, client will not be initialized")
            self.client = None
        else:
            self.client = smartsheet.Smartsheet(config.SMTSHEET_TOKEN)
            self.client.errors_as_exceptions(True)
    
    def validate_webhook(self, payload: str, signature: str, webhook_secret: str) -> bool:
        """
        Validate Smartsheet webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature header
            webhook_secret: Webhook secret for validation
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Create expected signature
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if is_valid:
                logger.info("Webhook signature validation successful")
            else:
                logger.warning("Webhook signature validation failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {e}")
            return False
    
    def parse_webhook_payload(self, payload: str) -> Dict[str, Any]:
        """
        Parse webhook payload and extract relevant information.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            Dict[str, Any]: Parsed webhook data
            
        Raises:
            ValueError: If payload cannot be parsed
        """
        try:
            data = json.loads(payload)
            logger.info(f"Successfully parsed webhook payload: {data.get('eventType', 'unknown')}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise ValueError(f"Invalid JSON payload: {e}")
    
    def extract_row_data(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract relevant row data from webhook payload.
        
        Args:
            webhook_data: Parsed webhook data
            
        Returns:
            Optional[Dict[str, Any]]: Extracted row data if relevant, None otherwise
        """
        try:
            # Check if this is a row update event
            event_type = webhook_data.get('eventType')
            if event_type != 'ROW_UPDATED':
                logger.info(f"Ignoring non-row-update event: {event_type}")
                return None
            
            # Extract row information
            row_data = webhook_data.get('row', {})
            if not row_data:
                logger.warning("No row data found in webhook payload")
                return None
            
            # Extract cell data
            cells = row_data.get('cells', [])
            cell_data = {}
            
            for cell in cells:
                column_id = cell.get('columnId')
                value = cell.get('value')
                cell_data[column_id] = value
            
            # Extract row ID and other metadata
            result = {
                'row_id': row_data.get('id'),
                'sheet_id': webhook_data.get('objectId'),
                'cells': cell_data,
                'modified_at': row_data.get('modifiedAt'),
                'row_number': row_data.get('rowNumber')
            }
            
            logger.info(f"Extracted row data for row {result['row_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract row data: {e}")
            return None
    
    def is_closed_won_deal(self, row_data: Dict[str, Any], sales_stage_column_id: str) -> bool:
        """
        Check if the row represents a "Closed Won" deal.
        
        Args:
            row_data: Extracted row data
            sales_stage_column_id: Column ID for "Sales Stage" field
            
        Returns:
            bool: True if deal is "Closed Won", False otherwise
        """
        try:
            cells = row_data.get('cells', {})
            sales_stage_value = cells.get(sales_stage_column_id)
            
            if sales_stage_value == "Closed Won":
                logger.info(f"Deal in row {row_data.get('row_id')} is marked as 'Closed Won'")
                return True
            else:
                logger.info(f"Deal in row {row_data.get('row_id')} has sales stage: {sales_stage_value}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check if deal is closed won: {e}")
            return False
    
    def extract_project_info(self, row_data: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract project information from row data using column mapping.
        
        Args:
            row_data: Extracted row data
            column_mapping: Mapping of field names to column IDs
            
        Returns:
            Dict[str, Any]: Extracted project information
        """
        try:
            cells = row_data.get('cells', {})
            project_info = {}
            
            for field_name, column_id in column_mapping.items():
                value = cells.get(column_id)
                project_info[field_name] = value
            
            # Add metadata
            project_info['row_id'] = row_data.get('row_id')
            project_info['sheet_id'] = row_data.get('sheet_id')
            project_info['modified_at'] = row_data.get('modified_at')
            
            logger.info(f"Extracted project info: {project_info}")
            return project_info
            
        except Exception as e:
            logger.error(f"Failed to extract project info: {e}")
            return {}
    
    def get_sheet_columns(self, sheet_id: int) -> List[Dict[str, Any]]:
        """
        Get column information for a Smartsheet.
        
        Args:
            sheet_id: Smartsheet ID
            
        Returns:
            List[Dict[str, Any]]: List of column information
            
        Raises:
            Exception: If API call fails
        """
        try:
            if not self.client:
                logger.warning("Smartsheet client not initialized, cannot get columns")
                return []
                
            sheet = self.client.Sheets.get_sheet(sheet_id, include='columnDefinitions')
            columns = sheet.columns
            
            logger.info(f"Retrieved {len(columns)} columns from sheet {sheet_id}")
            return [
                {
                    'id': col.id,
                    'title': col.title,
                    'type': col.type
                }
                for col in columns
            ]
            
        except Exception as e:
            logger.error(f"Failed to get sheet columns for {sheet_id}: {e}")
            raise
    
    def create_column_mapping(self, sheet_id: int, required_fields: List[str]) -> Dict[str, str]:
        """
        Create a mapping of field names to column IDs for a sheet.
        
        Args:
            sheet_id: Smartsheet ID
            required_fields: List of required field names
            
        Returns:
            Dict[str, str]: Mapping of field names to column IDs
            
        Raises:
            Exception: If mapping cannot be created
        """
        try:
            columns = self.get_sheet_columns(sheet_id)
            mapping = {}
            
            for field_name in required_fields:
                # Find column by title (case-insensitive)
                column = None
                for col in columns:
                    if col['title'].lower() == field_name.lower():
                        column = col
                        break
                
                if column:
                    mapping[field_name] = str(column['id'])
                    logger.info(f"Mapped field '{field_name}' to column '{column['title']}' (ID: {column['id']})")
                else:
                    logger.warning(f"Could not find column for field '{field_name}'")
            
            return mapping
            
        except Exception as e:
            logger.error(f"Failed to create column mapping: {e}")
            raise
    
    def get_row_details(self, sheet_id: int, row_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific row.
        
        Args:
            sheet_id: Smartsheet ID
            row_id: Row ID
            
        Returns:
            Dict[str, Any]: Row details
            
        Raises:
            Exception: If API call fails
        """
        try:
            row = self.client.Sheets.get_row(sheet_id, row_id)
            
            # Extract cell values
            cells = {}
            for cell in row.cells:
                if hasattr(cell, 'column_id') and hasattr(cell, 'value'):
                    cells[str(cell.column_id)] = cell.value
            
            result = {
                'id': row.id,
                'row_number': row.row_number,
                'cells': cells,
                'modified_at': row.modified_at.isoformat() if row.modified_at else None
            }
            
            logger.info(f"Retrieved details for row {row_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get row details for {row_id}: {e}")
            raise
    
    def validate_webhook_challenge(self, challenge: str) -> str:
        """
        Handle Smartsheet webhook challenge for verification.
        
        Args:
            challenge: Challenge string from Smartsheet
            
        Returns:
            str: Challenge response
        """
        logger.info(f"Received webhook challenge: {challenge}")
        return challenge
    
    def process_webhook_event(self, payload: str, signature: str = None, webhook_secret: str = None) -> Optional[Dict[str, Any]]:
        """
        Process a complete webhook event.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature (optional)
            webhook_secret: Webhook secret for validation (optional)
            
        Returns:
            Optional[Dict[str, Any]]: Processed event data if relevant, None otherwise
        """
        try:
            logger.info("Starting webhook event processing")
            
            if signature and webhook_secret:
                logger.info("Validating webhook signature...")
                if not self.validate_webhook(payload, signature, webhook_secret):
                    logger.error("Webhook signature validation failed")
                    return None
                logger.info("Webhook signature validation passed")
            else:
                logger.info("Skipping webhook signature validation (no signature or secret)")
            
            webhook_data = self.parse_webhook_payload(payload)
            logger.info(f"Parsed webhook data, event type: {webhook_data.get('eventType')}")
            
            if webhook_data.get('eventType') == 'WEBHOOK_CHALLENGE':
                logger.info("Processing webhook challenge")
                challenge = webhook_data.get('challenge')
                return {
                    'type': 'challenge',
                    'response': self.validate_webhook_challenge(challenge)
                }
            
            logger.info("Extracting row data...")
            row_data = self.extract_row_data(webhook_data)
            if not row_data:
                logger.warning("No row data extracted, returning None")
                return None
            
            logger.info(f"Row data extracted for row {row_data.get('row_id')}")
            
            # Extract cells
            cells = row_data.get('cells', {})
            logger.info(f"Found {len(cells)} cells in row data")
            
            sales_stage = cells.get('593432251944836')
            logger.info(f"Sales stage value: {sales_stage}")
            
            if sales_stage != 'Closed Won':
                logger.info(f"Sales stage is not 'Closed Won' (got: {sales_stage}), ignoring event")
                return None
            
            # Extract project_id and project_type
            project_id = cells.get('3408182019051396')
            project_type = cells.get('5878702367002500')
            logger.info(f"Project ID: {project_id}, Project Type: {project_type}")
            
            if not project_id or not project_type:
                logger.info("Missing project_id or project_type, ignoring event")
                return None
            
            # Add all cell values by column ID to project_info
            project_info = {
                'project_id': project_id,
                'project_type': project_type,
                'row_id': row_data.get('row_id'),
                'sheet_id': row_data.get('sheet_id'),
                'modified_at': row_data.get('modified_at'),
                **cells  # <-- add all cell values by column ID
            }
            
            result = {
                'type': 'closed_won_deal',
                'row_data': row_data,
                'project_info': project_info,
                'webhook_data': webhook_data
            }
            
            logger.info(f"Successfully processed webhook event for Closed Won deal, project_id: {project_id}, project_type: {project_type}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}")
            logger.error(traceback.format_exc())
            return None


# Global Smartsheet listener instance
smartsheet_listener = SmartsheetListener() 