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


def get_column_id_to_name(client, sheet_id: int) -> dict:
    """
    Return a mapping of column ID (as str) to column name for the given sheet.
    """
    try:
        if not client:
            return {}
        sheet = client.Sheets.get_sheet(sheet_id, include='columnDefinitions')
        columns = sheet.columns
        return {str(col.id): col.title for col in columns}
    except Exception as e:
        logger.error(f"Failed to get column ID to name mapping: {e}")
        return {}


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
        Now supports both 'updated' and 'created' events for rows and cells.
        """
        try:
            events = webhook_data.get('events', [])
            if events:
                logger.info(f"Found {len(events)} events in webhook payload")
                row_events = []
                for event in events:
                    object_type = event.get('objectType')
                    event_type = event.get('eventType')
                    
                    # Handle row events
                    if object_type == 'row' and event_type in ('updated', 'created'):
                        row_events.append(event)
                    
                    # Handle cell events - convert to row events for processing
                    elif object_type == 'cell' and event_type in ('updated', 'created'):
                        # Check if this is a Sales Stage column update
                        column_id = event.get('columnId')
                        logger.info(f"Processing cell event: columnId={column_id} (type: {type(column_id)}), expected: '593432251944836'")
                        if str(column_id) == '593432251944836':  # Sales Stage column
                            logger.info(f"Found Sales Stage cell update event: rowId={event.get('rowId')}, columnId={column_id}")
                            row_event = {
                                'objectType': 'row',
                                'eventType': 'updated',
                                'event_type': 'updated',  # Ensure consistency
                                'id': event.get('rowId'),
                                'sheetId': webhook_data.get('scopeObjectId'),
                            }
                            logger.info(f"Converted Sales Stage cell update event to row event for row {event.get('rowId')}")
                            row_events.append(row_event)
                        else:
                            logger.info(f"Ignoring cell update for non-Sales Stage column: {column_id}")
                    
                    # Handle other cell created events (legacy support)
                    elif object_type == 'cell' and event_type == 'created':
                        # Convert cell created event to row event
                        logger.info(f"Found cell created event: rowId={event.get('rowId')}, columnId={event.get('columnId')}")
                        row_event = {
                            'objectType': 'row',
                            'eventType': 'created',
                            'event_type': 'created',  # Ensure consistency
                            'id': event.get('rowId'),
                            'sheetId': webhook_data.get('scopeObjectId'),
                        }
                        logger.info(f"Converted cell created event to row event for row {event.get('rowId')}")
                        row_events.append(row_event)
                
                if not row_events:
                    logger.info("No row events found in webhook payload")
                    return None
                
                # For now, just process the first row event
                row_event = row_events[0]
                row_id = row_event.get('id')
                sheet_id = row_event.get('sheetId') or webhook_data.get('scopeObjectId')
                
                if not row_id or not sheet_id:
                    logger.error("Missing row_id or sheet_id in row event")
                    return None
                
                logger.info(f"Found row event for row {row_id} in sheet {sheet_id}")
                row_details = self.get_row_details(int(sheet_id), int(row_id))
                
                if not row_details:
                    logger.error(f"Failed to get details for row {row_id} in sheet {sheet_id}")
                    return None
                
                # Attach event_type for downstream logic
                row_details['event_type'] = row_event.get('event_type') or row_event.get('eventType')
                row_details['row_id'] = row_id
                row_details['sheet_id'] = sheet_id
                return row_details
            else:
                logger.info("No events found in webhook payload")
                return None
        except Exception as e:
            logger.error(f"Error extracting row data: {e}")
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
        Now includes displayValue and hyperlink for each cell.
        Ensures hyperlink is always a dict if present.
        """
        try:
            if not self.client:
                raise Exception("Smartsheet client not initialized")
            row = self.client.Sheets.get_row(sheet_id, row_id)
            cells = {}
            for cell in row.cells:
                if hasattr(cell, 'column_id'):
                    # Normalize hyperlink to dict if present
                    hyperlink = None
                    if hasattr(cell, 'hyperlink') and cell.hyperlink:
                        h = cell.hyperlink
                        if hasattr(h, 'url'):
                            hyperlink = {
                                'url': getattr(h, 'url', None),
                                'label': getattr(h, 'label', None)
                            }
                        elif isinstance(h, dict):
                            hyperlink = h
                        else:
                            hyperlink = None
                    cell_info = {
                        'value': getattr(cell, 'value', None),
                        'displayValue': getattr(cell, 'display_value', None) or getattr(cell, 'displayValue', None),
                        'hyperlink': hyperlink
                    }
                    cells[str(cell.column_id)] = cell_info
            return {
                'id': row.id,
                'cells': cells
            }
        except Exception as e:
            logger.error(f"Error getting row details for {row_id}: {e}")
            return {}
    
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
            sales_stage_cell = cells.get('593432251944836', {})  # Sales Stage column ID
            
            # Handle new cell data structure (dict with value/displayValue)
            if isinstance(sales_stage_cell, dict):
                sales_stage = sales_stage_cell.get('displayValue') or sales_stage_cell.get('value')
            else:
                # Handle legacy cell data structure (direct value)
                sales_stage = sales_stage_cell
            
            # Only process if sales stage is "Closed Won"
            if sales_stage != 'Closed Won':
                logger.info(f"Sales stage is not 'Closed Won' (got: {sales_stage}), row has not changed meaningfully")
                return False
            
            # Check if we have the required project data
            project_id_cell = cells.get('3408182019051396', {})  # Opportunity ID
            project_type_cell = cells.get('5878702367002500', {})  # Project Category
            
            # Handle new cell data structure for project data
            if isinstance(project_id_cell, dict):
                project_id = project_id_cell.get('displayValue') or project_id_cell.get('value')
            else:
                project_id = project_id_cell
                
            if isinstance(project_type_cell, dict):
                project_type = project_type_cell.get('displayValue') or project_type_cell.get('value')
            else:
                project_type = project_type_cell
            
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

            # --- Determine Sales Stage and trigger appropriate logic ---
            cells = row_data.get('cells', {})
            sales_stage_cell = cells.get('593432251944836', {})
            sales_stage = sales_stage_cell.get('displayValue') or sales_stage_cell.get('value') or ""
            opportunity_stages = [
                "1 - Rumor",
                "2 - Identified",
                "3 - Qualified",
                "4 - Proposed 50",
                "4 - Proposed 75",
                "4 - Proposed 90",
            ]
            event_type = row_data.get('event_type')
            # For new rows, always process if sales stage is in opportunity stages
            if event_type == 'created' and sales_stage in opportunity_stages:
                logger.info(f"New row created with sales stage '{sales_stage}', triggering Opportunity Notebook logic.")
                try:
                    from src.onenote_manager import onenote_manager
                    opportunity_notebook_id = "1-967d595f-41fe-4f39-ae85-d82f0e9211b3"
                    opportunity_site_id = "bvcollective.sharepoint.com,a3c779e2-668d-4151-963c-eba6bb48c8c4,3eb6c052-ce82-4449-a860-470b0025611f"
                    customer_name = cells.get('1475623376867204', {}).get('displayValue') or cells.get('1475623376867204', {}).get('value') or "Unknown Customer"
                    opp_id = cells.get('3408182019051396', {}).get('displayValue') or cells.get('3408182019051396', {}).get('value') or ""
                    project_name = cells.get('3534360453271428', {}).get('displayValue') or cells.get('3534360453271428', {}).get('value') or ""
                    sheet_id = row_data.get('sheet_id')
                    if not sheet_id:
                        logger.error("No sheet_id found in row_data; skipping Opportunity Notebook integration.")
                    else:
                        column_id_to_name = get_column_id_to_name(self.client, int(sheet_id)) or {}
                        result = onenote_manager.add_opportunity_page_for_row(
                            site_id=opportunity_site_id,
                            notebook_id=opportunity_notebook_id,
                            customer_name=customer_name,
                            opp_id=opp_id,
                            project_name=project_name,
                            row_data=cells,
                            column_id_to_name=column_id_to_name
                        )
                        logger.info(f"Opportunity Notebook result: {result}")
                except Exception as e:
                    logger.error(f"Error in Opportunity Notebook integration: {e}")
            # For updates, require meaningful change
            elif event_type == 'updated':
                if sales_stage in opportunity_stages:
                    # Existing logic for meaningful change (if any)
                    # ... existing code ...
                    pass
            # Existing logic for Closed Won and other cases

            # Check if the row has actually changed meaningfully
            if not self._has_row_actually_changed(row_data):
                logger.info("Row has not changed meaningfully, skipping processing")
                return None
            
            # Extract cells
            cells = row_data.get('cells', {})
            logger.info(f"Found {len(cells)} cells in row data")
            
            # Handle new cell data structure for sales stage
            sales_stage_cell = cells.get('593432251944836', {})
            if isinstance(sales_stage_cell, dict):
                sales_stage = sales_stage_cell.get('displayValue') or sales_stage_cell.get('value')
            else:
                sales_stage = sales_stage_cell
            logger.info(f"Sales stage value: {sales_stage}")
            
            if sales_stage != 'Closed Won':
                logger.info(f"Sales stage is not 'Closed Won' (got: {sales_stage}), ignoring event")
                return None
            
            # Extract project_id and project_type with new cell data structure
            project_id_cell = cells.get('3408182019051396', {})
            project_type_cell = cells.get('5878702367002500', {})
            
            if isinstance(project_id_cell, dict):
                project_id = project_id_cell.get('displayValue') or project_id_cell.get('value')
            else:
                project_id = project_id_cell
                
            if isinstance(project_type_cell, dict):
                project_type = project_type_cell.get('displayValue') or project_type_cell.get('value')
            else:
                project_type = project_type_cell
                
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