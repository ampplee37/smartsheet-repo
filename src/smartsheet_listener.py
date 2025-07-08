"""
Smartsheet webhook listener and data processing.
Handles webhook validation and extracts relevant data from row updates.
"""

import json
import hashlib
import hmac
import logging
import time
from typing import Dict, Any, Optional, List
import smartsheet
import traceback
try:
    from .config import config
    from .storage import StorageManager
except ImportError:
    from config import config
    from storage import StorageManager

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
        
        # Initialize storage manager for webhook deduplication
        self.storage_manager = StorageManager()
        
        # Fallback in-memory cache for when storage is not available
        self._processed_webhooks = {}  # webhook_signature -> timestamp
        self._webhook_cache_ttl = 300  # 5 minutes cache TTL
    
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
            # Check if this is a webhook with events array (new format)
            events = webhook_data.get('events', [])
            if events:
                logger.info(f"Found {len(events)} events in webhook payload")
                
                # Look for row update events OR cell update events
                row_events = []
                for event in events:
                    object_type = event.get('objectType')
                    event_type = event.get('eventType')
                    
                    logger.info(f"Processing event: objectType={object_type}, eventType={event_type}")
                    
                    # Handle both row.updated and cell.updated events
                    if object_type == 'row' and event_type == 'updated':
                        row_events.append(event)
                        logger.info(f"Added row update event for row {event.get('id')}")
                    elif object_type == 'cell' and event_type == 'updated':
                        # For cell updates, we need to get the rowId from the cell event
                        row_id = event.get('rowId')
                        column_id = event.get('columnId')
                        
                        logger.info(f"Found cell update event: rowId={row_id}, columnId={column_id}")
                        
                        # Log the specific column we're monitoring
                        if column_id == '593432251944836':
                            logger.info(f"*** SALES STAGE COLUMN UPDATED *** - Row: {row_id}, Column: {column_id}")
                        
                        if row_id:
                            # Convert cell event to row event format for processing
                            row_event = {
                                'objectType': 'row',
                                'eventType': 'updated',
                                'id': row_id,
                                'userId': event.get('userId'),
                                'timestamp': event.get('timestamp')
                            }
                            row_events.append(row_event)
                            logger.info(f"Converted cell update event to row event for row {row_id}")
                
                if not row_events:
                    logger.info("No row update or cell update events found in webhook payload")
                    return None
                
                # Use the first row event
                row_event = row_events[0]
                row_id = row_event.get('id')
                sheet_id = webhook_data.get('scopeObjectId')
                
                logger.info(f"Found row update event for row {row_id} in sheet {sheet_id}")
                
                # For row updates, we need to fetch the actual row data from Smartsheet API
                # since the webhook doesn't include the full row data
                if self.client and row_id and sheet_id:
                    try:
                        row_details = self.get_row_details(int(sheet_id), int(row_id))
                        
                        # Log the Sales Stage value specifically
                        cells = row_details.get('cells', {})
                        sales_stage_value = cells.get('593432251944836')
                        logger.info(f"*** SALES STAGE VALUE FOR ROW {row_id}: '{sales_stage_value}' ***")
                        
                        # Ensure row_id is properly set in the returned data
                        row_details['row_id'] = row_details.get('id')
                        return row_details
                    except Exception as e:
                        logger.error(f"Failed to get row details for row {row_id}: {e}")
                        return None
                else:
                    logger.warning("Cannot fetch row details - missing client, row_id, or sheet_id")
                    return None
            
            # Legacy format check (single eventType) - only process if no events array was found
            event_type = webhook_data.get('eventType')
            if event_type != 'ROW_UPDATED':
                logger.info(f"Ignoring non-row-update event: {event_type}")
                return None
            
            # Extract row information (legacy format)
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
            if not self.client:
                raise Exception("Smartsheet client not initialized")
                
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
    
    def _is_duplicate_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Check if this webhook has already been processed recently.
        
        Args:
            webhook_data: Parsed webhook data
            
        Returns:
            bool: True if this is a duplicate webhook, False otherwise
        """
        try:
            # Check if this webhook has been processed recently
            webhook_id = webhook_data.get('webhookId')
            nonce = webhook_data.get('nonce')
            timestamp = webhook_data.get('timestamp')
            
            if not webhook_id:
                logger.warning("No webhook ID found, cannot check for duplicates")
                return False
            
            # Create a unique identifier for this webhook event
            event_signature = f"{webhook_id}_{nonce}_{timestamp}"
            
            # First try Azure Storage (persistent across function restarts)
            if self.storage_manager.is_webhook_processed(event_signature):
                logger.warning(f"Duplicate webhook detected in storage: {event_signature}")
                return True
            
            # Fallback to in-memory cache
            current_time = time.time()
            self._processed_webhooks = {
                sig: ts 
                for sig, ts in self._processed_webhooks.items()
                if current_time - ts < self._webhook_cache_ttl
            }
            
            if event_signature in self._processed_webhooks:
                logger.warning(f"Duplicate webhook detected in memory: {event_signature}")
                return True
            
            # Mark as processed in both storage and memory
            self.storage_manager.mark_webhook_processed(event_signature)
            self._processed_webhooks[event_signature] = current_time
            logger.info(f"Webhook {event_signature} marked as processed")
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicate webhook: {e}")
            return False
    
    def _has_row_actually_changed(self, row_data: Dict[str, Any]) -> bool:
        """
        Check if the row has actually changed by examining the sales stage and modification time.
        
        Args:
            row_data: Extracted row data
            
        Returns:
            bool: True if the row has meaningful changes, False otherwise
        """
        try:
            cells = row_data.get('cells', {})
            sales_stage = cells.get('593432251944836')  # Sales Stage column ID
            
            # Only process if sales stage is "Closed Won"
            if sales_stage != 'Closed Won':
                logger.info(f"Sales stage is not 'Closed Won' (got: {sales_stage}), row has not changed meaningfully")
                return False
            
            # Check if we have the required project data
            project_id = cells.get('3408182019051396')  # Opportunity ID
            project_type = cells.get('5878702367002500')  # Project Category
            
            if not project_id or not project_type:
                logger.info("Missing project_id or project_type, row change not meaningful")
                return False
            
            logger.info(f"Row has meaningful changes: sales_stage={sales_stage}, project_id={project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking if row has changed: {e}")
            return False
    
    def process_webhook_event(self, payload: str, signature: Optional[str] = None, webhook_secret: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
            logger.info(f"Payload length: {len(payload)} characters")
            
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
            logger.info(f"Webhook ID: {webhook_data.get('webhookId')}")
            logger.info(f"Scope: {webhook_data.get('scope')}")
            logger.info(f"Scope Object ID: {webhook_data.get('scopeObjectId')}")
            
            # Check for duplicate webhooks early
            if self._is_duplicate_webhook(webhook_data):
                logger.info("Duplicate webhook detected, skipping processing")
                return None
            
            if webhook_data.get('eventType') == 'WEBHOOK_CHALLENGE':
                logger.info("Processing webhook challenge")
                challenge = webhook_data.get('challenge')
                if challenge and isinstance(challenge, str):
                    return {
                        'type': 'challenge',
                        'response': self.validate_webhook_challenge(challenge)
                    }
                else:
                    logger.warning("Webhook challenge received but no valid challenge string found")
                    return None
            
            logger.info("Extracting row data...")
            row_data = self.extract_row_data(webhook_data)
            if not row_data:
                logger.warning("No row data extracted, returning None")
                return None
            
            logger.info(f"Row data extracted for row {row_data.get('row_id')}")
            
            # Check if the row has actually changed meaningfully
            if not self._has_row_actually_changed(row_data):
                logger.info("Row has not changed meaningfully, skipping processing")
                return None
            
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